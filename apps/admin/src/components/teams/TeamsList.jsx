import React, { useState, useEffect, useCallback } from 'react'
import { teamsApi } from '../../services'
import { TeamsIcon, PlusIcon, ViewIcon, EditIcon, TrashIcon } from '../common'
import { usePermissions } from '../../hooks'
import CreateTeamModal from './CreateTeamModal'
import ViewTeamModal from './ViewTeamModal'
import EditTeamModal from './EditTeamModal'
import './Teams.css'

const TeamsList = ({ 
  organizations = [],
  isPlatformAdmin,
  currentOrganization,
  workspaces = [],
  selectedWorkspaceId
}) => {
  const { teams: teamPerms } = usePermissions()
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  const loadTeams = useCallback(async () => {
    if (!currentOrganization?.id) {
      setTeams([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const response = await teamsApi.getAll()
      let filteredTeams = response.data.filter(team => team.organization_id === currentOrganization.id)
      
      if (selectedWorkspaceId) {
        filteredTeams = filteredTeams.filter(team => 
          team.scope_all_workspaces || 
          (team.scoped_workspaces && team.scoped_workspaces.some(ws => ws.id === selectedWorkspaceId))
        )
      }
      
      setTeams(filteredTeams)
    } catch (err) {
      setError('Failed to load teams')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [currentOrganization?.id, selectedWorkspaceId])

  useEffect(() => {
    loadTeams()
  }, [loadTeams])

  const handleView = async (team) => {
    try {
      const response = await teamsApi.getById(team.id)
      setSelectedTeam(response.data)
      setShowViewModal(true)
    } catch (err) {
      setError('Failed to load team details')
    }
  }

  const handleEdit = async (team) => {
    try {
      const response = await teamsApi.getById(team.id)
      setSelectedTeam(response.data)
      setShowEditModal(true)
    } catch (err) {
      setError('Failed to load team details')
    }
  }

  const handleDelete = async (team) => {
    if (team.is_default) {
      setError('Cannot delete default team')
      return
    }
    
    if (!window.confirm(`Are you sure you want to delete "${team.name}"?`)) {
      return
    }
    
    setActionLoading(true)
    try {
      await teamsApi.delete(team.id)
      await loadTeams()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete team')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreateTeam = async (teamData) => {
    setActionLoading(true)
    try {
      await teamsApi.create(teamData)
      setShowCreateModal(false)
      await loadTeams()
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create team')
      return false
    } finally {
      setActionLoading(false)
    }
  }

  const handleUpdateTeam = async (teamId, updates) => {
    setActionLoading(true)
    try {
      await teamsApi.update(teamId, updates)
      setShowEditModal(false)
      await loadTeams()
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update team')
      return false
    } finally {
      setActionLoading(false)
    }
  }

  const getOrgName = (orgId) => {
    const org = organizations.find(o => o.id === orgId)
    return org?.name || 'Unknown'
  }

  if (loading) {
    return (
      <div className="teams-container">
        <div className="loading-teams">
          <div className="section-loader-spinner"></div>
          <span>Loading teams...</span>
        </div>
      </div>
    )
  }

  if (!selectedWorkspaceId) {
    return (
      <div className="teams-container">
        <div className="empty-teams">
          <TeamsIcon size={48} />
          <h3>Select a Workspace</h3>
          <p>Please select a workspace to view and manage teams.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="teams-container">
      <div className="teams-header">
        <div>
          <p>Manage teams and team members within your workspace</p>
        </div>
        {teamPerms.canCreate && (
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            <PlusIcon size={16} />
            Create Team
          </button>
        )}
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: '1rem' }}>
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {teams.length === 0 ? (
        <div className="empty-teams">
          <TeamsIcon size={48} />
          <h3>No Teams Yet</h3>
          <p>{teamPerms.canCreate ? 'Create your first team to organize members and manage access.' : 'No teams available in this workspace.'}</p>
          {teamPerms.canCreate && (
            <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
              <PlusIcon size={16} />
              Create Team
            </button>
          )}
        </div>
      ) : (
        <div className="teams-grid">
          {teams.map(team => (
            <div key={team.id} className="team-card">
              <div className="team-card-header">
                <div className="team-card-title">
                  <h3>{team.name}</h3>
                  {team.is_default && <span className="team-badge default">Default</span>}
                  {!team.is_active && <span className="team-badge inactive">Inactive</span>}
                </div>
                <div className="team-card-actions">
                  <button onClick={() => handleView(team)} title="View">
                    <ViewIcon size={16} />
                  </button>
                  {teamPerms.canEdit && (
                    <button onClick={() => handleEdit(team)} title="Edit">
                      <EditIcon size={16} />
                    </button>
                  )}
                  {teamPerms.canDelete && !team.is_default && (
                    <button 
                      className="delete" 
                      onClick={() => handleDelete(team)} 
                      title="Delete"
                      disabled={actionLoading}
                    >
                      <TrashIcon size={16} />
                    </button>
                  )}
                </div>
              </div>
              
              <p className="team-card-description">
                {team.description || 'No description'}
              </p>
              
              <div className="team-card-meta">
                <div className="team-meta-item">
                  <TeamsIcon size={14} />
                  <strong>{team.member_count}</strong> members
                </div>
                <div className="team-meta-item">
                  <span className={`workspace-scope ${team.scope_all_workspaces ? 'all' : 'scoped'}`}>
                    {team.scope_all_workspaces 
                      ? 'All workspaces' 
                      : `${team.scoped_workspace_count || 0} workspace${team.scoped_workspace_count !== 1 ? 's' : ''}`}
                  </span>
                </div>
                {isPlatformAdmin && (
                  <div className="team-meta-item">
                    <span>{team.organization_name || getOrgName(team.organization_id)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateTeamModal
          organizations={organizations}
          isPlatformAdmin={isPlatformAdmin}
          currentOrganization={currentOrganization}
          workspaces={workspaces}
          selectedWorkspaceId={selectedWorkspaceId}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateTeam}
          loading={actionLoading}
        />
      )}

      {showViewModal && selectedTeam && (
        <ViewTeamModal
          team={selectedTeam}
          onClose={() => {
            setShowViewModal(false)
            setSelectedTeam(null)
          }}
          onEdit={() => {
            setShowViewModal(false)
            setShowEditModal(true)
          }}
        />
      )}

      {showEditModal && selectedTeam && (
        <EditTeamModal
          team={selectedTeam}
          organizations={organizations}
          isPlatformAdmin={isPlatformAdmin}
          currentOrganization={currentOrganization}
          onClose={() => {
            setShowEditModal(false)
            setSelectedTeam(null)
          }}
          onSubmit={handleUpdateTeam}
          loading={actionLoading}
          onRefresh={loadTeams}
        />
      )}
    </div>
  )
}

export default TeamsList

