import React, { useState, useEffect, useCallback } from 'react'
import { RefreshIcon, ChevronRightIcon, CheckIcon, AlertCircleIcon, CloseIcon } from '../common/Icons'
import { workflowsApi } from '../../services/api'
import './ExecutionHistory.css'

function ExecutionHistory({ workflow, onClose }) {
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const [executionDetails, setExecutionDetails] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)

  const fetchExecutions = useCallback(async () => {
    setLoading(true)
    try {
      const response = await workflowsApi.getExecutions(workflow.id)
      setExecutions(response.data.executions || [])
    } catch (err) {
      console.error('Failed to fetch executions:', err)
    } finally {
      setLoading(false)
    }
  }, [workflow.id])

  useEffect(() => {
    fetchExecutions()
  }, [fetchExecutions])

  const fetchExecutionDetails = async (executionId) => {
    setDetailsLoading(true)
    try {
      const response = await workflowsApi.getExecution(executionId)
      setExecutionDetails(response.data)
    } catch (err) {
      console.error('Failed to fetch execution details:', err)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleSelectExecution = (execution) => {
    setSelectedExecution(execution)
    fetchExecutionDetails(execution.id)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const formatDuration = (start, end) => {
    if (!start || !end) return '-'
    const duration = new Date(end) - new Date(start)
    if (duration < 1000) return `${duration}ms`
    if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`
    return `${Math.floor(duration / 60000)}m ${Math.floor((duration % 60000) / 1000)}s`
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckIcon size={14} />
      case 'failed':
        return <AlertCircleIcon size={14} />
      case 'running':
        return <span className="status-spinner" />
      default:
        return null
    }
  }

  const getTriggerLabel = (triggerType) => {
    const labels = {
      manual: 'Manual',
      schedule: 'Scheduled',
      webhook: 'Webhook',
      agent_event: 'Agent Event',
    }
    return labels[triggerType] || triggerType
  }

  return (
    <div className="execution-history-modal">
      <div className="history-overlay" onClick={onClose} />
      <div className="history-panel">
        <div className="history-header">
          <div className="history-title">
            <h2>Execution History</h2>
            <span className="workflow-name">{workflow.name}</span>
          </div>
          <div className="history-actions">
            <button className="btn-icon" onClick={fetchExecutions} title="Refresh">
              <RefreshIcon size={16} />
            </button>
            <button className="btn-icon" onClick={onClose} title="Close">
              <CloseIcon size={16} />
            </button>
          </div>
        </div>

        <div className="history-content">
          <div className="executions-list">
            {loading ? (
              <div className="list-loading">
                <div className="loading-spinner" />
                <span>Loading executions...</span>
              </div>
            ) : executions.length === 0 ? (
              <div className="list-empty">
                <p>No executions yet</p>
                <span>Run the workflow to see execution history</span>
              </div>
            ) : (
              executions.map((execution) => (
                <div
                  key={execution.id}
                  className={`execution-item ${selectedExecution?.id === execution.id ? 'selected' : ''} ${execution.status}`}
                  onClick={() => handleSelectExecution(execution)}
                >
                  <div className="execution-status">
                    {getStatusIcon(execution.status)}
                  </div>
                  <div className="execution-info">
                    <div className="execution-time">{formatDate(execution.created_at)}</div>
                    <div className="execution-meta">
                      <span className="trigger-type">{getTriggerLabel(execution.trigger_type)}</span>
                      <span className="execution-duration">
                        {formatDuration(execution.started_at, execution.completed_at)}
                      </span>
                    </div>
                  </div>
                  <ChevronRightIcon size={14} />
                </div>
              ))
            )}
          </div>

          <div className="execution-details">
            {!selectedExecution ? (
              <div className="details-empty">
                <p>Select an execution to view details</p>
              </div>
            ) : detailsLoading ? (
              <div className="details-loading">
                <div className="loading-spinner" />
                <span>Loading details...</span>
              </div>
            ) : executionDetails ? (
              <div className="details-content">
                <div className="details-section">
                  <h3>Execution Info</h3>
                  <div className="details-grid">
                    <div className="detail-item">
                      <span className="detail-label">Status</span>
                      <span className={`detail-value status-${executionDetails.status}`}>
                        {executionDetails.status}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Trigger</span>
                      <span className="detail-value">
                        {getTriggerLabel(executionDetails.trigger_type)}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Started</span>
                      <span className="detail-value">
                        {formatDate(executionDetails.started_at)}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Duration</span>
                      <span className="detail-value">
                        {formatDuration(executionDetails.started_at, executionDetails.completed_at)}
                      </span>
                    </div>
                  </div>
                </div>

                {executionDetails.error_message && (
                  <div className="details-section error-section">
                    <h3>Error</h3>
                    <div className="error-message">{executionDetails.error_message}</div>
                  </div>
                )}

                {executionDetails.trigger_data && Object.keys(executionDetails.trigger_data).length > 0 && (
                  <div className="details-section">
                    <h3>Trigger Data</h3>
                    <pre className="json-view">
                      {JSON.stringify(executionDetails.trigger_data, null, 2)}
                    </pre>
                  </div>
                )}

                {executionDetails.logs && executionDetails.logs.length > 0 && (
                  <div className="details-section">
                    <h3>Node Logs</h3>
                    <div className="node-logs">
                      {executionDetails.logs.map((log, index) => (
                        <div key={log.id || index} className={`log-item ${log.status}`}>
                          <div className="log-header">
                            <span className="log-node">{log.node_id}</span>
                            <span className={`log-status ${log.status}`}>{log.status}</span>
                            <span className="log-duration">
                              {formatDuration(log.started_at, log.completed_at)}
                            </span>
                          </div>
                          {log.input_data && (
                            <div className="log-data">
                              <span className="data-label">Input:</span>
                              <pre>{JSON.stringify(log.input_data, null, 2)}</pre>
                            </div>
                          )}
                          {log.output_data && (
                            <div className="log-data">
                              <span className="data-label">Output:</span>
                              <pre>{JSON.stringify(log.output_data, null, 2)}</pre>
                            </div>
                          )}
                          {log.error && (
                            <div className="log-error">
                              <span className="data-label">Error:</span>
                              <pre>{log.error}</pre>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExecutionHistory
