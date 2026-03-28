import React, { useState, useEffect } from 'react'
import { mcpsApi } from '../../services'

const ViewMCPModal = ({
  visible,
  mcp,
  onClose,
  workspaces = [],
  availableAgents = [],
}) => {
  const [mcpAgents, setMcpAgents] = useState([])
  const [loadingAgents, setLoadingAgents] = useState(false)

  useEffect(() => {
    if (visible && mcp) {
      loadMcpAgents()
    } else {
      setMcpAgents([])
    }
  }, [visible, mcp])

  const loadMcpAgents = async () => {
    if (!mcp?.id) return
    setLoadingAgents(true)
    try {
      const response = await mcpsApi.getAgents(mcp.id)
      setMcpAgents(response.data || [])
    } catch (err) {
      console.error('Failed to load MCP agents:', err)
      setMcpAgents([])
    } finally {
      setLoadingAgents(false)
    }
  }

  if (!visible || !mcp) return null

  const connectedAgents = mcpAgents

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>MCP Server Details</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="view-content">
          <div className="view-section">
            <h3>Basic Information</h3>
            <div className="view-field">
              <label>Name</label>
              <div className="view-value">{mcp.name}</div>
            </div>
            <div className="view-field">
              <label>ID</label>
              <div className="view-value view-value-code">{mcp.id}</div>
            </div>
            {mcp.description && (
              <div className="view-field">
                <label>Description</label>
                <div className="view-value">{mcp.description}</div>
              </div>
            )}
            <div className="view-field">
              <label>Status</label>
              <div className="view-value">
                {mcp.is_system_server && (
                  <span className="badge badge-system">System Server</span>
                )}
                {mcp.delete_protection && (
                  <span className="badge badge-warning" style={{ marginLeft: '0.5rem' }}>Protected</span>
                )}
              </div>
            </div>
            <div className="view-field">
              <label>Type</label>
              <div className="view-value">
                {mcp.is_system_server ? 'System Server' : 'Custom Server'}
              </div>
            </div>
            {mcp.default_config && (
              <div className="view-field">
                <label>Default Configuration</label>
                <div className="view-value">
                  <pre className="view-code" style={{ maxHeight: '300px', overflow: 'auto', fontSize: '0.85rem', padding: '0.75rem', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>{JSON.stringify(mcp.default_config, null, 2)}</pre>
                </div>
              </div>
            )}
            {mcp.default_config?.command && (
              <div className="view-field">
                <label>Command</label>
                <div className="view-value view-value-code">{mcp.default_config.command}</div>
              </div>
            )}
            {mcp.default_config?.args && Array.isArray(mcp.default_config.args) && mcp.default_config.args.length > 0 && (
              <div className="view-field">
                <label>Arguments</label>
                <div className="view-value">
                  <div className="view-value-code" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {mcp.default_config.args.map((arg, idx) => (
                      <span key={idx}>{arg}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {loadingAgents ? (
            <div className="view-section">
              <div className="view-empty">
                <p>Loading connected agents...</p>
              </div>
            </div>
          ) : connectedAgents.length > 0 ? (
            <div className="view-section">
              <h3>Connected Agents ({connectedAgents.length})</h3>
              <div className="view-info">
                <p>Agents that can use this MCP server:</p>
              </div>
              <div className="view-list">
                {connectedAgents.map(agent => (
                  <div key={agent.id} className="view-list-item">
                    <div className="view-list-item-header">
                      <span className="view-list-item-name">{agent.name}</span>
                      {agent.is_system_agent && (
                        <span className="badge badge-system">System Agent</span>
                      )}
                      {agent.is_custom_agent && (
                        <span className="badge badge-custom">Custom Agent</span>
                      )}
                    </div>
                    <div className="view-list-item-meta">
                      <span>ID: {agent.id}</span>
                    </div>
                    {agent.description && (
                      <div className="view-list-item-detail">
                        <strong>Description:</strong> {agent.description}
                      </div>
                    )}
                    {agent.default_url && (
                      <div className="view-list-item-detail">
                        <strong>URL:</strong> <span className="view-value-code">{agent.default_url}</span>
                      </div>
                    )}
                    {agent.mcp_config && (
                      <div className="view-list-item-detail">
                        <strong>Agent-Specific Config:</strong>
                        <pre className="view-code" style={{ maxHeight: '200px', overflow: 'auto', fontSize: '0.85rem' }}>{JSON.stringify(agent.mcp_config, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="view-section">
              <div className="view-empty">
                <p>No agents are currently connected to this MCP server.</p>
                <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#666' }}>
                  Edit an agent to assign this MCP server.
                </p>
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

export default ViewMCPModal

