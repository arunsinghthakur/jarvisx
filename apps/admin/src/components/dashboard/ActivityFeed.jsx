import React from 'react'
import { motion } from 'framer-motion'

const ActivityFeed = ({ activities = [], onViewAll, isLoading = false }) => {
  const getActivityIcon = (type) => {
    switch (type) {
      case 'workflow':
      case 'workflow_completed':
      case 'workflow_started':
        return { icon: '⚡', className: 'workflow' }
      case 'workflow_failed':
        return { icon: '⚠️', className: 'error' }
      case 'agent':
      case 'agent_response':
        return { icon: '🤖', className: 'agent' }
      case 'workspace':
      case 'workspace_created':
        return { icon: '📁', className: 'workspace' }
      case 'error':
        return { icon: '❌', className: 'error' }
      case 'system':
      default:
        return { icon: '🔔', className: 'system' }
    }
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Just now'
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  }

  const LoadingSkeleton = () => (
    <div className="activity-feed">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="activity-item skeleton">
          <div className="activity-icon skeleton-icon" />
          <div className="activity-content">
            <div className="skeleton-text" style={{ width: '80%' }} />
            <div className="skeleton-text" style={{ width: '40%', marginTop: '8px' }} />
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <motion.div
      className="dashboard-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      <div className="card-header">
        <div className="card-header-left">
          <h3>Recent Activity</h3>
          {activities.length > 0 && <span className="card-header-badge">Live</span>}
        </div>
        {onViewAll && (
          <button className="card-action" onClick={onViewAll}>
            View All
          </button>
        )}
      </div>
      <div className="card-content">
        {isLoading ? (
          <LoadingSkeleton />
        ) : activities.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h4>No recent activity</h4>
            <p>Activities will appear here as you use the platform</p>
          </div>
        ) : (
          <motion.div 
            className="activity-feed"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {activities.map((activity, index) => {
              const { icon, className } = getActivityIcon(activity.type)
              return (
                <motion.div 
                  key={activity.id || index} 
                  className="activity-item"
                  variants={itemVariants}
                >
                  <div className={`activity-icon ${className}`}>
                    {icon}
                  </div>
                  <div className="activity-content">
                    <div 
                      className="activity-title"
                      dangerouslySetInnerHTML={{ __html: activity.title }}
                    />
                    <div className="activity-meta">
                      <span className="activity-time">
                        {formatTime(activity.timestamp)}
                      </span>
                      {activity.meta && (
                        <>
                          <span>•</span>
                          <span>{activity.meta}</span>
                        </>
                      )}
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

export default ActivityFeed
