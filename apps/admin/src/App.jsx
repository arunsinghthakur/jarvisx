import React, { useState, useMemo } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { useAuth } from './contexts/AuthContext'
import { useAppData, useOrganizationActions, useWorkspaceActions, useAgentActions, useMCPActions } from './hooks'
import { Sidebar, LoadingFallback } from './components/common'
import { ToastProvider } from './components/common/ToastProvider'
import { Header, MainContent } from './components/layout'
import { Login, EmailVerification, ForgotPassword, ResetPassword, SSOCallback } from './components/auth'

function App() {
  const { user, isAuthenticated, loading: authLoading, error: authError, login, logout } = useAuth()

  const isPlatformAdmin = user?.is_platform_admin || false
  const currentOrganizationId = user?.organization_id || null
  const currentOrganization = useMemo(() => {
    if (!user) return null
    return {
      id: user.organization_id,
      name: user.organization_name,
      is_platform_admin: user.is_platform_admin,
      features: user.features || {}
    }
  }, [user])

  const complianceEnabled = currentOrganization?.features?.compliance ?? false

  const [activeSection, setActiveSection] = useState('dashboard')
  const [error, setError] = useState(null)

  const appData = useAppData(isAuthenticated, currentOrganizationId)

  const orgActions = useOrganizationActions(
    appData.loadOrganizations,
    appData.loadWorkspaces
  )

  const workspaceActions = useWorkspaceActions(
    appData.loadWorkspaces,
    appData.loadOrganizations,
    appData.loadWorkspaceDetails
  )

  const agentActions = useAgentActions(
    appData.loadAvailableAgents,
    appData.loadWorkspaces,
    appData.loadAvailableMcps
  )

  const mcpActions = useMCPActions(
    appData.loadAvailableMcps,
    appData.loadWorkspaces,
    appData.loadAvailableAgents
  )

  const combinedError = error || orgActions.error || workspaceActions.error || agentActions.error || mcpActions.error

  const clearAllErrors = () => {
    setError(null)
    orgActions.clearError()
    workspaceActions.clearError()
    agentActions.clearError()
    mcpActions.clearError()
  }

  const handleLogin = async (email, password) => {
    await login(email, password)
  }

  if (authLoading) {
    return <LoadingFallback message="Authenticating..." />
  }

  return (
    <ToastProvider>
      <Routes>
        <Route path="/verify-email" element={<EmailVerification />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/sso/callback" element={<SSOCallback />} />
        <Route
          path="/*"
          element={
            !isAuthenticated ? (
              <Login onLogin={handleLogin} error={authError} loading={authLoading} />
            ) : (
              <div className="App">
                <Header
                  user={user}
                  isPlatformAdmin={isPlatformAdmin}
                  onLogout={logout}
                />

                {combinedError && (
                  <div className="error-banner">
                    {combinedError}
                    <button onClick={clearAllErrors}>×</button>
                  </div>
                )}

                <div className="main-container">
                  <Sidebar
                    activeSection={activeSection}
                    onSectionChange={setActiveSection}
                    isPlatformAdmin={isPlatformAdmin}
                    complianceEnabled={complianceEnabled}
                  />

                  <div className="content">
                    <MainContent
                      activeSection={activeSection}
                      setActiveSection={setActiveSection}
                      isPlatformAdmin={isPlatformAdmin}
                      currentOrganization={currentOrganization}
                      organizations={appData.organizations}
                      workspaces={appData.workspaces}
                      availableAgents={appData.availableAgents}
                      availableMcps={appData.availableMcps}
                      teams={appData.teams}
                      organizationsLoading={appData.organizationsLoading}
                      workspacesLoading={appData.workspacesLoading}
                      availableAgentsLoading={appData.availableAgentsLoading}
                      availableMcpsLoading={appData.availableMcpsLoading}
                      orgActions={orgActions}
                      workspaceActions={workspaceActions}
                      agentActions={agentActions}
                      mcpActions={mcpActions}
                      loadWorkspaceDetails={appData.loadWorkspaceDetails}
                    />
                  </div>
                </div>
              </div>
            )
          }
        />
      </Routes>
    </ToastProvider>
  )
}

export default App
