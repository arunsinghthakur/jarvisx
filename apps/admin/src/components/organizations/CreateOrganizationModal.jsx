import React from 'react'

const CreateOrganizationModal = ({
  newOrganization,
  setNewOrganization,
  onCreate,
  onClose,
  loading,
}) => {
  const handleSubmit = (e) => {
    e.preventDefault()
    onCreate()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create Organization</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="org-name">Organization Name *</label>
            <input
              id="org-name"
              type="text"
              value={newOrganization.name || ''}
              onChange={(e) => setNewOrganization({ ...newOrganization, name: e.target.value })}
              required
              placeholder="Enter organization name"
            />
          </div>
          <div className="form-group">
            <label htmlFor="org-description">Description</label>
            <textarea
              id="org-description"
              value={newOrganization.description || ''}
              onChange={(e) => setNewOrganization({ ...newOrganization, description: e.target.value })}
              placeholder="Enter organization description"
              rows="3"
            />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !newOrganization.name}>
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateOrganizationModal

