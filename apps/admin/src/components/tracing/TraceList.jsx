import React from 'react'
import { motion } from 'framer-motion'

const TraceList = ({ 
  traces, 
  total, 
  limit, 
  offset, 
  isLoading, 
  onSelectTrace,
  onPrevPage,
  onNextPage,
  selectedTraceId,
}) => {
  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const extractMethodPath = (name) => {
    const match = name?.match(/^(GET|POST|PUT|DELETE|PATCH|OPTIONS)\s+(.+)$/)
    if (match) {
      return { method: match[1], path: match[2] }
    }
    return { method: null, path: name }
  }

  if (isLoading) {
    return (
      <div className="traces-list">
        <div className="tracing-loading">
          <div className="loading-spinner" />
          <p>Loading traces...</p>
        </div>
      </div>
    )
  }

  if (!traces || traces.length === 0) {
    return (
      <div className="traces-list">
        <div className="tracing-empty">
          <div className="empty-icon">📊</div>
          <h4>No Traces Found</h4>
          <p>No traces match your current filters, or no traces have been recorded yet.</p>
        </div>
      </div>
    )
  }

  const currentPage = Math.floor(offset / limit) + 1
  const totalPages = Math.ceil(total / limit)

  return (
    <motion.div 
      className="traces-list"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
    >
      <table className="traces-table">
        <thead>
          <tr>
            <th>Trace</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((trace, index) => {
            const { method, path } = extractMethodPath(trace.name)
            const isSelected = selectedTraceId === trace.id
            return (
              <tr 
                key={trace.id || index}
                onClick={() => onSelectTrace(trace)}
                className={isSelected ? 'selected' : ''}
              >
                <td>
                  <div className="trace-name">
                    {method && <code>{method}</code>}
                    {path}
                  </div>
                </td>
                <td>
                  <span className={`trace-status ${trace.status}`}>
                    <span className="status-dot" />
                    {trace.status}
                  </span>
                </td>
                <td>
                  <span className="trace-duration">
                    {formatDuration(trace.duration_ms)}
                  </span>
                </td>
                <td>
                  <span className="trace-time">
                    {formatTime(trace.timestamp)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="traces-pagination">
        <span className="pagination-info">
          Showing {offset + 1}-{Math.min(offset + limit, total)} of {total} traces
        </span>
        <div className="pagination-buttons">
          <button 
            onClick={onPrevPage} 
            disabled={offset === 0}
          >
            Previous
          </button>
          <button 
            onClick={onNextPage} 
            disabled={offset + limit >= total}
          >
            Next
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export default TraceList
