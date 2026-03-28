import { useState, useCallback } from 'react'
import { organizationsApi } from '../services'

export function useOrganizationActions(loadOrganizations, loadWorkspaces) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [createdOrgCredentials, setCreatedOrgCredentials] = useState(null)

  const createOrganization = useCallback(async (newOrganization) => {
    if (!newOrganization.name) {
      setError('Organization Name is required')
      return false
    }
    setLoading(true)
    setError(null)
    try {
      const response = await organizationsApi.create(newOrganization)
      if (response.data.default_user) {
        setCreatedOrgCredentials({
          organizationName: response.data.organization.name,
          ...response.data.default_user
        })
      }
      await loadOrganizations()
      return true
    } catch (err) {
      setError(`Failed to create organization: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadOrganizations])

  const updateOrganization = useCallback(async (organizationId, updates) => {
    setLoading(true)
    setError(null)
    try {
      await organizationsApi.update(organizationId, updates)
      await loadOrganizations()
      return true
    } catch (err) {
      setError(`Failed to update organization: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadOrganizations])

  const deleteOrganization = useCallback(async (organizationId) => {
    setLoading(true)
    setError(null)
    try {
      await organizationsApi.delete(organizationId)
      await loadOrganizations()
      await loadWorkspaces()
      return true
    } catch (err) {
      setError(`Failed to delete organization: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadOrganizations, loadWorkspaces])

  const dismissCredentials = useCallback(() => {
    setCreatedOrgCredentials(null)
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    createdOrgCredentials,
    createOrganization,
    updateOrganization,
    deleteOrganization,
    dismissCredentials,
    clearError,
  }
}

