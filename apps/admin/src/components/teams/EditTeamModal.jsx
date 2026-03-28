import React, { useState, useEffect } from 'react'
import { teamsApi } from '../../services'
import { CloseIcon, TeamsIcon, PlusIcon, TrashIcon } from '../common'

const EditTeamModal = ({
  team,
  organizations,
  isPlatformAdmin,
  currentOrganization,
  onClose,
  onSubmit,
  loading,
  onRefresh
}) => {
  const [formData, setFormData] = useState({
    name: team.name,
    description: team.description || '',
    role: team.role || 'member',
    is_active: team.is_active,
    scope_all_workspaces: team.scope_all_workspaces !== false,
    workspace_ids: (team.scoped_workspaces || []).map(w => w.workspace_id)
  })
  const [members, setMembers] = useState(team.members || [])
  const [availableUsers, setAvailableUsers] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [error, setError] = useState('')
  const [memberLoading, setMemberLoading] = useState(false)
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false)

  useEffect(() => {
    loadAvailableUsers()
    loadWorkspaces()
  }, [team.organization_id])

  const loadAvailableUsers = async () => {
    try {
      const response = await teamsApi.getOrganizationUsers(team.organization_id)
      setAvailableUsers(response.data)
    } catch (err) {
      console.error('Failed to load users:', err)
    }
  }

  const loadWorkspaces = async () => {
    setLoadingWorkspaces(true)
    try {
      const response = await teamsApi.getOrganizationWorkspaces(team.organization_id)
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

    await onSubmit(team.id, {
      name: formData.name.trim(),
      description: formData.description.trim() || null,
      role: formData.role,
      is_active: formData.is_active,
      scope_all_workspaces: formData.scope_all_workspaces,
      workspace_ids: formData.scope_all_workspaces ? [] : formData.workspace_ids
    })
  }

  const handleAddMember = async () => {
    if (!selectedUserId) return

    setMemberLoading(true)
    setError('')
    try {
      await teamsApi.addMember(team.id, {
        user_id: selectedUserId
      })
      
      const response = await teamsApi.getById(team.id)
      setMembers(response.data.members || [])
      setSelectedUserId('')
      onRefresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add member')
    } finally {
      setMemberLoading(false)
    }
  }

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Remove this member from the team?')) return

    setMemberLoading(true)
    setError('')
    try {
      await teamsApi.removeMember(team.id, memberId)
      setMembers(members.filter(m => m.id !== memberId))
      onRefresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove member')
    } finally {
      setMemberLoading(false)
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

  const getInitials = (firstName, lastName, email) => {
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase()
    }
    if (email) {
      return email[0].toUpperCase()
    }
    return '?'
  }

  const memberUserIds = new Set(members.map(m => m.user_id))
  const filteredUsers = availableUsers.filter(u => !memberUserIds.has(u.id))

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: '600px' }}>
        <div className="modal-header">
          <h3>Edit Team</h3>
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

              <div className="form-group">
                <label>Team Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter team name"
                  disabled={team.is_default}
                  style={team.is_default ? { backgroundColor: 'var(--color-background)', cursor: 'not-allowed' } : {}}
                />
                {team.is_default && (
                  <small style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                    Default team name cannot be changed
                  </small>
                )}
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

              {!team.is_default && (
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      style={{ width: 'auto' }}
                    />
                    Active
                  </label>
                </div>
              )}

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
                      (Team role applies to all workspaces)
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
                      (Select workspaces)
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
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '120px', overflowY: 'auto' }}>
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

              <div className="members-section">
                <h4>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <TeamsIcon size={16} />
                    Team Members ({members.length})
                  </span>
                </h4>

                {members.length === 0 ? (
                  <div className="empty-members">
                    No members in this team yet.
                  </div>
                ) : (
                  <div className="members-list">
                    {members.map(member => (
                      <div key={member.id} className="member-item">
                        <div className="member-info">
                          <div className="member-avatar">
                            {getInitials(member.user_first_name, member.user_last_name, member.user_email)}
                          </div>
                          <div className="member-details">
                            <span className="member-name">
                              {member.user_first_name && member.user_last_name 
                                ? `${member.user_first_name} ${member.user_last_name}`
                                : member.user_email}
                            </span>
                            <span className="member-email">{member.user_email}</span>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="remove"
                          onClick={() => handleRemoveMember(member.id)}
                          disabled={memberLoading}
                          style={{ padding: '0.25rem', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)' }}
                          title="Remove member"
                        >
                          <TrashIcon size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {filteredUsers.length > 0 && (
                  <div className="add-member-form">
                    <select
                      value={selectedUserId}
                      onChange={(e) => setSelectedUserId(e.target.value)}
                      disabled={memberLoading}
                    >
                      <option value="">Select user to add...</option>
                      {filteredUsers.map(user => (
                        <option key={user.id} value={user.id}>
                          {user.first_name && user.last_name 
                            ? `${user.first_name} ${user.last_name} (${user.email})`
                            : user.email}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleAddMember}
                      disabled={!selectedUserId || memberLoading}
                      style={{ padding: '0.5rem 0.75rem' }}
                    >
                      <PlusIcon size={14} />
                      Add
                    </button>
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
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EditTeamModal
