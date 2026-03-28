import React, { useState } from 'react'
import './MCPs.css'
import AddMCPModal from './AddMCPModal'
import EditMCPModal from './EditMCPModal'
import ViewMCPModal from './ViewMCPModal'
import { usePermissions } from '../../hooks'
import { ViewIcon, EditIcon, TrashIcon } from '../common'

const MCPList = ({
  mcps,
  workspaces,
  loading,
  onCreateMCP,
  onUpdateMCP,
  onDeleteMCP,
  newMCP,
  setNewMCP,
  showCreateModal,
  setShowCreateModal,
  createLoading,
  availableAgents = [],
  onUpdateMCPConnections,
}) => {
  const { mcps: mcpPerms } = usePermissions()
  const [editingMCP, setEditingMCP] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [viewingMCP, setViewingMCP] = useState(null)
  const [showViewModal, setShowViewModal] = useState(false)

  const handleView = (mcp) => {
    setViewingMCP(mcp)
    setShowViewModal(true)
  }

  const handleEdit = (mcp) => {
    setEditingMCP(mcp)
    setShowEditModal(true)
  }

  const handleDelete = async (mcp) => {
    if (!window.confirm(`Are you sure you want to delete MCP server "${mcp.name}"? This action cannot be undone.`)) {
      return
    }
    await onDeleteMCP(mcp.id)
  }

  return (
    <div className="section-content">
      <div className="section-header">
        <h2>MCP Servers</h2>
        {mcpPerms.canCreate && (
          <button
            className="btn-primary"
            onClick={() => setShowCreateModal(true)}
            disabled={loading}
          >
            + Add MCP Server
          </button>
        )}
      </div>

      <div className="info-banner">
        <p>💡 Click "Edit" on a workspace in the Workspaces section to assign/remove agents and MCP servers.</p>
      </div>

      <AddMCPModal
        visible={showCreateModal}
        newMCP={newMCP}
        setNewMCP={setNewMCP}
        onCreate={onCreateMCP}
        onClose={() => setShowCreateModal(false)}
        loading={createLoading}
      />

      {viewingMCP && (
        <ViewMCPModal
          visible={showViewModal}
          mcp={viewingMCP}
          workspaces={workspaces}
          availableAgents={availableAgents}
          onClose={() => {
            setShowViewModal(false)
            setViewingMCP(null)
          }}
        />
      )}

      {editingMCP && (
        <EditMCPModal
          visible={showEditModal}
          mcp={editingMCP}
          onUpdate={async (updates) => {
            await onUpdateMCP(editingMCP.id, updates)
            setShowEditModal(false)
            setEditingMCP(null)
          }}
          onClose={() => {
            setShowEditModal(false)
            setEditingMCP(null)
          }}
          loading={createLoading}
          workspaces={workspaces}
          availableAgents={availableAgents}
          onUpdateMCPConnections={onUpdateMCPConnections}
        />
      )}

      {loading ? (
        <div className="loading-state">Loading MCP servers...</div>
      ) : (
        <div className="list-container">
          {mcps.length === 0 ? (
            <div className="empty-state">
              <p>No MCP servers found. Add your first MCP server to get started.</p>
            </div>
          ) : (
            <div className="items-list">
              {mcps.map(mcp => (
                <div key={mcp.id} className="list-item">
                  <div className="list-item-content">
                    <div className="list-item-header">
                      <h3>{mcp.name}</h3>
                      <div className="list-item-badges">
                        {mcp.is_system_server && (
                          <span className="badge badge-system">System Server</span>
                        )}
                      </div>
                    </div>
                    <div className="list-item-meta">
                      <span className="meta-item">ID: {mcp.id}</span>
                    </div>
                    {mcp.description && (
                      <p className="list-item-description">{mcp.description}</p>
                    )}
                  </div>
                  <div className="list-item-actions">
                    <button
                      className="btn-icon"
                      onClick={() => handleView(mcp)}
                      title="View details"
                    >
                      <ViewIcon size={16} />
                    </button>
                    {mcpPerms.canEdit && mcp.can_edit !== false && (
                      <button
                        className="btn-icon"
                        onClick={() => handleEdit(mcp)}
                        title="Edit"
                      >
                        <EditIcon size={16} />
                      </button>
                    )}
                    {mcpPerms.canDelete && mcp.can_delete && (
                      <button
                        className="btn-icon btn-danger"
                        onClick={() => handleDelete(mcp)}
                        title="Delete"
                      >
                        <TrashIcon size={16} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default MCPList
