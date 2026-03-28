import React, { useState } from 'react'
import './Workspaces.css'
import CreateWorkspaceModal from './CreateWorkspaceModal'
import EditWorkspaceModal from './EditWorkspaceModal'
import ViewWorkspaceModal from './ViewWorkspaceModal'
import { usePermissions } from '../../hooks'
import { ViewIcon, EditIcon, TrashIcon } from '../common'

const WorkspacesList = ({
  workspaces,
  loading,
  onCreateWorkspace,
  onUpdateWorkspace,
  onDeleteWorkspace,
  newWorkspace,
  setNewWorkspace,
  showCreateModal,
  setShowCreateModal,
  createLoading,
  organizationId,
  organizations = [],
  hideCreateButton = false,
  isPlatformAdmin = false,
  currentOrganization = null,
}) => {
  const { workspaces: workspacePerms } = usePermissions()
  const availableOrganizations = isPlatformAdmin ? organizations : (currentOrganization ? [currentOrganization] : [])
  const defaultOrgId = currentOrganization ? currentOrganization.id : organizationId
  
  const filteredWorkspaces = workspaces.filter(ws => ws.organization_id === currentOrganization?.id)
  
  const [editingWorkspace, setEditingWorkspace] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [viewingWorkspace, setViewingWorkspace] = useState(null)
  const [showViewModal, setShowViewModal] = useState(false)

  const handleView = (workspace) => {
    setViewingWorkspace(workspace)
    setShowViewModal(true)
  }

  const handleEdit = (workspace) => {
    setEditingWorkspace(workspace)
    setShowEditModal(true)
  }

  const handleDelete = async (workspace) => {
    if (!window.confirm(`Are you sure you want to delete workspace "${workspace.name}"? This action cannot be undone.`)) {
      return
    }
    await onDeleteWorkspace(workspace.id)
  }

  return (
    <div className="section-content">
      {!hideCreateButton && (
        <div className="section-header">
          <h2>Workspaces</h2>
          {workspacePerms.canCreate && (
            <button
              className="btn-primary"
              onClick={() => {
                if (defaultOrgId) {
                  setNewWorkspace({ ...newWorkspace, organization_id: defaultOrgId })
                }
                setShowCreateModal(true)
              }}
              disabled={loading}
            >
              + Add Workspace
            </button>
          )}
        </div>
      )}

      <CreateWorkspaceModal
        visible={showCreateModal}
        newWorkspace={newWorkspace}
        setNewWorkspace={setNewWorkspace}
        onCreate={onCreateWorkspace}
        onClose={() => setShowCreateModal(false)}
        loading={createLoading}
        organizations={availableOrganizations}
        isPlatformAdmin={isPlatformAdmin}
      />

      {viewingWorkspace && (
        <ViewWorkspaceModal
          visible={showViewModal}
          workspace={viewingWorkspace}
          onClose={() => {
            setShowViewModal(false)
            setViewingWorkspace(null)
          }}
        />
      )}

      {editingWorkspace && (
        <EditWorkspaceModal
          visible={showEditModal}
          workspace={editingWorkspace}
          onUpdate={async (updates) => {
            await onUpdateWorkspace(editingWorkspace.id, updates)
            setShowEditModal(false)
            setEditingWorkspace(null)
          }}
          onClose={() => {
            setShowEditModal(false)
            setEditingWorkspace(null)
          }}
          loading={createLoading}
        />
      )}

      {loading ? (
        <div className="loading-state">Loading workspaces...</div>
      ) : (
        <div className="list-container">
          {filteredWorkspaces.length === 0 ? (
            <div className="empty-state">
              <p>No workspaces found. Create your first workspace to get started.</p>
            </div>
          ) : (
            <div className="items-list">
              {filteredWorkspaces.map(workspace => (
                <div
                  key={workspace.id}
                  className="list-item"
                >
                  <div className="list-item-content">
                    <div className="list-item-header">
                      <h3>{workspace.name}</h3>
                      <div className="list-item-badges">
                        {workspace.is_active ? (
                          <span className="badge badge-success">Active</span>
                        ) : (
                          <span className="badge badge-inactive">Inactive</span>
                        )}
                        {workspace.is_system_workspace && (
                          <span className="badge badge-system">System</span>
                        )}
                      </div>
                    </div>
                    <div className="list-item-meta">
                      <span className="meta-item">
                        Org: {organizations.find(o => o.id === workspace.organization_id)?.name || 'Unknown'}
                      </span>
                    </div>
                    {workspace.description && (
                      <p className="list-item-description">{workspace.description}</p>
                    )}
                  </div>
                  <div className="list-item-actions">
                    <button
                      className="btn-icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleView(workspace)
                      }}
                      title="View details"
                    >
                      <ViewIcon size={16} />
                    </button>
                    {workspacePerms.canEdit && (
                      <button
                        className="btn-icon"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEdit(workspace)
                        }}
                        title="Edit"
                      >
                        <EditIcon size={16} />
                      </button>
                    )}
                    {workspacePerms.canDelete && !workspace.delete_protection && (
                      <button
                        className="btn-icon btn-danger"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(workspace)
                        }}
                        title="Delete"
                      >
                        <TrashIcon size={16} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default WorkspacesList
