import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { healthApi, billingApi, workflowsApi, dashboardApi } from '../../services'
import {
  WorkspacesIcon,
  AgentIcon,
  MCPIcon,
  PlusCircleIcon,
  StarIcon,
} from '../common'
import { usePermissions } from '../../hooks'
import StatCard from './StatCard'
import AgentStatusPanel from './AgentStatusPanel'
import ExecutionChart from './ExecutionChart'
import ActivityFeed from './ActivityFeed'
import RecentWorkflows from './RecentWorkflows'
import './Dashboard.css'

const Dashboard = ({ 
  organizations = [], 
  workspaces = [], 
  agents = [], 
  mcps = [],
  teams = [],
  onNavigate 
}) => {
  const {
    workspaces: workspacePerms,
    workflows: workflowPerms,
    agents: agentPerms,
    mcps: mcpPerms,
    teams: teamPerms,
    billing: billingPerms,
  } = usePermissions()
  const [healthStatus, setHealthStatus] = useState({})
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)
  const [billingData, setBillingData] = useState(null)
  const [plans, setPlans] = useState([])
  const [allWorkflows, setAllWorkflows] = useState([])
  const [dashboardStats, setDashboardStats] = useState(null)
  const [executionTrends, setExecutionTrends] = useState([])
  const [activities, setActivities] = useState([])
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true)

  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true)
    const status = {}

    const adminResult = await healthApi.checkAdminApi()
    status['admin-api'] = {
      name: 'Admin API',
      description: 'Configuration & management',
      ...adminResult,
    }

    const agentResults = await healthApi.checkAllAgents()
    Object.keys(agentResults).forEach(agentId => {
      status[`agent-${agentId}`] = {
        ...agentResults[agentId],
        description: agentResults[agentId].url || 'No URL configured',
      }
    })

    setHealthStatus(status)
    setLastChecked(new Date())
    setIsCheckingHealth(false)
  }, [])

  const loadBillingData = useCallback(async () => {
    if (organizations.length === 0) return
    try {
      const [plansRes, overviewRes] = await Promise.all([
        billingApi.getPlans(),
        billingApi.getOverview(organizations[0]?.id)
      ])
      setPlans(plansRes.data)
      setBillingData(overviewRes.data)
    } catch (err) {
      console.error('Failed to load billing data:', err)
    }
  }, [organizations])

  const loadWorkflowData = useCallback(async () => {
    if (workspaces.length === 0) return
    try {
      const workflowPromises = workspaces.slice(0, 3).map(ws => 
        workflowsApi.getAll(ws.id).catch(() => ({ data: { workflows: [] } }))
      )
      const results = await Promise.all(workflowPromises)
      const workflows = results.flatMap(r => r.data?.workflows || [])
      setAllWorkflows(workflows)
    } catch (err) {
      console.error('Failed to load workflow data:', err)
    }
  }, [workspaces])

  const loadDashboardData = useCallback(async () => {
    setIsLoadingDashboard(true)
    try {
      const [statsRes, trendsRes, activityRes] = await Promise.all([
        dashboardApi.getStats().catch(() => ({ data: null })),
        dashboardApi.getExecutionTrends(7).catch(() => ({ data: { trends: [] } })),
        dashboardApi.getActivity(20).catch(() => ({ data: { activities: [] } })),
      ])
      
      if (statsRes.data?.stats) {
        setDashboardStats(statsRes.data.stats)
      }
      
      if (trendsRes.data?.trends) {
        setExecutionTrends(trendsRes.data.trends)
      }
      
      if (activityRes.data?.activities) {
        setActivities(activityRes.data.activities)
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
    } finally {
      setIsLoadingDashboard(false)
    }
  }, [])

  useEffect(() => {
    checkHealth()
  }, [checkHealth])

  useEffect(() => {
    loadBillingData()
  }, [loadBillingData])

  useEffect(() => {
    loadWorkflowData()
  }, [loadWorkflowData])

  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData])

  const activeWorkspaces = workspaces.filter(t => t.is_active).length
  const onlineAgents = Object.values(healthStatus).filter(s => s.status === 'online').length
  const totalAgents = agents.length

  const getCurrentPlan = () => {
    if (!billingData?.subscription) return plans.find(p => p.id === 'free')
    return plans.find(p => p.id === billingData.subscription.plan) || plans.find(p => p.id === 'free')
  }

  const currentPlan = getCurrentPlan()

  const formatCurrency = (cents) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(cents / 100)
  }

  const formatTrend = (trend) => {
    if (!trend) return null
    const sign = trend.change >= 0 ? '+' : ''
    return `${sign}${trend.change}`
  }

  const stats = [
    {
      label: 'Workspaces',
      value: dashboardStats?.total_workspaces ?? workspaces.length,
      subtext: `${dashboardStats?.active_workspaces ?? activeWorkspaces} active`,
      icon: <WorkspacesIcon size={22} />,
      color: 'emerald',
      trend: dashboardStats?.workspaces_trend?.change >= 0 ? 'up' : 'down',
      trendValue: formatTrend(dashboardStats?.workspaces_trend),
      onClick: () => onNavigate('workspaces')
    },
    {
      label: 'Workflows',
      value: dashboardStats?.total_workflows ?? allWorkflows.length,
      subtext: `${dashboardStats?.active_workflows ?? allWorkflows.filter(w => w.is_active).length} active`,
      icon: '⚡',
      color: 'indigo',
      trend: dashboardStats?.workflows_trend?.change >= 0 ? 'up' : 'down',
      trendValue: formatTrend(dashboardStats?.workflows_trend),
      onClick: () => onNavigate('workflows')
    },
    {
      label: 'Agents',
      value: totalAgents,
      subtext: `${onlineAgents} online`,
      icon: <AgentIcon size={22} />,
      color: 'amber',
      onClick: () => onNavigate('agents')
    },
    {
      label: 'MCP Servers',
      value: mcps.length,
      subtext: `${mcps.filter(m => m.is_system_server).length} system`,
      icon: <MCPIcon size={22} />,
      color: 'violet',
      onClick: () => onNavigate('mcps')
    },
  ]

  return (
    <div className="dashboard">
      <motion.div 
        className="dashboard-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="dashboard-greeting">
          <span className="wave">👋</span>
          <h2>Welcome back</h2>
        </div>
        <p>Here's what's happening with your AI platform</p>
      </motion.div>

      <div className="stats-grid">
        {stats.map((stat, index) => (
          <StatCard
            key={index}
            {...stat}
            delay={index}
          />
        ))}
      </div>

      <div className="dashboard-row">
        <ExecutionChart 
          data={executionTrends}
          isLoading={isLoadingDashboard}
        />
        <ActivityFeed 
          activities={activities}
          isLoading={isLoadingDashboard}
        />
      </div>

      <div className="dashboard-row">
        <RecentWorkflows 
          workflows={allWorkflows}
          onViewAll={() => onNavigate('workflows')}
          onNavigate={onNavigate}
        />
        
        <motion.div
          className="dashboard-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 }}
        >
          <div className="card-header">
            <h3>Quick Actions</h3>
          </div>
          <div className="card-content">
            <div className="quick-actions">
              {workspacePerms.canCreate && (
                <button className="quick-action-btn" onClick={() => onNavigate('workspaces')}>
                  <PlusCircleIcon size={20} />
                  <span>New Workspace</span>
                </button>
              )}
              {workflowPerms.canCreate && (
                <button className="quick-action-btn" onClick={() => onNavigate('workflows')}>
                  <PlusCircleIcon size={20} />
                  <span>New Workflow</span>
                </button>
              )}
              {agentPerms.canCreate && (
                <button className="quick-action-btn" onClick={() => onNavigate('agents')}>
                  <PlusCircleIcon size={20} />
                  <span>Add Agent</span>
                </button>
              )}
              {mcpPerms.canCreate && (
                <button className="quick-action-btn" onClick={() => onNavigate('mcps')}>
                  <PlusCircleIcon size={20} />
                  <span>Add MCP Server</span>
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      <div className="dashboard-row three-col">
        {billingPerms.canView && (
          <motion.div
            className="dashboard-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.6 }}
          >
            <div className="card-header">
              <h3>Billing Overview</h3>
              {billingPerms.canEdit && (
                <button className="card-action" onClick={() => onNavigate('billing')}>Manage</button>
              )}
            </div>
            <div className="card-content">
              <div className="billing-summary">
                <div className="billing-plan">
                  <div className={`plan-badge ${currentPlan?.id === 'free' ? 'free' : ''}`}>
                    {currentPlan?.name || 'Free'}
                  </div>
                  <span className="plan-price">
                    {currentPlan?.price === 0 ? 'Free' : `${formatCurrency(currentPlan?.price || 0)}/mo`}
                  </span>
                </div>
                <div className="billing-metrics">
                  <div className="billing-metric">
                    <div className="metric-header">
                      <span className="metric-label">Workspaces</span>
                      <span className="metric-value">
                        {workspaces.length} / {currentPlan?.limits?.workspaces === -1 ? '∞' : currentPlan?.limits?.workspaces || 2}
                      </span>
                    </div>
                    <div className="metric-bar">
                      <div 
                        className="metric-fill" 
                        style={{ 
                          width: `${Math.min((workspaces.length / (currentPlan?.limits?.workspaces || 2)) * 100, 100)}%`,
                          background: workspaces.length >= (currentPlan?.limits?.workspaces || 2) ? '#f43f5e' : '#10b981'
                        }}
                      />
                    </div>
                  </div>
                  <div className="billing-metric">
                    <div className="metric-header">
                      <span className="metric-label">Teams</span>
                      <span className="metric-value">
                        {teams.length} / {currentPlan?.limits?.teams === -1 ? '∞' : currentPlan?.limits?.teams || 1}
                      </span>
                    </div>
                    <div className="metric-bar">
                      <div 
                        className="metric-fill" 
                        style={{ 
                          width: `${Math.min((teams.length / (currentPlan?.limits?.teams || 1)) * 100, 100)}%`,
                          background: teams.length >= (currentPlan?.limits?.teams || 1) ? '#f43f5e' : '#8b5cf6'
                        }}
                      />
                    </div>
                  </div>
                </div>
                {billingPerms.canEdit && currentPlan?.id === 'free' && (
                  <button className="upgrade-btn" onClick={() => onNavigate('billing')}>
                    <StarIcon size={16} />
                    Upgrade Plan
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}

        <motion.div
          className="dashboard-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.7 }}
        >
          <div className="card-header">
            <h3>Recent Workspaces</h3>
            <button className="card-action" onClick={() => onNavigate('workspaces')}>View All</button>
          </div>
          <div className="card-content">
            {workspaces.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📁</div>
                <h4>No workspaces yet</h4>
                <p>{workspacePerms.canCreate ? 'Create your first workspace to get started' : 'No workspaces available'}</p>
                {workspacePerms.canCreate && (
                  <button className="btn-primary-sm" onClick={() => onNavigate('workspaces')}>
                    Create Workspace
                  </button>
                )}
              </div>
            ) : (
              <div className="workflow-list">
                {workspaces.slice(0, 4).map((workspace, index) => (
                  <motion.div 
                    key={workspace.id} 
                    className="workspace-item"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.7 + index * 0.05 }}
                  >
                    <div className="workspace-info">
                      <div className="workspace-name">{workspace.name}</div>
                      <div className="workspace-org">
                        {organizations.find(o => o.id === workspace.organization_id)?.name || 'Unknown'}
                      </div>
                    </div>
                    <div className={`workspace-status ${workspace.is_active ? 'active' : 'inactive'}`}>
                      {workspace.is_active ? 'Active' : 'Inactive'}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.8 }}
        >
          <div className="card-header">
            <h3>Teams</h3>
            {teamPerms.canEdit && (
              <button className="card-action" onClick={() => onNavigate('teams')}>Manage</button>
            )}
          </div>
          <div className="card-content">
            {teams.length === 0 ? (
              <div className="teams-preview">
                <div className="teams-icon">👥</div>
                <h4>Collaborate with your team</h4>
                <p>{teamPerms.canCreate ? 'Create teams to organize members and manage access' : 'No teams available'}</p>
                {teamPerms.canCreate && (
                  <button className="btn-primary-sm" onClick={() => onNavigate('teams')}>
                    Create Team
                  </button>
                )}
              </div>
            ) : (
              <div className="team-list">
                {teams.slice(0, 4).map((team, index) => (
                  <motion.div 
                    key={team.id} 
                    className="workspace-item"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.8 + index * 0.05 }}
                  >
                    <div className="workspace-info">
                      <div className="workspace-name">{team.name}</div>
                      <div className="workspace-org">{team.member_count || 0} members</div>
                    </div>
                    <div className={`workspace-status ${team.is_active ? 'active' : 'inactive'}`}>
                      {team.is_default ? 'Default' : team.is_active ? 'Active' : 'Inactive'}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </div>

      <AgentStatusPanel
        agents={agents}
        healthStatus={healthStatus}
        isCheckingHealth={isCheckingHealth}
        lastChecked={lastChecked}
        onRefresh={checkHealth}
      />
    </div>
  )
}

export default Dashboard
