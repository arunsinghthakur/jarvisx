import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

const StatCard = ({ 
  label, 
  value, 
  subtext, 
  icon, 
  color, 
  trend,
  trendValue,
  onClick,
  delay = 0 
}) => {
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    const duration = 1000
    const steps = 30
    const increment = value / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplayValue(value)
        clearInterval(timer)
      } else {
        setDisplayValue(Math.floor(current))
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [value])

  const accentColors = {
    indigo: { bg: 'rgba(99, 102, 241, 0.15)', text: '#6366f1', glow: 'rgba(99, 102, 241, 0.3)' },
    emerald: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', glow: 'rgba(16, 185, 129, 0.3)' },
    amber: { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', glow: 'rgba(245, 158, 11, 0.3)' },
    rose: { bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', glow: 'rgba(244, 63, 94, 0.3)' },
    violet: { bg: 'rgba(139, 92, 246, 0.15)', text: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.3)' },
    cyan: { bg: 'rgba(6, 182, 212, 0.15)', text: '#06b6d4', glow: 'rgba(6, 182, 212, 0.3)' },
  }

  const colorScheme = accentColors[color] || accentColors.indigo

  return (
    <motion.div
      className="stat-card"
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: delay * 0.1 }}
      whileHover={{ scale: 1.02 }}
      style={{ '--card-accent': colorScheme.text }}
    >
      <div className="stat-card-header">
        <div 
          className="stat-icon"
          style={{ 
            backgroundColor: colorScheme.bg,
            color: colorScheme.text,
          }}
        >
          {icon}
        </div>
        {trendValue && (
          <div className={`stat-trend ${trend || 'up'}`}>
            {trend === 'down' ? '↓' : '↑'} {trendValue}
          </div>
        )}
      </div>
      
      <div className="stat-content">
        <motion.div 
          className="stat-value"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: delay * 0.1 + 0.2 }}
        >
          {displayValue}
        </motion.div>
        <div className="stat-label">{label}</div>
        {subtext && <div className="stat-subtext">{subtext}</div>}
      </div>
    </motion.div>
  )
}

export default StatCard
