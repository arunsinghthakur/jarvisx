import React, { useState, useEffect } from 'react'
import { teamsApi } from '../../services'
import { CloseIcon } from '../common'

const CreateTeamModal = ({
  organizations,
  isPlatformAdmin,
  currentOrganization,
  workspaces: propsWorkspaces = [],
  selectedWorkspaceId,
  onClose,
  onSubmit,
  loading
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    role: 'member',
    organization_id: currentOrganization?.id || '',
    scope_all_workspaces: !selectedWorkspaceId,
    workspace_ids: selectedWorkspaceId ? [selectedWorkspaceId] : []
  })
  const [workspaces, setWorkspaces] = useState([])
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const orgId = isPlatformAdmin ? formData.organization_id : currentOrganization?.id
    if (orgId) {
      loadWorkspaces(orgId)
    }
  }, [formData.organization_id, currentOrganization?.id, isPlatformAdmin])

  const loadWorkspaces = async (orgId) => {
    setLoadingWorkspaces(true)
    try {
      const response = await teamsApi.getOrganizationWorkspaces(orgId)
      setWorkspaces(response.data)
    } catch (err) {
      console.error('Failed to load workspaces:', err)
      setWorkspaces([])
    } finally {
      setLoadingWorkspaces(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!formData.name.trim()) {
      setError('Team name is required')
      return
    }

    const success = await onSubmit({
      name: formData.name.trim(),
      description: formData.description.trim() || null,
      role: formData.role,
      organization_id: isPlatformAdmin ? formData.organization_id : undefined,
      scope_all_workspaces: formData.scope_all_workspaces,
      workspace_ids: formData.scope_all_workspaces ? [] : formData.workspace_ids
    })

    if (!success) {
      setError('Failed to create team')
    }
  }

  const handleWorkspaceToggle = (workspaceId) => {
    setFormData(prev => ({
      ...prev,
      workspace_ids: prev.workspace_ids.includes(workspaceId)
        ? prev.workspace_ids.filter(id => id !== workspaceId)
        : [...prev.workspace_ids, workspaceId]
    }))
  }

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: '550px' }}>
        <div className="modal-header">
          <h3>Create Team</h3>
          <button className="modal-close" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="team-modal-content">
              {error && (
                <div className="form-error" style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '4px', color: '#ef4444', fontSize: '0.875rem' }}>
                  {error}
                </div>
              )}

              {isPlatformAdmin && organizations.length > 0 && (
                <div className="form-group">
                  <label>Organization</label>
                  <select
                    value={formData.organization_id}
                    onChange={(e) => setFormData({ ...formData, organization_id: e.target.value, workspace_ids: [] })}
                    required
                  >
                    <option value="">Select organization</option>
                    {organizations.map(org => (
                      <option key={org.id} value={org.id}>{org.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-group">
                <label>Team Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter team name"
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Enter team description (optional)"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Team Role *</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="viewer">Viewer</option>
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                  <option value="owner">Owner</option>
                </select>
                <small style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
                  All members of this team will inherit this role
                </small>
              </div>

              <div className="form-group">
                <label style={{ marginBottom: '0.75rem', display: 'block' }}>Workspace Scope</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      checked={formData.scope_all_workspaces}
                      onChange={() => setFormData({ ...formData, scope_all_workspaces: true, workspace_ids: [] })}
                      style={{ width: 'auto' }}
                    />
                    <span>All Workspaces</span>
                    <small style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>
                      (Team role applies to all workspaces in the organization)
                    </small>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      checked={!formData.scope_all_workspaces}
                      onChange={() => setFormData({ ...formData, scope_all_workspaces: false })}
                      style={{ width: 'auto' }}
                    />
                    <span>Specific Workspaces</span>
                    <small style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>
                      (Select which workspaces this team can access)
                    </small>
                  </label>
                </div>

                {!formData.scope_all_workspaces && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--color-background)', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                    {loadingWorkspaces ? (
                      <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Loading workspaces...</div>
                    ) : workspaces.length === 0 ? (
                      <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>No workspaces available</div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '150px', overflowY: 'auto' }}>
                        {workspaces.map(workspace => (
                          <label key={workspace.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={formData.workspace_ids.includes(workspace.id)}
                              onChange={() => handleWorkspaceToggle(workspace.id)}
                              style={{ width: 'auto' }}
                            />
                            <span>{workspace.name}</span>
                          </label>
                        ))}
                      </div>
                    )}
                    {!formData.scope_all_workspaces && formData.workspace_ids.length === 0 && workspaces.length > 0 && (
                      <small style={{ color: '#f59e0b', fontSize: '0.75rem', marginTop: '0.5rem', display: 'block' }}>
                        ⚠ No workspaces selected. Team members won't have access to any workspace.
                      </small>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Team'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateTeamModal
