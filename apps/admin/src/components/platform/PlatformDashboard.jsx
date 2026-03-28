import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { platformApi } from '../../services'
import './Platform.css'

const PlatformDashboard = ({ onNavigate }) => {
  const [overview, setOverview] = useState(null)
  const [organizations, setOrganizations] = useState([])
  const [usageTrends, setUsageTrends] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [overviewRes, orgsRes, trendsRes] = await Promise.all([
        platformApi.getOverview(),
        platformApi.getOrganizations(0, 10),
        platformApi.getUsageTrends(30),
      ])
      
      setOverview(overviewRes.data?.overview)
      setOrganizations(orgsRes.data?.organizations || [])
      setUsageTrends(trendsRes.data?.trends || [])
    } catch (err) {
      console.error('Failed to load platform data:', err)
      setError(err.response?.data?.detail || 'Failed to load platform data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (error) {
    return (
      <div className="platform-dashboard">
        <div className="platform-error">
          <h2>Access Denied</h2>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  const stats = overview ? [
    {
      label: 'Organizations',
      value: overview.total_organizations,
      subtext: `${overview.active_organizations} active`,
      icon: '🏢',
      color: 'emerald',
    },
    {
      label: 'Total Users',
      value: overview.total_users,
      subtext: 'across all orgs',
      icon: '👥',
      color: 'blue',
    },
    {
      label: 'Workspaces',
      value: overview.total_workspaces,
      subtext: 'platform-wide',
      icon: '📁',
      color: 'indigo',
    },
    {
      label: 'Workflows',
      value: overview.total_workflows,
      subtext: 'total created',
      icon: '⚡',
      color: 'amber',
    },
    {
      label: 'System Agents',
      value: overview.system_agents,
      subtext: `${overview.custom_agents} custom`,
      icon: '🤖',
      color: 'violet',
    },
    {
      label: 'System MCPs',
      value: overview.system_mcps,
      subtext: `${overview.custom_mcps} custom`,
      icon: '🔧',
      color: 'rose',
    },
  ] : []

  return (
    <div className="platform-dashboard">
      <motion.div 
        className="platform-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="platform-greeting">
          <span className="icon">🛡️</span>
          <h2>Platform Administration</h2>
        </div>
        <p>Monitor and manage all organizations on the JarvisX platform</p>
      </motion.div>

      {isLoading ? (
        <div className="platform-loading">
          <div className="loading-spinner" />
          <p>Loading platform data...</p>
        </div>
      ) : (
        <>
          <div className="platform-stats-grid">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                className={`platform-stat-card ${stat.color}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <div className="stat-icon">{stat.icon}</div>
                <div className="stat-content">
                  <div className="stat-value">{stat.value}</div>
                  <div className="stat-label">{stat.label}</div>
                  <div className="stat-subtext">{stat.subtext}</div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="platform-row">
            <motion.div
              className="platform-card organizations-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
            >
              <div className="card-header">
                <h3>Organizations</h3>
                <button 
                  className="card-action" 
                  onClick={() => onNavigate('organizations')}
                >
                  View All
                </button>
              </div>
              <div className="card-content">
                <table className="organizations-table">
                  <thead>
                    <tr>
                      <th>Organization</th>
                      <th>Status</th>
                      <th>Users</th>
                      <th>Workspaces</th>
                      <th>Executions (30d)</th>
                      <th>Plan</th>
                    </tr>
                  </thead>
                  <tbody>
                    {organizations.map((org) => (
                      <tr key={org.id}>
                        <td>
                          <div className="org-name">
                            {org.name}
                            {org.is_platform_admin && (
                              <span className="platform-badge">Platform</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className={`status-badge ${org.is_active ? 'active' : 'inactive'}`}>
                            {org.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td>{org.user_count}</td>
                        <td>{org.workspace_count}</td>
                        <td>{org.execution_count_30d}</td>
                        <td>
                          <span className={`plan-badge ${org.subscription_plan}`}>
                            {org.subscription_plan || 'free'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </div>

          <div className="platform-row">
            <motion.div
              className="platform-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
            >
              <div className="card-header">
                <h3>Platform Growth (30 days)</h3>
              </div>
              <div className="card-content">
                <div className="trends-chart">
                  {usageTrends.length > 0 ? (
                    <div className="trends-summary">
                      <div className="trend-item">
                        <span className="trend-label">Organizations</span>
                        <span className="trend-value">
                          {usageTrends[usageTrends.length - 1]?.organizations || 0}
                        </span>
                      </div>
                      <div className="trend-item">
                        <span className="trend-label">Users</span>
                        <span className="trend-value">
                          {usageTrends[usageTrends.length - 1]?.users || 0}
                        </span>
                      </div>
                      <div className="trend-item">
                        <span className="trend-label">Workspaces</span>
                        <span className="trend-value">
                          {usageTrends[usageTrends.length - 1]?.workspaces || 0}
                        </span>
                      </div>
                      <div className="trend-item">
                        <span className="trend-label">Executions Today</span>
                        <span className="trend-value">
                          {usageTrends[usageTrends.length - 1]?.executions || 0}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="no-data">No trend data available</p>
                  )}
                </div>
              </div>
            </motion.div>

            <motion.div
              className="platform-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.5 }}
            >
              <div className="card-header">
                <h3>Quick Actions</h3>
              </div>
              <div className="card-content">
                <div className="quick-actions-grid">
                  <button 
                    className="quick-action-btn"
                    onClick={() => onNavigate('organizations')}
                  >
                    <span className="action-icon">🏢</span>
                    <span>Create Organization</span>
                  </button>
                  <button 
                    className="quick-action-btn"
                    onClick={() => onNavigate('agents')}
                  >
                    <span className="action-icon">🤖</span>
                    <span>Manage System Agents</span>
                  </button>
                  <button 
                    className="quick-action-btn"
                    onClick={() => onNavigate('mcps')}
                  >
                    <span className="action-icon">🔧</span>
                    <span>Manage System MCPs</span>
                  </button>
                  <button 
                    className="quick-action-btn"
                    onClick={() => onNavigate('users')}
                  >
                    <span className="action-icon">👥</span>
                    <span>Manage Users</span>
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </div>
  )
}

export default PlatformDashboard
