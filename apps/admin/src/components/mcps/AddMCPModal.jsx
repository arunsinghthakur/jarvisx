import React, { useState } from 'react'

const AddMCPModal = ({
  visible,
  newMCP,
  setNewMCP,
  onCreate,
  onClose,
  loading = false,
}) => {
  const [configError, setConfigError] = useState(null)

  if (!visible) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Add MCP Server</h2>
        <p style={{ color: '#65676b', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
          Add a new MCP server to the system.
        </p>
        <div className="form-group">
          <label>MCP Server ID *</label>
          <input
            type="text"
            value={newMCP.id}
            onChange={(e) => setNewMCP({ ...newMCP, id: e.target.value })}
            placeholder="e.g., custom_mcp_server"
          />
        </div>
        <div className="form-group">
          <label>Name *</label>
          <input
            type="text"
            value={newMCP.name}
            onChange={(e) => setNewMCP({ ...newMCP, name: e.target.value })}
            placeholder="MCP Server Name"
          />
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={newMCP.description}
            onChange={(e) => setNewMCP({ ...newMCP, description: e.target.value })}
            placeholder="Optional description"
          />
        </div>
        <div className="form-group">
          <label>Default Config (JSON)</label>
          <textarea
            value={typeof newMCP.default_config === 'string' ? newMCP.default_config : (newMCP.default_config ? JSON.stringify(newMCP.default_config, null, 2) : '')}
            onChange={(e) => {
              setNewMCP({ ...newMCP, default_config: e.target.value })
              setConfigError(null)
            }}
            placeholder='{"command": "node", "args": ["server.js"]}'
            rows={4}
          />
          <small style={{ color: '#65676b', display: 'block', marginTop: '0.25rem' }}>
            Optional JSON configuration for the MCP server
          </small>
        </div>
        <div className="form-actions">
          {configError && (
            <div style={{ color: '#c33', fontSize: '0.875rem', marginBottom: '1rem' }}>
              {configError}
            </div>
          )}
          <button 
            className="btn-primary" 
            onClick={() => {
              // Parse JSON config if provided
              let config = {}
              if (newMCP.default_config && typeof newMCP.default_config === 'string' && newMCP.default_config.trim()) {
                try {
                  config = JSON.parse(newMCP.default_config)
                  setConfigError(null)
                } catch (err) {
                  setConfigError('Invalid JSON in default config')
                  return
                }
              } else if (newMCP.default_config && typeof newMCP.default_config === 'object') {
                config = newMCP.default_config
              }
              onCreate({ ...newMCP, default_config: config })
            }} 
            disabled={loading || !newMCP.id || !newMCP.name}
          >
            Add MCP Server
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default AddMCPModal

