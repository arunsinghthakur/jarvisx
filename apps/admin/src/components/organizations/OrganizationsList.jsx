import React, { useState } from 'react'
import { CheckCircleIcon, ViewIcon, EditIcon, TrashIcon } from '../common'
import './Organizations.css'
import CreateOrganizationModal from './CreateOrganizationModal'
import EditOrganizationModal from './EditOrganizationModal'
import ViewOrganizationModal from './ViewOrganizationModal'

const OrganizationsList = ({
  organizations,
  workspaces,
  loading,
  onCreateOrganization,
  onUpdateOrganization,
  onDeleteOrganization,
  newOrganization,
  setNewOrganization,
  showCreateModal,
  setShowCreateModal,
  createLoading,
  createdOrgCredentials,
  onDismissCredentials,
}) => {
  const [editingOrganization, setEditingOrganization] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [viewingOrganization, setViewingOrganization] = useState(null)
  const [showViewModal, setShowViewModal] = useState(false)

  const handleView = (organization) => {
    setViewingOrganization(organization)
    setShowViewModal(true)
  }

  const handleEdit = (organization) => {
    setEditingOrganization(organization)
    setShowEditModal(true)
  }

  const handleDelete = async (organization) => {
    if (!window.confirm(`Are you sure you want to delete organization "${organization.name}"? This will also delete all workspaces under it. This action cannot be undone.`)) {
      return
    }
    await onDeleteOrganization(organization.id)
  }

  const organizationWorkspaces = (orgId) => {
    return workspaces.filter(t => t.organization_id === orgId)
  }

  return (
    <div className="section-content">
      <div className="section-header">
        <h2>Organizations</h2>
        <button
          className="btn-primary"
          onClick={() => setShowCreateModal(true)}
          disabled={loading}
        >
          + Add Organization
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading organizations...</div>
      ) : (
        <>
          {organizations.length === 0 ? (
            <div className="empty-state">
              <p>No organizations found. Create your first organization to get started.</p>
            </div>
          ) : (
            <div className="organizations-grid">
              {organizations.map(org => {
                const orgWorkspaces = organizationWorkspaces(org.id)
                const activeWorkspaces = orgWorkspaces.filter(t => t.is_active).length
                
                return (
                  <div key={org.id} className="organization-card">
                    <div className="organization-card-header">
                      <div className="organization-card-title">
                        <h3>{org.name}</h3>
                        <div className="organization-badges">
                          {!org.is_active && <span className="badge badge-inactive">Inactive</span>}
                          {org.delete_protection && <span className="badge badge-system">Protected</span>}
                        </div>
                      </div>
                      {org.description && (
                        <p className="organization-card-description">{org.description}</p>
                      )}
                    </div>
                    
                    <div className="organization-card-stats">
                      <div className="stat">
                        <span className="stat-value">{orgWorkspaces.length}</span>
                        <span className="stat-label">Workspaces</span>
                      </div>
                      <div className="stat">
                        <span className="stat-value">{activeWorkspaces}</span>
                        <span className="stat-label">Active</span>
                      </div>
                    </div>

                    <div className="organization-card-actions">
                      <button
                        className="btn-icon"
                        onClick={() => handleView(org)}
                        title="View details"
                      >
                        <ViewIcon size={16} />
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleEdit(org)}
                        title="Edit"
                      >
                        <EditIcon size={16} />
                      </button>
                      {!org.delete_protection && (
                        <button
                          className="btn-icon btn-danger"
                          onClick={() => handleDelete(org)}
                          title="Delete"
                          disabled={orgWorkspaces.length > 0}
                        >
                          <TrashIcon size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {showCreateModal && (
        <CreateOrganizationModal
          newOrganization={newOrganization}
          setNewOrganization={setNewOrganization}
          onCreate={onCreateOrganization}
          onClose={() => setShowCreateModal(false)}
          loading={createLoading}
        />
      )}

      {showEditModal && editingOrganization && (
        <EditOrganizationModal
          organization={editingOrganization}
          onUpdate={onUpdateOrganization}
          onClose={() => {
            setShowEditModal(false)
            setEditingOrganization(null)
          }}
          loading={loading}
        />
      )}

      {showViewModal && viewingOrganization && (
        <ViewOrganizationModal
          organization={viewingOrganization}
          workspaces={organizationWorkspaces(viewingOrganization.id)}
          onClose={() => {
            setShowViewModal(false)
            setViewingOrganization(null)
          }}
        />
      )}

      {createdOrgCredentials && (
        <div className="modal-overlay">
          <div className="modal credentials-modal">
            <div className="modal-header">
              <h3>Organization Created Successfully</h3>
            </div>
            <div className="modal-body">
              <div className="credentials-info">
                <div className="credentials-icon">
                  <CheckCircleIcon size={48} />
                </div>
                <p className="credentials-message">
                  <strong>{createdOrgCredentials.organizationName}</strong> has been created with a default admin user.
                </p>
                <div className="credentials-box">
                  <div className="credential-row">
                    <span className="credential-label">Email:</span>
                    <code className="credential-value">{createdOrgCredentials.email}</code>
                  </div>
                  <div className="credential-row">
                    <span className="credential-label">Password:</span>
                    <code className="credential-value">{createdOrgCredentials.password}</code>
                  </div>
                </div>
                <p className="credentials-warning">
                  ⚠️ Please save these credentials securely. The password should be changed after first login.
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={onDismissCredentials}>
                Got it, close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default OrganizationsList
