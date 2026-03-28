import React, { useState, useEffect, useCallback } from 'react'
import { usersApi } from '../../services'
import { UsersIcon, PlusIcon, EditIcon, TrashIcon, RefreshIcon } from '../common'
import { usePermissions } from '../../hooks'
import InviteUserModal from './InviteUserModal'
import './Users.css'

const UsersList = ({ 
  organizations = [],
  currentOrganization,
  isPlatformAdmin 
}) => {
  const { users: userPerms } = usePermissions()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const selectedOrgId = currentOrganization?.id || ''

  const loadUsers = useCallback(async () => {
    if (!selectedOrgId) {
      setUsers([])
      setLoading(false)
      return
    }
    
    setLoading(true)
    try {
      const response = await usersApi.getByOrganization(selectedOrgId)
      setUsers(response.data)
    } catch (err) {
      setError('Failed to load users')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [selectedOrgId])


  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleInviteUser = async (userData) => {
    setActionLoading(true)
    setError(null)
    try {
      await usersApi.invite(selectedOrgId, userData)
      setShowInviteModal(false)
      await loadUsers()
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to invite user')
      return false
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`Are you sure you want to delete user "${user.email}"?`)) {
      return
    }
    
    setActionLoading(true)
    setError(null)
    try {
      await usersApi.delete(user.id)
      await loadUsers()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete user')
    } finally {
      setActionLoading(false)
    }
  }

  const handleResendVerification = async (user) => {
    setActionLoading(true)
    setError(null)
    try {
      await usersApi.resendVerification(user.id)
      alert(`Verification email resent to ${user.email}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resend verification email')
    } finally {
      setActionLoading(false)
    }
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
      case 'owner': return 'role-owner'
      case 'admin': return 'role-admin'
      case 'viewer': return 'role-viewer'
      default: return 'role-member'
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="users-container">
      <div className="users-header">
        <div>
          <h2>Users</h2>
          <p>Manage users and access within your organization</p>
        </div>
        <div className="users-header-actions">
          {userPerms.canCreate && (
            <button 
              className="btn-primary" 
              onClick={() => setShowInviteModal(true)}
              disabled={!selectedOrgId}
            >
              <PlusIcon size={16} />
              Invite User
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading ? (
        <div className="loading-users">
          <div className="section-loader-spinner"></div>
          <span>Loading users...</span>
        </div>
      ) : !selectedOrgId ? (
        <div className="empty-users">
          <UsersIcon size={48} />
          <h3>Select an Organization</h3>
          <p>Please select an organization to view its users.</p>
        </div>
      ) : users.length === 0 ? (
        <div className="empty-users">
          <UsersIcon size={48} />
          <h3>No Users Yet</h3>
          <p>{userPerms.canCreate ? 'Invite your first user to get started.' : 'No users in this organization.'}</p>
          {userPerms.canCreate && (
            <button className="btn-primary" onClick={() => setShowInviteModal(true)}>
              <PlusIcon size={16} />
              Invite User
            </button>
          )}
        </div>
      ) : (
        <div className="users-table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>
                    <div className="user-info">
                      <div className="user-avatar">
                        {getInitials(user.first_name, user.last_name, user.email)}
                      </div>
                      <div className="user-details">
                        <span className="user-name">
                          {user.first_name && user.last_name 
                            ? `${user.first_name} ${user.last_name}`
                            : user.email}
                        </span>
                        <span className="user-email">{user.email}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`role-badge ${getRoleBadgeClass(user.effective_role)}`}>
                      {user.effective_role}
                    </span>
                  </td>
                  <td>
                    <div className="status-badges">
                      {user.is_active ? (
                        <span className="status-badge active">Active</span>
                      ) : (
                        <span className="status-badge inactive">Inactive</span>
                      )}
                      {!user.is_verified && (
                        <span className="status-badge pending">Pending</span>
                      )}
                    </div>
                  </td>
                  <td className="date-cell">{formatDate(user.last_login_at)}</td>
                  <td className="date-cell">{formatDate(user.created_at)}</td>
                  <td>
                    <div className="user-actions">
                      {!user.is_verified && (
                        <button 
                          className="action-btn resend"
                          onClick={() => handleResendVerification(user)}
                          disabled={actionLoading}
                          title="Resend verification email"
                        >
                          <RefreshIcon size={16} />
                        </button>
                      )}
                      {userPerms.canDelete && (
                        <button 
                          className="action-btn delete"
                          onClick={() => handleDeleteUser(user)}
                          disabled={actionLoading || user.effective_role === 'owner'}
                          title={user.effective_role === 'owner' ? 'Cannot delete owner' : 'Delete user'}
                        >
                          <TrashIcon size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showInviteModal && (
        <InviteUserModal
          onClose={() => setShowInviteModal(false)}
          onSubmit={handleInviteUser}
          loading={actionLoading}
        />
      )}
    </div>
  )
}

export default UsersList

