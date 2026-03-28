import React from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#1c1c26',
        border: '1px solid #2a2a3c',
        borderRadius: '8px',
        padding: '12px 16px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      }}>
        <p style={{ 
          color: '#f4f4f5', 
          fontSize: '13px', 
          fontWeight: 600,
          margin: '0 0 8px 0' 
        }}>
          {label}
        </p>
        {payload.map((entry, index) => (
          <p key={index} style={{ 
            color: entry.color, 
            fontSize: '12px',
            margin: '4px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: entry.color,
            }} />
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

const LoadingSkeleton = () => (
  <div className="chart-loading">
    <div className="skeleton-bar" style={{ height: '60%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '80%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '45%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '70%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '55%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '90%', width: '10%' }} />
    <div className="skeleton-bar" style={{ height: '65%', width: '10%' }} />
  </div>
)

const ExecutionChart = ({ data = [], title = 'Execution Trends', isLoading = false }) => {
  const totalSuccess = data.reduce((sum, d) => sum + (d.success || 0), 0)
  const totalFailed = data.reduce((sum, d) => sum + (d.failed || 0), 0)
  const total = totalSuccess + totalFailed
  const successRate = total > 0 ? Math.round((totalSuccess / total) * 100) : 0

  const hasData = data.length > 0 && total > 0

  return (
    <motion.div
      className="dashboard-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
    >
      <div className="card-header">
        <div className="card-header-left">
          <h3>{title}</h3>
          <span className="card-header-badge">Last 7 days</span>
        </div>
        <div className="card-header-actions">
          {hasData && (
            <>
              <span style={{ 
                fontSize: '24px', 
                fontWeight: 700, 
                color: successRate >= 90 ? '#10b981' : successRate >= 70 ? '#f59e0b' : '#f43f5e'
              }}>
                {successRate}%
              </span>
              <span style={{ fontSize: '12px', color: '#71717a', marginLeft: '4px' }}>success</span>
            </>
          )}
        </div>
      </div>
      <div className="card-content">
        {isLoading ? (
          <LoadingSkeleton />
        ) : !hasData ? (
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <h4>No execution data yet</h4>
            <p>Run some workflows to see execution trends</p>
          </div>
        ) : (
          <>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="failedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="name" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#71717a', fontSize: 11 }}
                    dy={10}
                  />
                  <YAxis 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#71717a', fontSize: 11 }}
                    dx={-10}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="success"
                    name="Successful"
                    stroke="#10b981"
                    strokeWidth={2}
                    fill="url(#successGradient)"
                  />
                  <Area
                    type="monotone"
                    dataKey="failed"
                    name="Failed"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fill="url(#failedGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-legend">
              <div className="legend-item">
                <span className="legend-dot success" />
                <span>Successful ({totalSuccess})</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot failed" />
                <span>Failed ({totalFailed})</span>
              </div>
            </div>
          </>
        )}
      </div>
    </motion.div>
  )
}

export default ExecutionChart
