import React, { useState, Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Login, ForgotPassword, ResetPassword, SSOCallback } from './components/auth'
import { LoadingFallback } from './components/common'
import { useAuth } from './contexts'
import './App.css'

const VoiceChat = lazy(() => import('./components/chat/VoiceChat'))

function ChatbotRoute() {
  const { user, loading, error, isAuthenticated, login, logout } = useAuth()
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState(null)

  const handleLogin = async (email, password) => {
    setLoginLoading(true)
    setLoginError(null)
    
    try {
      await login(email, password)
    } catch (err) {
      setLoginError(err.message || 'Login failed')
    } finally {
      setLoginLoading(false)
    }
  }

  if (loading) {
    return <LoadingFallback message="Authenticating..." />
  }

  if (!isAuthenticated) {
    const currentPath = window.location.pathname + window.location.search
    if (currentPath !== '/' && !currentPath.startsWith('/sso/')) {
      sessionStorage.setItem('sso_return_url', currentPath)
    }
    return <Login onLogin={handleLogin} error={loginError || error} loading={loginLoading} />
  }

  return (
    <div className="App">
      <Suspense fallback={<LoadingFallback message="Loading chat..." />}>
        <VoiceChat user={user} onLogout={logout} />
      </Suspense>
    </div>
  )
}

function WorkspaceRoute() {
  const { user, loading, error, isAuthenticated, login, logout } = useAuth()
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState(null)

  const handleLogin = async (email, password) => {
    setLoginLoading(true)
    setLoginError(null)
    
    try {
      await login(email, password)
    } catch (err) {
      setLoginError(err.message || 'Login failed')
    } finally {
      setLoginLoading(false)
    }
  }

  if (loading) {
    return <LoadingFallback message="Authenticating..." />
  }

  if (!isAuthenticated) {
    const currentPath = window.location.pathname + window.location.search
    if (currentPath !== '/' && !currentPath.startsWith('/sso/')) {
      sessionStorage.setItem('sso_return_url', currentPath)
    }
    return <Login onLogin={handleLogin} error={loginError || error} loading={loginLoading} />
  }

  return (
    <div className="App">
      <Suspense fallback={<LoadingFallback message="Loading voice assistant..." />}>
        <VoiceChat user={user} onLogout={logout} />
      </Suspense>
    </div>
  )
}

function AppContent() {
  return (
    <Routes>
      <Route path="/sso/callback" element={<SSOCallback />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/chatbot/:workflowId" element={<ChatbotRoute />} />
      <Route path="/workspace/:workspaceId" element={<WorkspaceRoute />} />
      <Route path="/:id" element={<WorkspaceRoute />} />
      <Route path="/*" element={<WorkspaceRoute />} />
    </Routes>
  )
}

function App() {
  return <AppContent />
}

export default App
