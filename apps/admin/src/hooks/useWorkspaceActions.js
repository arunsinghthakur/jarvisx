import { useState, useCallback } from 'react'
import { workspacesApi } from '../services'

export function useWorkspaceActions(loadWorkspaces, loadOrganizations) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const createWorkspace = useCallback(async (workspaceData) => {
    if (!workspaceData.name) {
      setError('Workspace Name is required')
      return false
    }
    if (!workspaceData.organization_id) {
      setError('Organization is required')
      return false
    }
    setLoading(true)
    setError(null)
    try {
      await workspacesApi.create({
        ...workspaceData,
        voice_agent_name: workspaceData.name,
        organization_id: workspaceData.organization_id,
      })
      await loadWorkspaces()
      await loadOrganizations()
      return true
    } catch (err) {
      setError(`Failed to create workspace: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadWorkspaces, loadOrganizations])

  const updateWorkspace = useCallback(async (workspaceId, updates) => {
    setLoading(true)
    setError(null)
    try {
      await workspacesApi.update(workspaceId, updates)
      await loadWorkspaces()
      return true
    } catch (err) {
      setError(`Failed to update workspace: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadWorkspaces])

  const deleteWorkspace = useCallback(async (workspaceId) => {
    setLoading(true)
    setError(null)
    try {
      await workspacesApi.delete(workspaceId)
      await loadWorkspaces()
      return true
    } catch (err) {
      setError(`Failed to delete workspace: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadWorkspaces])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    createWorkspace,
    updateWorkspace,
    deleteWorkspace,
    clearError,
  }
}
