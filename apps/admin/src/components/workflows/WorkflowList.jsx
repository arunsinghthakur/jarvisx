import React, { useState, useEffect, useCallback, useRef } from 'react'
import { PlusIcon, EditIcon, TrashIcon, PlayIcon, HistoryIcon, RefreshIcon, ChatIcon, CopyIcon, ExternalLinkIcon } from '../common/Icons'
import { workflowsApi } from '../../services/api'
import { useToast } from '../common/ToastProvider'
import { usePermissions } from '../../hooks'
import WorkflowEditor from './WorkflowEditor'
import ExecutionHistory from './ExecutionHistory'
import './WorkflowList.css'

function WorkflowList({ workspaceId }) {
  const toast = useToast()
  const { workflows: workflowPerms } = usePermissions()
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState(null)
  const [designingWorkflow, setDesigningWorkflow] = useState(null)
  const [historyWorkflow, setHistoryWorkflow] = useState(null)
  const [executingId, setExecutingId] = useState(null)
  const [pollingEnabled, setPollingEnabled] = useState(false)
  const previousStatuses = useRef({})

  const fetchWorkflows = useCallback(async (silent = false) => {
    if (!workspaceId) return
    
    if (!silent) {
      setLoading(true)
      setError(null)
    }
    
    try {
      const response = await workflowsApi.getAll(workspaceId)
      const fetchedWorkflows = response.data.workflows || []
      
      fetchedWorkflows.forEach(w => {
        const prevStatus = previousStatuses.current[w.id]
        const newStatus = w.last_execution?.status
        
        if (prevStatus && prevStatus !== newStatus) {
          if (newStatus === 'completed') {
            toast.success(`Workflow "${w.name}" completed successfully`)
          } else if (newStatus === 'failed') {
            toast.error(`Workflow "${w.name}" failed`)
          }
        }
        
        previousStatuses.current[w.id] = newStatus
      })
      
      setWorkflows(fetchedWorkflows)
      
      const hasRunning = fetchedWorkflows.some(
        w => w.last_execution?.status === 'running' || w.last_execution?.status === 'pending'
      )
      setPollingEnabled(hasRunning)
    } catch (err) {
      if (!silent) {
        setError(err.response?.data?.detail || err.message || 'Failed to fetch workflows')
      }
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }, [workspaceId, toast])

  useEffect(() => {
    fetchWorkflows()
  }, [fetchWorkflows])

  useEffect(() => {
    if (!pollingEnabled) return
    
    const interval = setInterval(() => {
      fetchWorkflows(true)
    }, 3000)
    
    return () => clearInterval(interval)
  }, [pollingEnabled, fetchWorkflows])

  const handleCreate = async (workflowData) => {
    try {
      await workflowsApi.create(workspaceId, workflowData)
      setShowCreateModal(false)
      fetchWorkflows()
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to create workflow')
    }
  }

  const handleUpdate = async (workflowId, workflowData) => {
    try {
      await workflowsApi.update(workflowId, workflowData)
      setEditingWorkflow(null)
      fetchWorkflows()
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to update workflow')
    }
  }

  const handleDelete = async (workflowId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) return
    
    try {
      await workflowsApi.delete(workflowId)
      fetchWorkflows()
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to delete workflow')
    }
  }

  const handleExecute = async (workflowId) => {
    setExecutingId(workflowId)
    const workflow = workflows.find(w => w.id === workflowId)
    
    try {
      await workflowsApi.execute(workflowId)
      toast.info(`Workflow "${workflow?.name || 'Untitled'}" execution started`)
      setPollingEnabled(true)
      fetchWorkflows(true)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to execute workflow')
    } finally {
      setExecutingId(null)
    }
  }

  const getExecutionStatusBadge = (lastExecution) => {
    if (!lastExecution) {
      return <span className="execution-badge idle">Never run</span>
    }

    const { status } = lastExecution
    const statusLabels = {
      pending: 'Starting...',
      running: 'Running',
      completed: 'Completed',
      failed: 'Failed',
    }
    
    return (
      <span className={`execution-badge ${status}`}>
        {status === 'running' && <span className="badge-spinner" />}
        {statusLabels[status] || status}
      </span>
    )
  }

  const toggleActive = async (workflow) => {
    try {
      await workflowsApi.update(workflow.id, { is_active: !workflow.is_active })
      fetchWorkflows()
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to update workflow')
    }
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getTriggerLabel = (triggerType) => {
    const labels = {
      manual: 'Manual',
      schedule: 'Scheduled',
      webhook: 'Webhook',
      agent_event: 'Agent Event',
      chatbot: 'Chatbot',
    }
    return labels[triggerType] || triggerType
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('URL copied to clipboard')
  }

  const openChatbot = (url) => {
    window.open(url, '_blank')
  }

  if (!workspaceId) {
    return (
      <div className="workflow-list">
        <div className="workflow-empty">
          <p>Please select a workspace to view workflows</p>
        </div>
      </div>
    )
  }

  return (
    <div className="workflow-list">
      <div className="workflow-header">
        <div className="workflow-header-left">
          <span className="workflow-count">{workflows.length} workflow{workflows.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="workflow-header-actions">
          <button className="btn-icon" onClick={fetchWorkflows} title="Refresh">
            <RefreshIcon size={16} />
          </button>
          {workflowPerms.canCreate && (
            <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
              <PlusIcon size={16} />
              <span>New Workflow</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="workflow-error">
          <span>{error}</span>
          <button onClick={fetchWorkflows}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="workflow-loading">
          <div className="loading-spinner" />
          <span>Loading workflows...</span>
        </div>
      ) : workflows.length === 0 ? (
        <div className="workflow-empty">
          <div className="empty-icon">⚡</div>
          <h3>No workflows yet</h3>
          <p>{workflowPerms.canCreate ? 'Create your first workflow to automate tasks' : 'No workflows available in this workspace'}</p>
          {workflowPerms.canCreate && (
            <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
              <PlusIcon size={16} />
              <span>Create Workflow</span>
            </button>
          )}
        </div>
      ) : (
        <div className="workflow-grid">
          {workflows.map((workflow) => (
            <div key={workflow.id} className={`workflow-card ${!workflow.is_active ? 'inactive' : ''}`}>
              <div className="workflow-card-header">
                <div className="workflow-card-title">
                  <h3>{workflow.name}</h3>
                  <div className="workflow-badges">
                    <span className={`trigger-badge ${workflow.trigger_type}`}>
                      {getTriggerLabel(workflow.trigger_type)}
                    </span>
                    {getExecutionStatusBadge(workflow.last_execution)}
                  </div>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={workflow.is_active}
                    onChange={() => toggleActive(workflow)}
                    disabled={!workflowPerms.canEdit}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              
              {workflow.description && (
                <p className="workflow-card-description">{workflow.description}</p>
              )}
              
              <div className="workflow-card-meta">
                <span>Updated {formatDate(workflow.updated_at)}</span>
              </div>
              
              {workflow.trigger_type === 'chatbot' && workflow.trigger_config?.chatbot_url && (
                <div className="chatbot-url-section">
                  <div className="chatbot-url-display">
                    <span className="chatbot-url-text">{workflow.trigger_config.chatbot_url}</span>
                    <button
                      className="btn-icon-small"
                      onClick={() => copyToClipboard(workflow.trigger_config.chatbot_url)}
                      title="Copy URL"
                    >
                      <CopyIcon size={12} />
                    </button>
                  </div>
                </div>
              )}
              
              <div className="workflow-card-actions">
                {workflow.trigger_type === 'chatbot' ? (
                  <button
                    className="btn-action chat"
                    onClick={() => openChatbot(workflow.trigger_config?.chatbot_url)}
                    disabled={!workflow.is_active || !workflow.trigger_config?.chatbot_url}
                    title="Open chatbot"
                  >
                    <ChatIcon size={14} />
                    <span>Open Chat</span>
                  </button>
                ) : workflowPerms.canExecute && (
                  <button
                    className="btn-action run"
                    onClick={() => handleExecute(workflow.id)}
                    disabled={!workflow.is_active || executingId === workflow.id}
                    title="Run workflow"
                  >
                    {executingId === workflow.id ? (
                      <span className="mini-spinner" />
                    ) : (
                      <PlayIcon size={14} />
                    )}
                    <span>Run</span>
                  </button>
                )}
                {workflowPerms.canEdit && (
                  <button
                    className="btn-action design"
                    onClick={() => setDesigningWorkflow(workflow)}
                    title="Design workflow"
                  >
                    <EditIcon size={14} />
                    <span>Design</span>
                  </button>
                )}
                {workflow.trigger_type !== 'chatbot' && (
                  <button
                    className="btn-action"
                    onClick={() => setHistoryWorkflow(workflow)}
                    title="View history"
                  >
                    <HistoryIcon size={14} />
                    <span>History</span>
                  </button>
                )}
                {workflowPerms.canDelete && (
                  <button
                    className="btn-action delete"
                    onClick={() => handleDelete(workflow.id)}
                    title="Delete workflow"
                  >
                    <TrashIcon size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreateModal || editingWorkflow) && (
        <WorkflowModal
          workflow={editingWorkflow}
          onClose={() => {
            setShowCreateModal(false)
            setEditingWorkflow(null)
          }}
          onSave={(data) => {
            if (editingWorkflow) {
              handleUpdate(editingWorkflow.id, data)
            } else {
              handleCreate(data)
            }
          }}
        />
      )}

      {designingWorkflow && (
        <WorkflowEditor
          workflow={designingWorkflow}
          onClose={() => setDesigningWorkflow(null)}
          onSave={async (definition) => {
            const updateData = { definition }
            
            const triggerNode = definition.nodes?.find(n => 
              n.type === 'trigger' || n.type === 'chatbotTrigger'
            )
            if (triggerNode?.data?.config) {
              updateData.trigger_config = triggerNode.data.config
            }
            
            await handleUpdate(designingWorkflow.id, updateData)
            setDesigningWorkflow(null)
          }}
        />
      )}

      {historyWorkflow && (
        <ExecutionHistory
          workflow={historyWorkflow}
          onClose={() => setHistoryWorkflow(null)}
        />
      )}
    </div>
  )
}

function WorkflowModal({ workflow, onClose, onSave }) {
  const [name, setName] = useState(workflow?.name || '')
  const [description, setDescription] = useState(workflow?.description || '')
  const [triggerType, setTriggerType] = useState(workflow?.trigger_type || 'manual')
  const [isActive, setIsActive] = useState(workflow?.is_active ?? true)

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (!name.trim()) {
      alert('Name is required')
      return
    }
    
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      trigger_type: triggerType,
      is_active: isActive,
      definition: workflow?.definition || { nodes: [], edges: [] },
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{workflow ? 'Edit Workflow' : 'Create Workflow'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter workflow name"
              autoFocus
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter workflow description"
              rows={3}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="trigger">Trigger Type</label>
            <select
              id="trigger"
              value={triggerType}
              onChange={(e) => setTriggerType(e.target.value)}
            >
              <option value="manual">Manual</option>
              <option value="schedule">Scheduled (Cron)</option>
              <option value="webhook">Webhook</option>
              <option value="agent_event">Agent Event</option>
              <option value="chatbot">Chatbot App</option>
            </select>
          </div>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
              />
              <span>Active</span>
            </label>
          </div>
          
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {workflow ? 'Save Changes' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default WorkflowList
