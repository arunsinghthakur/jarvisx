import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { CloseIcon } from '../common/Icons'
import TraceTree from './TraceTree'
import MessageViewer from './MessageViewer'

const TraceDetailPanel = ({ trace, onClose }) => {
  const [selectedObservation, setSelectedObservation] = useState(null)
  const [activeTab, setActiveTab] = useState('preview')

  if (!trace) return null

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

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const calculateTotalCost = () => {
    let total = 0
    trace.observations?.forEach(obs => {
      if (obs.cost) total += obs.cost
    })
    return total > 0 ? `$${total.toFixed(6)}` : null
  }

  const calculateTotalTokens = () => {
    let prompt = 0, completion = 0, total = 0
    trace.observations?.forEach(obs => {
      if (obs.prompt_tokens) prompt += obs.prompt_tokens
      if (obs.completion_tokens) completion += obs.completion_tokens
      if (obs.total_tokens) total += obs.total_tokens
    })
    return { prompt, completion, total }
  }

  const tokens = calculateTotalTokens()
  const totalCost = calculateTotalCost()

  const handleSelectObservation = (obs) => {
    setSelectedObservation(obs)
    setActiveTab('preview')
  }

  const renderObservationDetail = () => {
    if (!selectedObservation) {
      return (
        <div className="observation-detail-placeholder">
          <p>Select an observation from the tree to view details</p>
        </div>
      )
    }

    return (
      <div className="observation-detail">
        <div className="observation-detail-header">
          <div className="obs-info">
            <span className={`obs-type-badge ${selectedObservation.type?.toLowerCase() || 'span'}`}>
              {selectedObservation.type || 'SPAN'}
            </span>
            <h4>{selectedObservation.name}</h4>
          </div>
          <div className="obs-meta-row">
            <span className="obs-duration">{formatDuration(selectedObservation.duration_ms)}</span>
            {selectedObservation.model && (
              <span className="obs-model">{selectedObservation.model}</span>
            )}
          </div>
        </div>

        {(selectedObservation.total_tokens || selectedObservation.cost) && (
          <div className="observation-stats">
            {selectedObservation.prompt_tokens !== null && (
              <div className="stat">
                <span className="stat-label">Input</span>
                <span className="stat-value">{selectedObservation.prompt_tokens?.toLocaleString()}</span>
              </div>
            )}
            {selectedObservation.completion_tokens !== null && (
              <div className="stat">
                <span className="stat-label">Output</span>
                <span className="stat-value">{selectedObservation.completion_tokens?.toLocaleString()}</span>
              </div>
            )}
            {selectedObservation.total_tokens !== null && (
              <div className="stat total">
                <span className="stat-label">Total</span>
                <span className="stat-value">{selectedObservation.total_tokens?.toLocaleString()}</span>
              </div>
            )}
            {selectedObservation.cost !== null && (
              <div className="stat cost">
                <span className="stat-label">Cost</span>
                <span className="stat-value">${selectedObservation.cost?.toFixed(6)}</span>
              </div>
            )}
          </div>
        )}

        {selectedObservation.model_parameters && Object.keys(selectedObservation.model_parameters).length > 0 && (
          <div className="observation-section">
            <MessageViewer 
              data={selectedObservation.model_parameters} 
              title="Model Parameters"
              defaultView="json"
            />
          </div>
        )}

        {selectedObservation.input && (
          <div className="observation-section">
            <MessageViewer 
              data={selectedObservation.input} 
              title="Input"
              defaultView="pretty"
            />
          </div>
        )}

        {selectedObservation.status_message && (
          <div className="observation-section error-section">
            <h5>Error</h5>
            <pre className="error-message">{selectedObservation.status_message}</pre>
          </div>
        )}

        {selectedObservation.output && (
          <div className="observation-section">
            <MessageViewer 
              data={selectedObservation.output} 
              title="Output"
              defaultView="pretty"
            />
          </div>
        )}

        {selectedObservation.metadata && Object.keys(selectedObservation.metadata).length > 0 && (
          <div className="observation-section">
            <MessageViewer 
              data={selectedObservation.metadata} 
              title="Metadata"
              defaultView="json"
            />
          </div>
        )}
      </div>
    )
  }

  const renderTraceOverview = () => (
    <div className="trace-overview-content">
      {trace.input && (
        <div className="trace-section">
          <MessageViewer 
            data={trace.input} 
            title="Trace Input"
            defaultView="pretty"
          />
        </div>
      )}
      {trace.output && (
        <div className="trace-section">
          <MessageViewer 
            data={trace.output} 
            title="Trace Output"
            defaultView="pretty"
          />
        </div>
      )}
      {trace.metadata && Object.keys(trace.metadata).length > 0 && (
        <div className="trace-section">
          <MessageViewer 
            data={trace.metadata} 
            title="Metadata"
            defaultView="json"
          />
        </div>
      )}
    </div>
  )

  return (
    <motion.div 
      className="trace-detail-panel"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
    >
      <div className="panel-header">
        <div className="panel-title-area">
          <div className="panel-title-row">
            <span className={`trace-status-badge ${trace.status}`}>
              <span className="status-dot" />
              TRACE
            </span>
            <h3>{trace.name}</h3>
          </div>
          <div className="panel-subtitle">
            <span className="trace-time">{formatTime(trace.timestamp)}</span>
          </div>
        </div>
        <button className="panel-close-btn" onClick={onClose}>
          <CloseIcon size={18} />
        </button>
      </div>

      <div className="panel-stats">
        <div className="panel-stat">
          <span className="stat-value">{formatDuration(trace.duration_ms)}</span>
          <span className="stat-label">Duration</span>
        </div>
        {tokens.total > 0 && (
          <div className="panel-stat">
            <span className="stat-value">
              {tokens.prompt.toLocaleString()} → {tokens.completion.toLocaleString()}
              <span className="token-total"> ({tokens.total.toLocaleString()})</span>
            </span>
            <span className="stat-label">Tokens</span>
          </div>
        )}
        {totalCost && (
          <div className="panel-stat cost">
            <span className="stat-value">{totalCost}</span>
            <span className="stat-label">Cost</span>
          </div>
        )}
      </div>

      <div className="panel-tabs">
        <button 
          className={`panel-tab ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          Preview
        </button>
        <button 
          className={`panel-tab ${activeTab === 'scores' ? 'active' : ''}`}
          onClick={() => setActiveTab('scores')}
        >
          Scores
        </button>
      </div>

      <div className="panel-content">
        <div className="panel-left">
          <TraceTree 
            trace={trace}
            observations={trace.observations}
            onSelectObservation={handleSelectObservation}
            selectedObservationId={selectedObservation?.id}
          />
        </div>
        <div className="panel-right">
          {activeTab === 'preview' && (
            selectedObservation ? renderObservationDetail() : renderTraceOverview()
          )}
          {activeTab === 'scores' && (
            <div className="scores-placeholder">
              <p>No scores available</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default TraceDetailPanel
