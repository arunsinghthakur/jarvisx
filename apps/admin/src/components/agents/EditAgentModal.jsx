import React, { useState, useEffect } from 'react'
import { agentsApi, llmConfigsApi } from '../../services'
import { isOrchestratorAgent } from '../../constants'

const EditAgentModal = ({
  visible,
  agent,
  onUpdate,
  onClose,
  loading = false,
  availableMcps = [],
  availableAgents = [],
  organizationId,
}) => {
  const [editAgent, setEditAgent] = useState({
    name: '',
    description: '',
    default_url: '',
    health_endpoint: '',
    system_prompt: '',
    llm_config_id: '',
  })

  const [selectedSubAgents, setSelectedSubAgents] = useState(new Set())
  const [selectedMcps, setSelectedMcps] = useState(new Set())
  const [llmConfigs, setLlmConfigs] = useState([])
  const [loadingConfigs, setLoadingConfigs] = useState(false)

  const isOrchestrator = isOrchestratorAgent(agent)
  const isDynamic = agent?.is_dynamic_agent

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
    if (agent) {
      setEditAgent({
        name: agent.name || '',
        description: agent.description || '',
        default_url: agent.default_url || '',
        health_endpoint: agent.health_endpoint || '',
        system_prompt: agent.system_prompt || '',
        llm_config_id: agent.llm_config_id || '',
      })

      if (agent.allowed_delegate_agents) {
        setSelectedSubAgents(new Set(agent.allowed_delegate_agents))
      } else {
        setSelectedSubAgents(new Set())
      }

      const fetchAgentMcps = async () => {
        try {
          const response = await agentsApi.getMcps(agent.id)
          const agentMcpIds = new Set(response.data.map(mcp => mcp.id))
          setSelectedMcps(agentMcpIds)
        } catch (err) {
          console.error('Failed to fetch agent MCPs:', err)
          setSelectedMcps(new Set())
        }
      }

      fetchAgentMcps()
    }
  }, [agent, availableMcps])

  if (!visible) return null

  const handleSubmit = async () => {
    const isSystemAgent = agent?.is_system_agent
    
    if (!isSystemAgent && !editAgent.name) return
    
    if (!isSystemAgent && isDynamic) {
      if (!editAgent.system_prompt || !editAgent.llm_config_id) return
    } else if (!isSystemAgent && !isDynamic) {
      if (!editAgent.default_url) return
      if (!editAgent.default_url.startsWith('http://') && !editAgent.default_url.startsWith('https://')) return
    }
    
    const updateData = {
      mcp_server_ids: Array.from(selectedMcps),
    }

    if (!isSystemAgent) {
      updateData.name = editAgent.name
      updateData.description = editAgent.description
    }

    if (isDynamic) {
      if (!isSystemAgent) {
        updateData.system_prompt = editAgent.system_prompt
        updateData.llm_config_id = editAgent.llm_config_id
      }
    } else {
      if (!isSystemAgent) {
        updateData.default_url = editAgent.default_url
      }
      updateData.health_endpoint = editAgent.health_endpoint || null
    }
    
    await onUpdate(updateData)
  }

  const handleSubAgentToggle = (agentId) => {
    const newSet = new Set(selectedSubAgents)
    if (newSet.has(agentId)) {
      newSet.delete(agentId)
    } else {
      newSet.add(agentId)
    }
    setSelectedSubAgents(newSet)
  }

  const handleMCPToggle = (mcpId) => {
    const newSet = new Set(selectedMcps)
    if (newSet.has(mcpId)) {
      newSet.delete(mcpId)
    } else {
      newSet.add(mcpId)
    }
    setSelectedMcps(newSet)
  }

  const isValid = () => {
    const isSystemAgent = agent?.is_system_agent
    
    if (isSystemAgent) {
      return true
    }
    
    if (!editAgent.name) return false
    if (isDynamic) {
      return editAgent.system_prompt && editAgent.llm_config_id
    } else {
      return editAgent.default_url && editAgent.default_url.startsWith('http')
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

  const allAgentsExceptSelf = availableAgents.filter(a => a.id !== agent?.id)
  const allMcps = availableMcps

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <h2>Edit Agent</h2>
        
        {isDynamic && (
          <div style={{ marginBottom: '1rem', padding: '0.5rem 1rem', backgroundColor: '#f3e8ff', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>⚡</span>
            <span style={{ color: '#7c3aed', fontWeight: 500 }}>Dynamic Agent</span>
            <span style={{ color: '#666', fontSize: '0.85rem' }}>- Runs directly on the platform</span>
          </div>
        )}

        <div className="form-group">
          <label>Name *</label>
          <input
            type="text"
            value={editAgent.name}
            onChange={(e) => setEditAgent({ ...editAgent, name: e.target.value })}
            placeholder="Agent name"
            disabled={agent?.is_system_agent}
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={editAgent.description}
            onChange={(e) => setEditAgent({ ...editAgent, description: e.target.value })}
            placeholder="Optional description"
            disabled={agent?.is_system_agent}
            rows={2}
          />
        </div>

        {isDynamic ? (
          <>
            <div className="form-group">
              <label>System Prompt *</label>
              <textarea
                value={editAgent.system_prompt}
                onChange={(e) => setEditAgent({ ...editAgent, system_prompt: e.target.value })}
                placeholder="You are a helpful assistant that..."
                rows={6}
                style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                disabled={agent?.is_system_agent}
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
                      className={`llm-config-option ${editAgent.llm_config_id === config.id ? 'selected' : ''}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0.75rem',
                        border: editAgent.llm_config_id === config.id ? '2px solid #4CAF50' : '1px solid #ddd',
                        borderRadius: '8px',
                        cursor: agent?.is_system_agent ? 'not-allowed' : 'pointer',
                        background: editAgent.llm_config_id === config.id ? '#f0fff0' : '#fff',
                        opacity: agent?.is_system_agent ? 0.7 : 1,
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <input
                        type="radio"
                        name="llm_config"
                        value={config.id}
                        checked={editAgent.llm_config_id === config.id}
                        onChange={() => setEditAgent({ ...editAgent, llm_config_id: config.id })}
                        style={{ marginRight: '0.75rem' }}
                        disabled={agent?.is_system_agent}
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

            <div className="form-group">
              <label>MCP Tools - {allMcps.length} available</label>
              <small style={{ color: '#666', display: 'block', marginBottom: '0.5rem' }}>
                Select tools this agent can use
              </small>
              {allMcps.length > 0 ? (
                <div className="mcp-selector" style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '4px', padding: '0.5rem' }}>
                  {allMcps.map((mcp) => (
                    <label key={mcp.id} className="mcp-option" style={{ display: 'flex', alignItems: 'center', padding: '0.5rem', cursor: 'pointer', borderBottom: '1px solid #eee' }}>
                      <input
                        type="checkbox"
                        checked={selectedMcps.has(mcp.id)}
                        onChange={() => handleMCPToggle(mcp.id)}
                        style={{ marginRight: '0.75rem' }}
                        disabled={loading}
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
              ) : (
                <div style={{ padding: '1rem', textAlign: 'center', color: '#666' }}>
                  No MCP tools available
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="form-group">
              <label>Agent URL *</label>
              <input
                type="text"
                value={editAgent.default_url}
                onChange={(e) => setEditAgent({ ...editAgent, default_url: e.target.value })}
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
                value={editAgent.health_endpoint}
                onChange={(e) => setEditAgent({ ...editAgent, health_endpoint: e.target.value })}
                placeholder="/health or https://agent.example.com/health"
                disabled={loading}
              />
              <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                Leave empty to use default: {'{Agent URL}/health'}
              </small>
            </div>
          </>
        )}

        {isOrchestrator && (
          <>
            <div className="form-group">
              <div className="view-info" style={{ 
                marginTop: '0.5rem', 
                padding: '0.75rem', 
                backgroundColor: '#e7f3ff', 
                border: '1px solid #1877f2',
                borderRadius: '4px'
              }}>
                <p style={{ margin: 0, fontWeight: '500', color: '#1877f2' }}>
                  ℹ️ Orchestrator agent can manage connections to sub-agents and MCP tools. Use the toggles below to add or remove connections.
                </p>
              </div>
            </div>
            <div className="form-group">
              <label>Sub-Agents (Delegation Targets) - {allAgentsExceptSelf.length} available</label>
              <div className="view-info" style={{ marginTop: '0.5rem' }}>
                <p>Select agents that this agent can delegate tasks to:</p>
              </div>
              {allAgentsExceptSelf.length > 0 ? (
                <div className="assignment-list" style={{ marginTop: '0.75rem', maxHeight: '250px', overflowY: 'auto' }}>
                  {allAgentsExceptSelf.map(subAgent => {
                    const isSelected = selectedSubAgents.has(subAgent.id)
                    return (
                      <div key={subAgent.id} className="assignment-item">
                        <div className="assignment-item-content">
                          <div className="assignment-item-header">
                            <span className="assignment-item-name">{subAgent.name}</span>
                            <div className="assignment-item-badges">
                              {subAgent.is_system_agent && (
                                <span className="badge badge-system">System</span>
                              )}
                              {subAgent.is_dynamic_agent && (
                                <span className="badge badge-dynamic">Dynamic</span>
                              )}
                              {subAgent.is_custom_agent && !subAgent.is_dynamic_agent && (
                                <span className="badge badge-custom">External</span>
                              )}
                            </div>
                          </div>
                          {subAgent.description && (
                            <p className="assignment-item-description">{subAgent.description}</p>
                          )}
                          <div className="assignment-item-meta">
                            <span>ID: {subAgent.id}</span>
                          </div>
                        </div>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleSubAgentToggle(subAgent.id)}
                            disabled={loading}
                          />
                        </label>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="view-empty" style={{ marginTop: '0.75rem', padding: '1rem', textAlign: 'center' }}>
                  <p>No agents available to connect.</p>
                </div>
              )}
            </div>
            <div className="form-group">
              <label>MCP Tools - {allMcps.length} available</label>
              <div className="view-info" style={{ marginTop: '0.5rem' }}>
                <p>Select MCP tools that this agent can use:</p>
              </div>
              {allMcps.length > 0 ? (
                <div className="assignment-list" style={{ marginTop: '0.75rem', maxHeight: '250px', overflowY: 'auto' }}>
                  {allMcps.map(mcp => {
                    const isSelected = selectedMcps.has(mcp.id)
                    return (
                      <div key={mcp.id} className="assignment-item">
                        <div className="assignment-item-content">
                          <div className="assignment-item-header">
                            <span className="assignment-item-name">{mcp.name}</span>
                            <div className="assignment-item-badges">
                              {mcp.is_system_server && (
                                <span className="badge badge-system">System</span>
                              )}
                            </div>
                          </div>
                          {mcp.description && (
                            <p className="assignment-item-description">{mcp.description}</p>
                          )}
                          <div className="assignment-item-meta">
                            <span>ID: {mcp.id}</span>
                          </div>
                        </div>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleMCPToggle(mcp.id)}
                            disabled={loading}
                          />
                        </label>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="view-empty" style={{ marginTop: '0.75rem', padding: '1rem', textAlign: 'center' }}>
                  <p>No MCP tools available to connect.</p>
                </div>
              )}
            </div>
          </>
        )}

        {agent?.is_system_agent && !isOrchestrator && (
          <>
            <div className="form-group">
              <div className="view-info" style={{ 
                marginTop: '0.5rem', 
                padding: '0.75rem', 
                backgroundColor: '#fff3cd', 
                border: '1px solid #ffc107',
                borderRadius: '4px'
              }}>
                <p style={{ margin: 0, fontWeight: '500', color: '#856404' }}>
                  ⚠️ System agent connections are protected and cannot be modified to ensure system stability.
                </p>
              </div>
            </div>
            {selectedSubAgents.size > 0 && (
              <div className="form-group">
                <label>Connected Sub-Agents ({selectedSubAgents.size})</label>
                <div className="assignment-list" style={{ marginTop: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                  {availableAgents.filter(a => selectedSubAgents.has(a.id)).map(subAgent => (
                    <div key={subAgent.id} className="assignment-item">
                      <div className="assignment-item-content">
                        <div className="assignment-item-header">
                          <span className="assignment-item-name">{subAgent.name}</span>
                          {subAgent.is_system_agent && (
                            <span className="badge badge-system">System</span>
                          )}
                        </div>
                        <div className="assignment-item-meta">
                          <span>ID: {subAgent.id}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {selectedMcps.size > 0 && (
              <div className="form-group">
                <label>Connected MCP Tools ({selectedMcps.size})</label>
                <div className="assignment-list" style={{ marginTop: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                  {availableMcps.filter(m => selectedMcps.has(m.id)).map(mcp => (
                    <div key={mcp.id} className="assignment-item">
                      <div className="assignment-item-content">
                        <div className="assignment-item-header">
                          <span className="assignment-item-name">{mcp.name}</span>
                          {mcp.is_system_server && (
                            <span className="badge badge-system">System</span>
                          )}
                        </div>
                        <div className="assignment-item-meta">
                          <span>ID: {mcp.id}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        <div className="form-actions">
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || !isValid()}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default EditAgentModal
