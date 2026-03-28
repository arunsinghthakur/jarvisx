import React, { useState, useEffect } from 'react'
import { agentsApi } from '../../services'

const ViewAgentModal = ({
  visible,
  agent,
  onClose,
  availableMcps = [],
  availableAgents = [],
}) => {
  const [agentMcps, setAgentMcps] = useState([])
  const [loadingMcps, setLoadingMcps] = useState(false)

  useEffect(() => {
    if (visible && agent) {
      loadAgentMcps()
    } else {
      setAgentMcps([])
    }
  }, [visible, agent])

  const loadAgentMcps = async () => {
    if (!agent?.id) return
    setLoadingMcps(true)
    try {
      const response = await agentsApi.getMcps(agent.id)
      setAgentMcps(response.data || [])
    } catch (err) {
      console.error('Failed to load agent MCPs:', err)
      setAgentMcps([])
    } finally {
      setLoadingMcps(false)
    }
  }

  if (!visible || !agent) return null

  const connectedMcps = agentMcps
  const connectedSubAgents = agent.allowed_delegate_agents 
    ? availableAgents.filter(a => agent.allowed_delegate_agents.includes(a.id))
    : []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Agent Details</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="view-content">
          <div className="view-section">
            <h3>Basic Information</h3>
            <div className="view-field">
              <label>Name</label>
              <div className="view-value">{agent.name}</div>
            </div>
            <div className="view-field">
              <label>ID</label>
              <div className="view-value view-value-code">{agent.id}</div>
            </div>
            {agent.description && (
              <div className="view-field">
                <label>Description</label>
                <div className="view-value">{agent.description}</div>
              </div>
            )}
            <div className="view-field">
              <label>Status</label>
              <div className="view-value">
                {agent.is_system_agent && (
                  <span className="badge badge-system">System Agent</span>
                )}
                {agent.is_custom_agent && (
                  <span className="badge badge-custom" style={{ marginLeft: '0.5rem' }}>Custom Agent</span>
                )}
                {agent.is_dynamic_agent && (
                  <span className="badge badge-dynamic" style={{ marginLeft: '0.5rem' }}>Dynamic</span>
                )}
                {agent.delete_protection && (
                  <span className="badge badge-warning" style={{ marginLeft: '0.5rem' }}>Protected</span>
                )}
              </div>
            </div>
            {agent.default_url && (
              <div className="view-field">
                <label>Agent URL</label>
                <div className="view-value view-value-code">{agent.default_url}</div>
              </div>
            )}
            {!agent.is_dynamic_agent && (
              <div className="view-field">
                <label>Health Endpoint</label>
                <div className="view-value view-value-code">
                  {agent.health_endpoint || `${agent.default_url ? (agent.default_url.endsWith('/') ? agent.default_url.slice(0, -1) : agent.default_url) + '/health' : 'N/A'}`}
                </div>
              </div>
            )}
            <div className="view-field">
              <label>Type</label>
              <div className="view-value">
                {agent.is_system_agent ? 'System Agent' : agent.is_dynamic_agent ? 'Dynamic Agent' : agent.is_custom_agent ? 'External A2A Agent' : 'Standard Agent'}
              </div>
            </div>
            {agent.is_dynamic_agent && agent.llm_config && (
              <div className="view-field">
                <label>LLM Configuration</label>
                <div className="view-value">
                  {agent.llm_config.name} ({agent.llm_config.provider} / {agent.llm_config.model_name})
                </div>
              </div>
            )}
          </div>

          {agent.is_dynamic_agent && agent.system_prompt && (
            <div className="view-section">
              <h3>System Prompt</h3>
              <pre style={{ 
                background: '#f5f5f5', 
                padding: '1rem', 
                borderRadius: '4px', 
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                maxHeight: '200px',
                overflow: 'auto'
              }}>
                {agent.system_prompt}
              </pre>
            </div>
          )}

          {connectedSubAgents.length > 0 && (
            <div className="view-section">
              <h3>Connected Sub-Agents ({connectedSubAgents.length})</h3>
              <div className="view-info">
                <p>Agents that this agent can delegate tasks to:</p>
              </div>
              <div className="view-list">
                {connectedSubAgents.map(subAgent => (
                  <div key={subAgent.id} className="view-list-item">
                    <div className="view-list-item-header">
                      <span className="view-list-item-name">{subAgent.name}</span>
                      {subAgent.is_system_agent && (
                        <span className="badge badge-system">System Agent</span>
                      )}
                      {subAgent.is_custom_agent && (
                        <span className="badge badge-custom">Custom Agent</span>
                      )}
                      {subAgent.is_dynamic_agent && (
                        <span className="badge badge-dynamic">Dynamic</span>
                      )}
                    </div>
                    <div className="view-list-item-meta">
                      <span>ID: {subAgent.id}</span>
                    </div>
                    {subAgent.description && (
                      <div className="view-list-item-detail">
                        <strong>Description:</strong> {subAgent.description}
                      </div>
                    )}
                    {subAgent.default_url && (
                      <div className="view-list-item-detail">
                        <strong>URL:</strong> <span className="view-value-code">{subAgent.default_url}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {loadingMcps ? (
            <div className="view-section">
              <div className="view-empty">
                <p>Loading MCP tools...</p>
              </div>
            </div>
          ) : connectedMcps.length > 0 && (
            <div className="view-section">
              <h3>Connected MCP Tools ({connectedMcps.length})</h3>
              <div className="view-info">
                <p>MCP servers that this agent can use:</p>
              </div>
              <div className="view-list">
                {connectedMcps.map(mcp => (
                  <div key={mcp.id} className="view-list-item">
                    <div className="view-list-item-header">
                      <span className="view-list-item-name">{mcp.name}</span>
                      {mcp.is_system_server && (
                        <span className="badge badge-system">System Server</span>
                      )}
                      {mcp.delete_protection && (
                        <span className="badge badge-warning" style={{ marginLeft: '0.5rem' }}>Protected</span>
                      )}
                    </div>
                    <div className="view-list-item-meta">
                      <span>ID: {mcp.id}</span>
                    </div>
                    {mcp.description && (
                      <div className="view-list-item-detail">
                        <strong>Description:</strong> {mcp.description}
                      </div>
                    )}
                    {mcp.mcp_config && (
                      <div className="view-list-item-detail">
                        <strong>Agent-Specific Config:</strong>
                        <pre className="view-code" style={{ maxHeight: '200px', overflow: 'auto', fontSize: '0.85rem' }}>{JSON.stringify(mcp.mcp_config, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="form-actions">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default ViewAgentModal
