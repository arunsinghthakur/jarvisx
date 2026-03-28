import React, { useState, useEffect } from 'react'

const EditMCPModal = ({
  visible,
  mcp,
  onUpdate,
  onClose,
  loading = false,
}) => {
  const [editMCP, setEditMCP] = useState({
    name: '',
    description: '',
    default_config: '',
  })
  const [configError, setConfigError] = useState(null)

  useEffect(() => {
    if (mcp) {
      const configString = mcp.default_config && typeof mcp.default_config === 'object'
        ? JSON.stringify(mcp.default_config, null, 2)
        : mcp.default_config || ''
      
      setEditMCP({
        name: mcp.name || '',
        description: mcp.description || '',
        default_config: configString,
      })
    }
  }, [mcp])

  if (!visible) return null

  const handleSubmit = async () => {
    let configValue = {}
    if (editMCP.default_config && editMCP.default_config.trim()) {
      try {
        configValue = JSON.parse(editMCP.default_config)
        setConfigError(null)
      } catch (err) {
        setConfigError('Invalid JSON in default config')
        return
      }
    }
    
    await onUpdate({
      name: editMCP.name,
      description: editMCP.description,
      default_config: configValue,
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Edit MCP Server</h2>
        <div className="form-group">
          <label>Name *</label>
          <input
            type="text"
            value={editMCP.name}
            onChange={(e) => setEditMCP({ ...editMCP, name: e.target.value })}
            placeholder="MCP Server Name"
            disabled={mcp?.is_system_server}
          />
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={editMCP.description}
            onChange={(e) => setEditMCP({ ...editMCP, description: e.target.value })}
            placeholder="Optional description"
            disabled={mcp?.is_system_server}
          />
        </div>
        <div className="form-group">
          <label>Default Config (JSON)</label>
          <textarea
            value={editMCP.default_config}
            onChange={(e) => {
              setEditMCP({ ...editMCP, default_config: e.target.value })
              setConfigError(null)
            }}
            placeholder='{"command": "node", "args": ["server.js"]}'
            rows={4}
          />
          <small style={{ color: '#65676b', display: 'block', marginTop: '0.25rem' }}>
            Optional JSON configuration for the MCP server
          </small>
        </div>
        {configError && (
          <div style={{ color: '#c33', fontSize: '0.875rem', marginBottom: '1rem' }}>
            {configError}
          </div>
        )}

        <div className="form-actions">
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || !editMCP.name}
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

export default EditMCPModal
