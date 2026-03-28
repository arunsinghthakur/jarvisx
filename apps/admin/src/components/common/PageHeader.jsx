import React from 'react'
import { motion } from 'framer-motion'

const PageHeader = ({ 
  icon, 
  title, 
  subtitle, 
  action,
  actionLabel = 'Add New',
  onAction 
}) => {
  return (
    <motion.div 
      className="page-header"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="page-header-content">
        <div className="page-title">
          {icon && <span className="page-icon">{icon}</span>}
          <h2>{title}</h2>
        </div>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {(action || onAction) && (
        <div className="page-header-actions">
          {action || (
            <button className="btn btn-primary" onClick={onAction}>
              {actionLabel}
            </button>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default PageHeader
