import React from 'react'
import { motion } from 'framer-motion'

const RecentWorkflows = ({ workflows = [], executions = [], onViewAll, onNavigate }) => {
  const formatTime = (timestamp) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getWorkflowExecutions = () => {
    if (executions.length > 0) {
      return executions.slice(0, 5).map(exec => ({
        id: exec.id,
        name: exec.workflow_name || 'Workflow',
        status: exec.status,
        time: exec.completed_at || exec.started_at || exec.created_at,
        trigger: exec.trigger_type,
      }))
    }

    return workflows.slice(0, 5).map(wf => ({
      id: wf.id,
      name: wf.name,
      status: wf.is_active ? 'active' : 'inactive',
      time: wf.updated_at,
      trigger: wf.trigger_type,
    }))
  }

  const items = getWorkflowExecutions()

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.06
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0 }
  }

  const getTriggerIcon = (trigger) => {
    switch (trigger) {
      case 'manual': return '▶️'
      case 'schedule': return '⏰'
      case 'webhook': return '🔗'
      case 'agent_event': return '🤖'
      default: return '⚡'
    }
  }

  return (
    <motion.div
      className="dashboard-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.4 }}
    >
      <div className="card-header">
        <div className="card-header-left">
          <h3>Recent Workflows</h3>
        </div>
        {onViewAll && (
          <button className="card-action" onClick={onViewAll}>
            View All
          </button>
        )}
      </div>
      <div className="card-content">
        {items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚡</div>
            <h4>No workflows yet</h4>
            <p>Create your first workflow to automate tasks</p>
            {onNavigate && (
              <button className="btn-primary-sm" onClick={() => onNavigate('workflows')}>
                Create Workflow
              </button>
            )}
          </div>
        ) : (
          <motion.div 
            className="workflow-list"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {items.map((item, index) => (
              <motion.div 
                key={item.id || index} 
                className="workflow-item"
                variants={itemVariants}
                whileHover={{ scale: 1.01 }}
              >
                <div className="workflow-info">
                  <div className="workflow-icon">
                    {getTriggerIcon(item.trigger)}
                  </div>
                  <div className="workflow-details">
                    <div className="workflow-name">{item.name}</div>
                    <div className="workflow-meta">
                      {item.trigger && (
                        <span style={{ textTransform: 'capitalize' }}>
                          {item.trigger.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="workflow-status">
                  <span className={`execution-status ${item.status}`}>
                    {item.status}
                  </span>
                  <span className="execution-time">{formatTime(item.time)}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

export default RecentWorkflows
