import React from 'react'

const ViewOrganizationModal = ({
  organization,
  workspaces,
  onClose,
}) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Organization Details</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="view-content">
          <div className="view-section">
            <h3>Basic Information</h3>
            <div className="view-field">
              <label>Name</label>
              <div className="view-value">{organization.name}</div>
            </div>
            <div className="view-field">
              <label>ID</label>
              <div className="view-value view-value-code">{organization.id}</div>
            </div>
            {organization.description && (
              <div className="view-field">
                <label>Description</label>
                <div className="view-value">{organization.description}</div>
              </div>
            )}
            <div className="view-field">
              <label>Status</label>
              <div className="view-value">
                {organization.is_active ? (
                  <span className="badge badge-success">Active</span>
                ) : (
                  <span className="badge badge-inactive">Inactive</span>
                )}
              </div>
            </div>
            <div className="view-field">
              <label>Created</label>
              <div className="view-value">{new Date(organization.created_at).toLocaleString()}</div>
            </div>
            <div className="view-field">
              <label>Last Updated</label>
              <div className="view-value">{new Date(organization.updated_at).toLocaleString()}</div>
            </div>
          </div>

          <div className="view-section">
            <h3>Workspaces ({workspaces.length})</h3>
            {workspaces.length === 0 ? (
              <div className="view-empty">
                <p>No workspaces assigned to this organization.</p>
              </div>
            ) : (
              <div className="view-list">
                {workspaces.map(workspace => (
                  <div key={workspace.id} className="view-list-item">
                    <div className="view-list-item-header">
                      <span className="view-list-item-name">{workspace.name}</span>
                      {workspace.is_active ? (
                        <span className="badge badge-success">Active</span>
                      ) : (
                        <span className="badge badge-inactive">Inactive</span>
                      )}
                    </div>
                    {workspace.description && (
                      <div className="view-list-item-detail">
                        <strong>Description:</strong> {workspace.description}
                      </div>
                    )}
                    <div className="view-list-item-meta">
                      <span>ID: {workspace.id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="form-actions">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default ViewOrganizationModal

