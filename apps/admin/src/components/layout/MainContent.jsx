import React, { Suspense, lazy, useState, useMemo, useEffect } from 'react'
import { SectionLoader, WorkspaceSelector } from '../common'

const Dashboard = lazy(() => import('../dashboard/Dashboard'))
const PlatformDashboard = lazy(() => import('../platform/PlatformDashboard'))
const PlatformBilling = lazy(() => import('../platform/PlatformBilling'))
const PlatformSettings = lazy(() => import('../platform/PlatformSettings'))
const OrganizationsList = lazy(() => import('../organizations/OrganizationsList'))
const WorkspacesList = lazy(() => import('../workspaces/WorkspacesList'))
const AgentsList = lazy(() => import('../agents/AgentsList'))
const MCPList = lazy(() => import('../mcps/MCPList'))
const UsersList = lazy(() => import('../users/UsersList'))
const TeamsList = lazy(() => import('../teams/TeamsList'))
const Billing = lazy(() => import('../billing/Billing'))
const LLMSettings = lazy(() => import('../llm-settings/LLMSettings'))
const Settings = lazy(() => import('../settings/Settings'))
const KnowledgeBase = lazy(() => import('../knowledge-base/KnowledgeBase'))
const WorkflowList = lazy(() => import('../workflows/WorkflowList'))
const ComplianceDashboard = lazy(() => import('../compliance/ComplianceDashboard'))
const ComplianceSettings = lazy(() => import('../compliance/ComplianceSettings'))
const PIIPatterns = lazy(() => import('../compliance/PIIPatterns'))
const PolicyRules = lazy(() => import('../compliance/PolicyRules'))
const AuditLogs = lazy(() => import('../compliance/AuditLogs'))
const TracingPage = lazy(() => import('../tracing/TracingPage'))

