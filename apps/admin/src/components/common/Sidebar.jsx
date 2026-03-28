import React, { useMemo } from 'react'
import {
  DashboardIcon,
  OrganizationIcon,
  WorkspacesIcon,
  AgentIcon,
  MCPIcon,
  TeamsIcon,
  UsersIcon,
  BillingIcon,
  SettingsIcon,
  KnowledgeBaseIcon,
  WorkflowIcon,
  ShieldIcon,
  ActivityIcon,
} from './Icons'
import { usePermissions } from '../../hooks'
import './Sidebar.css'

const Sidebar = ({ activeSection, onSectionChange, isPlatformAdmin = false, complianceEnabled = false }) => {
  const {
    workspaces,
    agents,
    mcps,
    workflows,
    teams,
    users,
    settings,
    knowledgeBase,
    billing,
    organizations,
  } = usePermissions()

  const platformGroup = {
    title: 'Platform',
    items: [
      { id: 'platform', label: 'Platform Dashboard', icon: <DashboardIcon /> },
      { id: 'organizations', label: 'Organizations', icon: <OrganizationIcon />, visible: organizations.canView },
      { id: 'platform-billing', label: 'Platform Billing', icon: <BillingIcon />, visible: billing.canView },
      { id: 'platform-settings', label: 'Platform Settings', icon: <BillingIcon /> },
    ]
  }

  const menuGroups = useMemo(() => [
    ...(isPlatformAdmin ? [platformGroup] : []),
    {
      title: 'Overview',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
      ]
    },
    {
      title: 'AI Studio',
      items: [
        { id: 'workspaces', label: 'Workspaces', icon: <WorkspacesIcon />, visible: workspaces.canView },
        { id: 'agents', label: 'Agents', icon: <AgentIcon />, visible: agents.canView },
        { id: 'mcps', label: 'MCP Servers', icon: <MCPIcon />, visible: mcps.canView },
        { id: 'knowledge-base', label: 'Knowledge Base', icon: <KnowledgeBaseIcon />, visible: knowledgeBase.canView },
        { id: 'workflows', label: 'Workflows', icon: <WorkflowIcon />, visible: workflows.canView },
        { id: 'settings', label: 'Settings', icon: <SettingsIcon />, visible: settings.llmConfigs.canView || settings.ssoConfigs.canView || settings.integrations.canView },
      ]
    },
    {
      title: 'Observability',
      items: [
        { id: 'tracing', label: 'Traces & Logs', icon: <ActivityIcon /> },
      ]
    },
    ...(complianceEnabled ? [{
      title: 'Compliance',
      items: [
        { id: 'compliance-dashboard', label: 'Overview', icon: <ShieldIcon />, visible: settings.compliance.canView },
        { id: 'compliance-settings', label: 'Settings', icon: <SettingsIcon />, visible: settings.compliance.canView },
        { id: 'pii-patterns', label: 'PII Patterns', icon: <ShieldIcon />, visible: settings.compliance.canView },
        { id: 'policy-rules', label: 'Policy Rules', icon: <ShieldIcon />, visible: settings.compliance.canView },
        { id: 'audit-logs', label: 'Audit Logs', icon: <ShieldIcon />, visible: settings.compliance.canView },
      ]
    }] : []),
    {
      title: 'Administration',
      items: [
        { id: 'users', label: 'Users', icon: <UsersIcon />, visible: users.canView },
        { id: 'teams', label: 'Teams', icon: <TeamsIcon />, visible: teams.canView },
        { id: 'billing', label: 'Billing', icon: <BillingIcon />, disabled: true, visible: billing.canView },
      ]
    },
  ], [isPlatformAdmin, complianceEnabled, workspaces, agents, mcps, workflows, teams, users, settings, knowledgeBase, billing, organizations])

  const filteredMenuGroups = useMemo(() => {
    return menuGroups
      .map(group => ({
        ...group,
        items: group.items.filter(item => item.visible !== false)
      }))
      .filter(group => group.items.length > 0)
  }, [menuGroups])

  return (
    <nav className="sidebar">
      <div className="sidebar-nav">
        {filteredMenuGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="sidebar-group">
            <div className="sidebar-group-title">{group.title}</div>
            <div className="sidebar-group-items">
              {group.items.map(item => (
                <button
                  key={item.id}
                  className={`sidebar-item ${activeSection === item.id ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`}
                  onClick={() => !item.disabled && onSectionChange(item.id)}
                  disabled={item.disabled}
                  title={item.disabled ? 'Coming soon' : item.label}
                >
                  <span className="sidebar-item-icon">{item.icon}</span>
                  <span className="sidebar-item-label">{item.label}</span>
                  {item.disabled && <span className="sidebar-item-badge">Soon</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </nav>
  )
}

export default Sidebar
