import { useState, useEffect, useCallback } from 'react'
import { organizationsApi, workspacesApi, agentsApi, mcpsApi, teamsApi } from '../services'

export function useAppData(isAuthenticated, currentOrganizationId) {
  const [organizations, setOrganizations] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [availableAgents, setAvailableAgents] = useState([])
  const [availableMcps, setAvailableMcps] = useState([])
  const [teams, setTeams] = useState([])

  const [organizationsLoading, setOrganizationsLoading] = useState(false)
  const [workspacesLoading, setWorkspacesLoading] = useState(false)
  const [availableAgentsLoading, setAvailableAgentsLoading] = useState(false)
  const [availableMcpsLoading, setAvailableMcpsLoading] = useState(false)
  const [teamsLoading, setTeamsLoading] = useState(false)

  const loadOrganizations = useCallback(async () => {
    setOrganizationsLoading(true)
    try {
      const response = await organizationsApi.getAll()
      setOrganizations(response.data)
    } catch (err) {
      console.error('Failed to load organizations:', err)
    } finally {
      setOrganizationsLoading(false)
    }
  }, [])

  const loadWorkspaces = useCallback(async () => {
    setWorkspacesLoading(true)
    try {
      const response = await workspacesApi.getAll()
      setWorkspaces(response.data)
    } catch (err) {
      console.error('Failed to load workspaces:', err)
    } finally {
      setWorkspacesLoading(false)
    }
  }, [])

  const loadAvailableAgents = useCallback(async () => {
    setAvailableAgentsLoading(true)
    try {
      const response = await agentsApi.getAll()
      setAvailableAgents(response.data)
    } catch (err) {
      console.error('Failed to load available agents:', err)
    } finally {
      setAvailableAgentsLoading(false)
    }
  }, [])

  const loadAvailableMcps = useCallback(async () => {
    setAvailableMcpsLoading(true)
    try {
      const response = await mcpsApi.getAll()
      setAvailableMcps(response.data)
    } catch (err) {
      console.error('Failed to load available MCPs:', err)
    } finally {
      setAvailableMcpsLoading(false)
    }
  }, [])

  const loadTeams = useCallback(async () => {
    setTeamsLoading(true)
    try {
      const response = await teamsApi.getAll()
      setTeams(response.data)
    } catch (err) {
      console.error('Failed to load teams:', err)
    } finally {
      setTeamsLoading(false)
    }
  }, [])

  const loadWorkspaceDetails = useCallback(async (workspaceId) => {
    if (!workspaceId) return null
    try {
      const response = await workspacesApi.getById(workspaceId)
      return response.data
    } catch (err) {
      console.error('Failed to load workspace details:', err)
      return null
    }
  }, [])

  const refreshAll = useCallback(() => {
    loadOrganizations()
    loadWorkspaces()
    loadAvailableAgents()
    loadAvailableMcps()
    loadTeams()
  }, [loadOrganizations, loadWorkspaces, loadAvailableAgents, loadAvailableMcps, loadTeams])

  useEffect(() => {
    if (isAuthenticated && currentOrganizationId) {
      refreshAll()
    }
  }, [isAuthenticated, currentOrganizationId, refreshAll])

  return {
    organizations,
    workspaces,
    availableAgents,
    availableMcps,
    teams,
    organizationsLoading,
    workspacesLoading,
    availableAgentsLoading,
    availableMcpsLoading,
    teamsLoading,
    loadOrganizations,
    loadWorkspaces,
    loadAvailableAgents,
    loadAvailableMcps,
    loadTeams,
    loadWorkspaceDetails,
    refreshAll,
  }
}