function MainContent({
  activeSection,
  setActiveSection,
  isPlatformAdmin,
  currentOrganization,
  organizations,
  workspaces,
  availableAgents,
  availableMcps,
  teams,
  organizationsLoading,
  workspacesLoading,
  availableAgentsLoading,
  availableMcpsLoading,
  orgActions,
  workspaceActions,
  agentActions,
  mcpActions,
  loadWorkspaceDetails,
}) {
  const filteredWorkspaces = useMemo(() => {
    if (!currentOrganization?.id) return []
    return workspaces.filter(ws => ws.organization_id === currentOrganization.id)
  }, [workspaces, currentOrganization?.id])

  const filteredTeams = useMemo(() => {
    if (!currentOrganization?.id) return []
    return teams.filter(team => team.organization_id === currentOrganization.id)
  }, [teams, currentOrganization?.id])
  const [showCreateOrgModal, setShowCreateOrgModal] = useState(false)
  const [showCreateWorkspaceModal, setShowCreateWorkspaceModal] = useState(false)
  const [showAddAgentModal, setShowAddAgentModal] = useState(false)
  const [showAddMCPModal, setShowAddMCPModal] = useState(false)
  
  const [selectedWorkflowWorkspaceId, setSelectedWorkflowWorkspaceId] = useState(null)
  const [selectedTeamsWorkspaceId, setSelectedTeamsWorkspaceId] = useState(null)
  
  useEffect(() => {
    if (filteredWorkspaces.length > 0 && !selectedWorkflowWorkspaceId) {
      setSelectedWorkflowWorkspaceId(filteredWorkspaces[0].id)
    }
    if (filteredWorkspaces.length > 0 && !selectedTeamsWorkspaceId) {
      setSelectedTeamsWorkspaceId(filteredWorkspaces[0].id)
    }
  }, [filteredWorkspaces, selectedWorkflowWorkspaceId, selectedTeamsWorkspaceId])
  
  useEffect(() => {
    setSelectedWorkflowWorkspaceId(null)
    setSelectedTeamsWorkspaceId(null)
  }, [currentOrganization?.id])

  const [newOrganization, setNewOrganization] = useState({ name: '', description: '' })
  const [newWorkspace, setNewWorkspace] = useState({
    organization_id: null,
    name: '',
    description: '',
  })
  const [newAgent, setNewAgent] = useState({
    id: '',
    name: '',
    description: '',
    default_url: '',
    health_endpoint: '',
  })
  const [newMCP, setNewMCP] = useState({
    id: '',
    name: '',
    description: '',
    default_config: null,
  })

  const handleCreateOrganization = async () => {
    const success = await orgActions.createOrganization(newOrganization)
    if (success) {
      setShowCreateOrgModal(false)
      setNewOrganization({ name: '', description: '' })
    }
  }

  const handleCreateWorkspace = async (workspaceData) => {
    const data = workspaceData || newWorkspace
    const success = await workspaceActions.createWorkspace(data)
    if (success) {
      setShowCreateWorkspaceModal(false)
      setNewWorkspace({
        organization_id: '',
        name: '',
        description: '',
      })
    }
  }

  const handleCreateAgent = async (agentData) => {
    const data = agentData || newAgent
    const success = await agentActions.createAgent(data)
    if (success) {
      setShowAddAgentModal(false)
      setNewAgent({ id: '', name: '', description: '', default_url: '', health_endpoint: '', is_dynamic_agent: true, system_prompt: '', llm_config_id: '', mcp_server_ids: [] })
    }
  }

  const handleCreateMCP = async () => {
    const success = await mcpActions.createMCP(newMCP)
    if (success) {
      setShowAddMCPModal(false)
      setNewMCP({ id: '', name: '', description: '', default_config: null })
    }
  }

  const renderContent = () => {
    switch (activeSection) {
      case 'platform':
        return isPlatformAdmin ? (
          <PlatformDashboard
            onNavigate={setActiveSection}
          />
        ) : (
          <div className="access-denied">
            <h2>Access Restricted</h2>
            <p>Platform dashboard is only available to platform administrators.</p>
          </div>
        )
      case 'dashboard':
        return (
          <Dashboard
            organizations={currentOrganization ? [currentOrganization] : []}
            workspaces={filteredWorkspaces}
            agents={availableAgents}
            mcps={availableMcps}
            teams={filteredTeams}
            onNavigate={setActiveSection}
            isPlatformAdmin={isPlatformAdmin}
          />
        )
      case 'platform-billing':
        return isPlatformAdmin ? (
          <PlatformBilling />
        ) : (
          <div className="access-denied">
            <h2>Access Restricted</h2>
            <p>Platform billing is only available to platform administrators.</p>
          </div>
        )
      case 'platform-settings':
        return isPlatformAdmin ? (
          <PlatformSettings />
        ) : (
          <div className="access-denied">
            <h2>Access Restricted</h2>
            <p>Platform settings are only available to platform administrators.</p>
          </div>
        )
      case 'organizations':
        return isPlatformAdmin ? (
          <OrganizationsList
            organizations={organizations}
            workspaces={workspaces}
            loading={organizationsLoading}
            onCreateOrganization={handleCreateOrganization}
            onUpdateOrganization={orgActions.updateOrganization}
            onDeleteOrganization={orgActions.deleteOrganization}
            newOrganization={newOrganization}
            setNewOrganization={setNewOrganization}
            showCreateModal={showCreateOrgModal}
            setShowCreateModal={setShowCreateOrgModal}
            createLoading={orgActions.loading}
            createdOrgCredentials={orgActions.createdOrgCredentials}
            onDismissCredentials={orgActions.dismissCredentials}
          />
        ) : (
          <div className="access-denied">
            <h2>Access Restricted</h2>
            <p>Organization management is only available to platform administrators.</p>
          </div>
        )
      case 'workspaces':
        return (
          <WorkspacesList
            workspaces={workspaces}
            organizations={organizations}
            loading={workspacesLoading}
            onCreateWorkspace={handleCreateWorkspace}
            onUpdateWorkspace={workspaceActions.updateWorkspace}
            onDeleteWorkspace={workspaceActions.deleteWorkspace}
            newWorkspace={newWorkspace}
            setNewWorkspace={setNewWorkspace}
            showCreateModal={showCreateWorkspaceModal}
            setShowCreateModal={setShowCreateWorkspaceModal}
            createLoading={workspaceActions.loading}
            isPlatformAdmin={isPlatformAdmin}
            currentOrganization={currentOrganization}
          />
        )
      case 'agents':
        return (
          <AgentsList
            agents={availableAgents}
            loading={availableAgentsLoading || agentActions.loading}
            onCreateAgent={handleCreateAgent}
            onUpdateAgent={agentActions.updateAgent}
            onDeleteAgent={agentActions.deleteAgent}
            newAgent={newAgent}
            setNewAgent={setNewAgent}
            showCreateModal={showAddAgentModal}
            setShowCreateModal={setShowAddAgentModal}
            createLoading={agentActions.loading}
            availableMcps={availableMcps}
            availableAgents={availableAgents}
            organizationId={currentOrganization?.id}
          />
        )
      case 'mcps':
        return (
          <MCPList
            mcps={availableMcps}
            workspaces={filteredWorkspaces}
            loading={availableMcpsLoading || mcpActions.loading}
            onCreateMCP={handleCreateMCP}
            onUpdateMCP={mcpActions.updateMCP}
            onDeleteMCP={mcpActions.deleteMCP}
            newMCP={newMCP}
            setNewMCP={setNewMCP}
            showCreateModal={showAddMCPModal}
            setShowCreateModal={setShowAddMCPModal}
            createLoading={mcpActions.loading}
            availableAgents={availableAgents}
            onUpdateMCPConnections={mcpActions.updateMCPConnections}
            isPlatformAdmin={isPlatformAdmin}
            currentOrganization={currentOrganization}
          />
        )
      case 'users':
        return (
          <UsersList
            organizations={organizations}
            isPlatformAdmin={isPlatformAdmin}
            currentOrganization={currentOrganization}
          />
        )
      case 'teams':
        return (
          <div className="section-with-selector">
            <div className="section-header-bar">
              <h2>Teams</h2>
              <WorkspaceSelector
                workspaces={filteredWorkspaces}
                selectedId={selectedTeamsWorkspaceId}
                onChange={setSelectedTeamsWorkspaceId}
                label="Workspace"
                placeholder="Select a workspace"
              />
            </div>
            <TeamsList
              organizations={organizations}
              isPlatformAdmin={isPlatformAdmin}
              currentOrganization={currentOrganization}
              workspaces={filteredWorkspaces}
              selectedWorkspaceId={selectedTeamsWorkspaceId}
            />
          </div>
        )
      case 'billing':
        return (
          <Billing
            organizations={currentOrganization ? [currentOrganization] : []}
            workspaces={filteredWorkspaces}
            teams={filteredTeams}
            isPlatformAdmin={isPlatformAdmin}
            currentOrganization={currentOrganization}
          />
        )
      case 'llm-settings':
        return (
          <LLMSettings
            currentOrganization={currentOrganization}
          />
        )
      case 'settings':
        return (
          <Settings
            currentOrganization={currentOrganization}
          />
        )
      case 'knowledge-base':
        return (
          <KnowledgeBase
            organizations={organizations}
            isPlatformAdmin={isPlatformAdmin}
            currentOrganization={currentOrganization}
          />
        )
      case 'workflows':
        return (
          <div className="section-with-selector">
            <div className="section-header-bar">
              <h2>Workflows</h2>
              <WorkspaceSelector
                workspaces={filteredWorkspaces}
                selectedId={selectedWorkflowWorkspaceId}
                onChange={setSelectedWorkflowWorkspaceId}
                label="Workspace"
                placeholder="Select a workspace"
              />
            </div>
            <WorkflowList
              workspaceId={selectedWorkflowWorkspaceId}
            />
          </div>
        )
      case 'compliance-dashboard':
        return <ComplianceDashboard />
      case 'compliance-settings':
        return <ComplianceSettings />
      case 'pii-patterns':
        return <PIIPatterns />
      case 'policy-rules':
        return <PolicyRules />
      case 'audit-logs':
        return <AuditLogs />
      case 'tracing':
        return <TracingPage />
      default:
        return null
    }
  }

  return (
    <Suspense fallback={<SectionLoader message={`Loading ${activeSection}...`} />}>
      {renderContent()}
    </Suspense>
  )
}

export default MainContent

