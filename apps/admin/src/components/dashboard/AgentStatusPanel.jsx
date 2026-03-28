import React from 'react'
import { motion } from 'framer-motion'
import { RefreshIcon } from '../common'

const AgentStatusPanel = ({ 
  agents = [], 
  healthStatus = {}, 
  isCheckingHealth, 
  lastChecked, 
  onRefresh 
}) => {
  const getStatusItems = () => {
    const items = []
    
    if (healthStatus['admin-api']) {
      items.push({
        ...healthStatus['admin-api'],
        name: 'Admin API',
        description: 'Configuration & management',
      })
    }

    agents.forEach(agent => {
      const agentStatus = healthStatus[`agent-${agent.id}`]
      if (agentStatus) {
        let description = agentStatus.url || agent.default_url
        if (!description) {
          if (agentStatus.status === 'in-process' || agentStatus.status === 'dynamic') {
            description = agentStatus.message || 'Runs in-process with orchestrator'
          } else {
            description = 'No URL configured'
          }
        }
        items.push({
          ...agentStatus,
          description,
        })
      } else {
        items.push({
          name: agent.name,
          description: agent.default_url || 'No URL configured',
          status: 'unknown',
        })
      }
    })

    return items
  }

  const statusItems = getStatusItems()
  const onlineCount = Object.values(healthStatus).filter(s => 
    s.status === 'online' || s.status === 'in-process' || s.status === 'dynamic'
  ).length
  const totalServices = Object.keys(healthStatus).length

  const getLatencyClass = (latency) => {
    if (!latency) return ''
    if (latency < 100) return 'fast'
    if (latency < 500) return 'medium'
    return 'slow'
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0 }
  }

  return (
    <div className="dashboard-card full-width">
      <div className="card-header">
        <div className="card-header-left">
          <h3>Platform Status</h3>
          {totalServices > 0 && (
            <span className="status-summary">
              {onlineCount}/{totalServices} online
            </span>
          )}
        </div>
        <div className="card-header-actions">
          {lastChecked && (
            <span className="last-checked">
              Updated {lastChecked.toLocaleTimeString()}
            </span>
          )}
          <button 
            className="refresh-btn" 
            onClick={onRefresh}
            disabled={isCheckingHealth}
            title="Refresh status"
          >
            <RefreshIcon size={16} className={isCheckingHealth ? 'spinning' : ''} />
          </button>
        </div>
      </div>
      <div className="card-content">
        {isCheckingHealth && statusItems.length === 0 ? (
          <div className="loading-state">
            <div className="loading-spinner" />
            <span>Checking service health...</span>
          </div>
        ) : (
          <motion.div 
            className="agent-status-grid"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {statusItems.map((item, index) => (
              <motion.div 
                key={index} 
                className="agent-status-item"
                variants={itemVariants}
              >
                <div className={`status-indicator ${item.status === 'in-process' || item.status === 'dynamic' ? 'online' : item.status}`} />
                <div className="agent-info">
                  <div className="agent-name">{item.name}</div>
                  <div className="agent-url" title={item.description}>
                    {item.description?.length > 35 
                      ? `${item.description.substring(0, 35)}...` 
                      : item.description}
                  </div>
                </div>
                <div className="agent-meta">
                  {item.latency && (
                    <span className={`latency-badge ${getLatencyClass(item.latency)}`}>
                      {item.latency}ms
                    </span>
                  )}
                  <span className={`status-badge ${item.status === 'in-process' || item.status === 'dynamic' ? 'online' : item.status}`}>
                    {item.status === 'online' ? 'Online' 
                      : item.status === 'in-process' ? 'In-Process'
                      : item.status === 'dynamic' ? 'Dynamic'
                      : item.status === 'offline' ? 'Offline' 
                      : 'Unknown'}
                  </span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default AgentStatusPanel
