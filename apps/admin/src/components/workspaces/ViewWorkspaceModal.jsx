import React from 'react'

const ViewWorkspaceModal = ({
  visible,
  workspace,
  onClose,
}) => {
  if (!visible || !workspace) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Workspace Details</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="view-content">
          <div className="view-section">
            <h3>Basic Information</h3>
            <div className="view-field">
              <label>Name</label>
              <div className="view-value">{workspace.name}</div>
            </div>
            <div className="view-field">
              <label>ID</label>
              <div className="view-value view-value-code">{workspace.id}</div>
            </div>
            {workspace.description && (
              <div className="view-field">
                <label>Description</label>
                <div className="view-value">{workspace.description}</div>
              </div>
            )}
            <div className="view-field">
              <label>Status</label>
              <div className="view-value">
                {workspace.is_active ? (
                  <span className="badge badge-success">Active</span>
                ) : (
                  <span className="badge badge-inactive">Inactive</span>
                )}
                {workspace.is_system_workspace && (
                  <span className="badge badge-system" style={{ marginLeft: '0.5rem' }}>System</span>
                )}
              </div>
            </div>
            <div className="view-field">
              <label>Created</label>
              <div className="view-value">{new Date(workspace.created_at).toLocaleString()}</div>
            </div>
            <div className="view-field">
              <label>Last Updated</label>
              <div className="view-value">{new Date(workspace.updated_at).toLocaleString()}</div>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default ViewWorkspaceModal
