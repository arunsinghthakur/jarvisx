import React, { useState, useEffect } from 'react'

const EditOrganizationModal = ({
  organization,
  onUpdate,
  onClose,
  loading,
}) => {
  const [formData, setFormData] = useState({
    name: organization.name || '',
    description: organization.description || '',
    is_active: organization.is_active !== undefined ? organization.is_active : true,
  })

  const isProtected = organization.delete_protection

  const handleSubmit = (e) => {
    e.preventDefault()
    onUpdate(organization.id, formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Organization</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="edit-org-name">Organization Name *</label>
            <input
              id="edit-org-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Enter organization name"
              disabled={isProtected}
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit-org-description">Description</label>
            <textarea
              id="edit-org-description"
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Enter organization description"
              rows="3"
              disabled={isProtected}
            />
          </div>
          <div className="form-group">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              />
              <span>Active</span>
            </label>
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !formData.name}>
              {loading ? 'Updating...' : 'Update'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EditOrganizationModal

