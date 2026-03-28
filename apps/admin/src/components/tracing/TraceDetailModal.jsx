import React from 'react'
import { motion } from 'framer-motion'
import { CloseIcon } from '../common/Icons'

const TraceDetailModal = ({ trace, onClose }) => {
  if (!trace) return null

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const formatJson = (data) => {
    if (!data) return 'null'
    try {
      if (typeof data === 'string') {
        return data
      }
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <motion.div 
      className="trace-detail-modal"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={handleBackdropClick}
    >
      <motion.div 
        className="trace-detail-content"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
      >
        <div className="trace-detail-header">
          <h3>
            <span className={`trace-status ${trace.status}`}>
              <span className="status-dot" />
            </span>
            Trace Details
          </h3>
          <button className="close-btn" onClick={onClose}>
            <CloseIcon size={18} />
          </button>
        </div>

        <div className="trace-detail-body">
          <div className="trace-overview">
            <div className="trace-overview-item">
              <div className="label">Name</div>
              <div className="value">{trace.name || '-'}</div>
            </div>
            <div className="trace-overview-item">
              <div className="label">Status</div>
              <div className="value">
                <span className={`trace-status ${trace.status}`}>
                  <span className="status-dot" />
                  {trace.status}
                </span>
              </div>
            </div>
            <div className="trace-overview-item">
              <div className="label">Duration</div>
              <div className="value">{formatDuration(trace.duration_ms)}</div>
            </div>
            <div className="trace-overview-item">
              <div className="label">Timestamp</div>
              <div className="value">{formatTime(trace.timestamp)}</div>
            </div>
          </div>

          {trace.observations && trace.observations.length > 0 && (
            <div className="observations-section">
              <h4>Observations ({trace.observations.length})</h4>
              <div className="observations-timeline">
                {trace.observations.map((obs, index) => (
                  <div 
                    key={obs.id || index} 
                    className={`observation-item ${obs.type?.toLowerCase() || ''} ${obs.level === 'ERROR' ? 'error' : ''}`}
                  >
                    <div className="observation-header">
                      <div className="observation-name">
                        {obs.name}
                        <span className={`observation-type ${obs.type?.toLowerCase() || ''}`}>
                          {obs.type || 'SPAN'}
                        </span>
                      </div>
                      <div className="observation-meta">
                        <span>{formatDuration(obs.duration_ms)}</span>
                        {obs.model && <span className="model-badge">🤖 {obs.model}</span>}
                      </div>
                    </div>
                    
                    {(obs.total_tokens || obs.prompt_tokens || obs.completion_tokens) && (
                      <div className="observation-tokens">
                        <div className="token-stats">
                          {obs.prompt_tokens !== null && (
                            <span className="token-stat">
                              <span className="token-label">Input:</span> 
                              <span className="token-value">{obs.prompt_tokens?.toLocaleString()}</span>
                            </span>
                          )}
                          {obs.completion_tokens !== null && (
                            <span className="token-stat">
                              <span className="token-label">Output:</span> 
                              <span className="token-value">{obs.completion_tokens?.toLocaleString()}</span>
                            </span>
                          )}
                          {obs.total_tokens !== null && (
                            <span className="token-stat total">
                              <span className="token-label">Total:</span> 
                              <span className="token-value">{obs.total_tokens?.toLocaleString()}</span>
                            </span>
                          )}
                          {obs.cost !== null && obs.cost !== undefined && (
                            <span className="token-stat cost">
                              <span className="token-label">Cost:</span> 
                              <span className="token-value">${obs.cost.toFixed(6)}</span>
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {obs.model_parameters && Object.keys(obs.model_parameters).length > 0 && (
                      <div className="observation-params">
                        <details>
                          <summary>Model Parameters</summary>
                          <pre>{formatJson(obs.model_parameters)}</pre>
                        </details>
                      </div>
                    )}
                    
                    {obs.input && (
                      <div className="observation-content">
                        <details>
                          <summary>Input</summary>
                          <pre>{formatJson(obs.input)}</pre>
                        </details>
                      </div>
                    )}
                    
                    {obs.status_message && (
                      <div className="observation-content error-message">
                        <pre>{obs.status_message}</pre>
                      </div>
                    )}
                    
                    {obs.output && (
                      <div className="observation-content">
                        <details>
                          <summary>Output</summary>
                          <pre>{formatJson(obs.output)}</pre>
                        </details>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!trace.observations || trace.observations.length === 0) && (
            <div className="no-observations">
              No observations recorded for this trace.
            </div>
          )}

          {trace.metadata && Object.keys(trace.metadata).length > 0 && (
            <div className="metadata-section">
              <h4>Metadata</h4>
              <pre>{formatJson(trace.metadata)}</pre>
            </div>
          )}

          {trace.output && (
            <div className="metadata-section">
              <h4>Output</h4>
              <pre>{formatJson(trace.output)}</pre>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

export default TraceDetailModal
