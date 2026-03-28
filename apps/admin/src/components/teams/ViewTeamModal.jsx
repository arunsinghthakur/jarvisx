import React from 'react'
import { CloseIcon, TeamsIcon, EditIcon } from '../common'

const ViewTeamModal = ({ team, onClose, onEdit }) => {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
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

  const getRoleBadgeClass = (role) => {
    switch (role) {
      case 'owner': return 'owner'
      case 'admin': return 'admin'
      case 'viewer': return 'viewer'
      default: return ''
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: '600px' }}>
        <div className="modal-header">
          <h3>{team.name}</h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn-secondary" onClick={onEdit} style={{ padding: '0.5rem 0.75rem' }}>
              <EditIcon size={16} />
              Edit
            </button>
            <button className="modal-close" onClick={onClose}>
              <CloseIcon size={20} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          <div className="team-modal-content">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              {team.is_default && <span className="team-badge default">Default Team</span>}
              {!team.is_active && <span className="team-badge inactive">Inactive</span>}
              {team.is_active && !team.is_default && (
                <span className="team-badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>Active</span>
              )}
            </div>

            {team.description && (
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', marginBottom: '1rem' }}>
                {team.description}
              </p>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Organization</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{team.organization_name || 'Unknown'}</p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Team Role</label>
                <p style={{ margin: '0.25rem 0 0' }}>
                  <span className={`member-role ${getRoleBadgeClass(team.role)}`} style={{ textTransform: 'capitalize' }}>
                    {team.role}
                  </span>
                </p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Members</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{team.member_count}</p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Workspace Scope</label>
                <p style={{ margin: '0.25rem 0 0' }}>
                  <span className={`workspace-scope ${team.scope_all_workspaces ? 'all' : 'scoped'}`}>
                    {team.scope_all_workspaces ? 'All Workspaces' : `${team.scoped_workspaces?.length || 0} Workspace(s)`}
                  </span>
                </p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Created</label>
                <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem' }}>{formatDate(team.created_at)}</p>
              </div>
            </div>

            {!team.scope_all_workspaces && team.scoped_workspaces && team.scoped_workspaces.length > 0 && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'var(--color-background)', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem', display: 'block' }}>Scoped Workspaces</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {team.scoped_workspaces.map(sw => (
                    <span key={sw.id} style={{ padding: '0.25rem 0.5rem', background: 'var(--color-surface)', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--color-text-primary)' }}>
                      {sw.workspace_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="members-section" style={{ marginTop: '1rem', paddingTop: '1rem' }}>
              <h4>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <TeamsIcon size={16} />
                  Team Members ({team.members?.length || 0})
                </span>
              </h4>

              {(!team.members || team.members.length === 0) ? (
                <div className="empty-members">
                  No members in this team yet.
                </div>
              ) : (
                <div className="members-list">
                  {team.members.map(member => (
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
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default ViewTeamModal

