import React, { useEffect } from 'react'

const CreateWorkspaceModal = ({
  visible,
  newWorkspace,
  setNewWorkspace,
  onCreate,
  onClose,
  loading = false,
  organizations = [],
  isPlatformAdmin = false,
}) => {
  useEffect(() => {
    if (visible && !isPlatformAdmin && organizations.length === 1 && !newWorkspace.organization_id) {
      setNewWorkspace(prev => ({ ...prev, organization_id: organizations[0].id }))
    }
  }, [visible, isPlatformAdmin, organizations, newWorkspace.organization_id, setNewWorkspace])

  if (!visible) return null

  const showOrgSelector = isPlatformAdmin || organizations.length > 1

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Create New Workspace</h2>
      {showOrgSelector ? (
        <div className="form-group">
          <label>Organization *</label>
          <select
            value={newWorkspace.organization_id || ''}
            onChange={(e) => setNewWorkspace({ ...newWorkspace, organization_id: e.target.value })}
            required
          >
            <option value="">Select Organization</option>
            {organizations.map(org => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))}
          </select>
        </div>
      ) : organizations.length === 1 && (
        <div className="form-group">
          <label>Organization</label>
          <input type="text" value={organizations[0].name} disabled />
        </div>
      )}
      <div className="form-group">
        <label>Name *</label>
        <input
          type="text"
          value={newWorkspace.name}
          onChange={(e) => setNewWorkspace({ ...newWorkspace, name: e.target.value })}
          placeholder="Acme Corporation"
          required
        />
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea
          value={newWorkspace.description}
          onChange={(e) => setNewWorkspace({ ...newWorkspace, description: e.target.value })}
          placeholder="Optional description"
        />
      </div>
      <div className="form-actions">
        <button 
          className="btn-primary" 
          onClick={() => onCreate(newWorkspace)} 
          disabled={loading || !newWorkspace.name?.trim() || !newWorkspace.organization_id}
        >
          Create Workspace
        </button>
        <button className="btn-secondary" onClick={onClose} disabled={loading}>
          Cancel
        </button>
      </div>
      </div>
    </div>
  )
}

export default CreateWorkspaceModal

