import React, { useState, useEffect } from 'react'
import { llmConfigsApi } from '../../services'

const AddAgentModal = ({
  visible,
  newAgent,
  setNewAgent,
  onCreate,
  onClose,
  loading = false,
  availableMcps = [],
  organizationId,
}) => {
  const [agentType, setAgentType] = useState('dynamic')
  const [selectedMcps, setSelectedMcps] = useState(new Set())
  const [llmConfigs, setLlmConfigs] = useState([])
  const [loadingConfigs, setLoadingConfigs] = useState(false)

  useEffect(() => {
    if (visible && organizationId) {
      loadLlmConfigs()
    }
  }, [visible, organizationId])

  const loadLlmConfigs = async () => {
    if (!organizationId) return
    setLoadingConfigs(true)
    try {
      const res = await llmConfigsApi.getAll(organizationId)
      setLlmConfigs(res.data.configs || [])
    } catch (err) {
      console.error('Failed to load LLM configs:', err)
    } finally {
      setLoadingConfigs(false)
    }
  }

  useEffect(() => {
    if (visible) {
      setAgentType('dynamic')
      setSelectedMcps(new Set())
      setNewAgent({
        id: '',
        name: '',
        description: '',
        default_url: '',
        health_endpoint: '',
        is_dynamic_agent: true,
        system_prompt: '',
        llm_config_id: '',
        mcp_server_ids: [],
      })
    }
  }, [visible, setNewAgent])

  const handleAgentTypeChange = (type) => {
    setAgentType(type)
    setNewAgent({
      ...newAgent,
      is_dynamic_agent: type === 'dynamic',
      default_url: type === 'dynamic' ? '' : newAgent.default_url,
      system_prompt: type === 'dynamic' ? newAgent.system_prompt : '',
      llm_config_id: type === 'dynamic' ? newAgent.llm_config_id : '',
    })
  }

  const handleMcpToggle = (mcpId) => {
    const newSet = new Set(selectedMcps)
    if (newSet.has(mcpId)) {
      newSet.delete(mcpId)
    } else {
      newSet.add(mcpId)
    }
    setSelectedMcps(newSet)
    setNewAgent({
      ...newAgent,
      mcp_server_ids: Array.from(newSet),
    })
  }

  const handleCreate = () => {
    onCreate(newAgent)
  }

  const isValid = () => {
    if (!newAgent.name) return false
    if (agentType === 'dynamic') {
      return newAgent.system_prompt && newAgent.llm_config_id
    } else {
      return newAgent.default_url && newAgent.default_url.startsWith('http')
    }
  }

  const getProviderColor = (provider) => {
    const colors = {
      openai: '#10a37f',
      anthropic: '#cc785c',
      azure_openai: '#0078d4',
      google_vertex: '#4285f4',
      litellm: '#8b5cf6',
      custom: '#6b7280',
    }
    return colors[provider] || '#6b7280'
  }

  if (!visible) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <h2>Add Custom Agent</h2>
        
        <div className="form-group">
          <label>Agent Type</label>
          <div className="agent-type-selector">
            <button
              type="button"
              className={`type-option ${agentType === 'dynamic' ? 'selected' : ''}`}
              onClick={() => handleAgentTypeChange('dynamic')}
            >
              <span className="type-icon">⚡</span>
              <span className="type-label">Dynamic Agent</span>
              <span className="type-desc">Runs directly on the platform</span>
            </button>
            <button
              type="button"
              className={`type-option ${agentType === 'external' ? 'selected' : ''}`}
              onClick={() => handleAgentTypeChange('external')}
            >
              <span className="type-icon">🔗</span>
              <span className="type-label">External A2A Agent</span>
              <span className="type-desc">Points to external URL</span>
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Name *</label>
          <input
            type="text"
            value={newAgent.name}
            onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
            placeholder="My Custom Agent"
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={newAgent.description}
            onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
            placeholder="What does this agent do?"
            rows={2}
          />
        </div>

        {agentType === 'dynamic' ? (
          <>
            <div className="form-group">
              <label>System Prompt *</label>
              <textarea
                value={newAgent.system_prompt}
                onChange={(e) => setNewAgent({ ...newAgent, system_prompt: e.target.value })}
                placeholder="You are a helpful assistant that..."
                rows={6}
                style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
              />
              <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                The instructions that define this agent's behavior and capabilities
              </small>
            </div>

            <div className="form-group">
              <label>LLM Configuration *</label>
              {loadingConfigs ? (
                <div style={{ padding: '1rem', color: '#666' }}>Loading configurations...</div>
              ) : llmConfigs.length === 0 ? (
                <div style={{ padding: '1rem', background: '#fff3cd', borderRadius: '4px', color: '#856404' }}>
                  No LLM configurations found. Please add an LLM configuration in LLM Settings first.
                </div>
              ) : (
                <div className="llm-config-selector" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {llmConfigs.filter(c => c.is_active).map((config) => (
                    <label
                      key={config.id}
                      className={`llm-config-option ${newAgent.llm_config_id === config.id ? 'selected' : ''}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0.75rem',
                        border: newAgent.llm_config_id === config.id ? '2px solid #4CAF50' : '1px solid #ddd',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        background: newAgent.llm_config_id === config.id ? '#f0fff0' : '#fff',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <input
                        type="radio"
                        name="llm_config"
                        value={config.id}
                        checked={newAgent.llm_config_id === config.id}
                        onChange={() => setNewAgent({ ...newAgent, llm_config_id: config.id })}
                        style={{ marginRight: '0.75rem' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontWeight: 600 }}>{config.name}</span>
                          {config.is_default && (
                            <span style={{ fontSize: '0.7rem', background: '#4CAF50', color: 'white', padding: '2px 6px', borderRadius: '4px' }}>
                              Default
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem', display: 'flex', gap: '1rem' }}>
                          <span style={{ 
                            display: 'inline-flex', 
                            alignItems: 'center',
                            backgroundColor: `${getProviderColor(config.provider)}20`,
                            color: getProviderColor(config.provider),
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                          }}>
                            {config.provider}
                          </span>
                          <span>{config.model_name}</span>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {availableMcps.length > 0 && (
              <div className="form-group">
                <label>MCP Tools (Optional)</label>
                <small style={{ color: '#666', display: 'block', marginBottom: '0.5rem' }}>
                  Select tools this agent can use
                </small>
                <div className="mcp-selector" style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '4px', padding: '0.5rem' }}>
                  {availableMcps.map((mcp) => (
                    <label key={mcp.id} className="mcp-option" style={{ display: 'flex', alignItems: 'center', padding: '0.5rem', cursor: 'pointer', borderBottom: '1px solid #eee' }}>
                      <input
                        type="checkbox"
                        checked={selectedMcps.has(mcp.id)}
                        onChange={() => handleMcpToggle(mcp.id)}
                        style={{ marginRight: '0.75rem' }}
                      />
                      <div>
                        <div style={{ fontWeight: 500 }}>{mcp.name}</div>
                        {mcp.description && (
                          <div style={{ fontSize: '0.8rem', color: '#666' }}>{mcp.description}</div>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="form-group">
              <label>Agent URL *</label>
              <input
                type="text"
                value={newAgent.default_url}
                onChange={(e) => setNewAgent({ ...newAgent, default_url: e.target.value })}
                placeholder="https://agent.example.com/"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                Must be a valid A2A-compatible agent endpoint
              </small>
            </div>

            <div className="form-group">
              <label>Health Endpoint</label>
              <input
                type="text"
                value={newAgent.health_endpoint || ''}
                onChange={(e) => setNewAgent({ ...newAgent, health_endpoint: e.target.value })}
                placeholder="/health or https://agent.example.com/health"
              />
              <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                Leave empty to use default: {'{Agent URL}'}/health
              </small>
            </div>
          </>
        )}

        <div className="form-actions">
          <button 
            className="btn-primary" 
            onClick={handleCreate} 
            disabled={loading || !isValid()}
          >
            {loading ? 'Creating...' : 'Add Agent'}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default AddAgentModal
