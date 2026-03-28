import React, { useState, useEffect } from 'react'

const EditWorkspaceModal = ({
  visible,
  workspace,
  onUpdate,
  onClose,
  loading = false,
}) => {
  const [editWorkspace, setEditWorkspace] = useState({
    name: '',
    description: '',
    is_active: true,
  })
  const isProtected = workspace?.delete_protection || workspace?.is_system_workspace

  useEffect(() => {
    if (workspace) {
      setEditWorkspace({
        name: workspace.name || '',
        description: workspace.description || '',
        is_active: workspace.is_active ?? true,
      })
    }
  }, [workspace])

  if (!visible) return null

  const handleSubmit = () => {
    onUpdate({
      name: editWorkspace.name || workspace.name,
      description: editWorkspace.description,
      is_active: editWorkspace.is_active,
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content edit-workspace-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Edit Workspace</h2>
        
        <div className="modal-section">
          <h3>Basic Information</h3>
          <div className="form-group">
            <label>Name *</label>
            <input
              type="text"
              value={editWorkspace.name}
              onChange={(e) => setEditWorkspace({ ...editWorkspace, name: e.target.value })}
              placeholder="Workspace name"
              disabled={isProtected}
            />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea
              value={editWorkspace.description}
              onChange={(e) => setEditWorkspace({ ...editWorkspace, description: e.target.value })}
              placeholder="Optional description"
              disabled={isProtected}
            />
          </div>
          <div className="form-group">
            <label>Active</label>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={editWorkspace.is_active}
                onChange={(e) => setEditWorkspace({ ...editWorkspace, is_active: e.target.checked })}
              />
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button className="btn-primary" onClick={handleSubmit} disabled={loading || !editWorkspace.name}>
            Save Changes
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default EditWorkspaceModal
