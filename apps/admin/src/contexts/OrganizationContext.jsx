import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { organizationsApi, setCurrentOrganization as setApiOrganization } from '../services'

const OrganizationContext = createContext(null)

export const useOrganization = () => {
  const context = useContext(OrganizationContext)
  if (!context) {
    throw new Error('useOrganization must be used within an OrganizationProvider')
  }
  return context
}

export const OrganizationProvider = ({ children }) => {
  const [organizations, setOrganizations] = useState([])
  const [currentOrganization, setCurrentOrganizationState] = useState(null)
  const [loading, setLoading] = useState(true)
  const [initialized, setInitialized] = useState(false)

  const loadOrganizations = useCallback(async () => {
    try {
      const response = await organizationsApi.getAll()
      setOrganizations(response.data)
      return response.data
    } catch (error) {
      console.error('Failed to load organizations:', error)
      return []
    }
  }, [])

  const initializeOrganization = useCallback(async () => {
    try {
      const savedOrgId = localStorage.getItem('currentOrganizationId')
      
      const orgsData = await loadOrganizations()
      
      let selectedOrg = null
      if (savedOrgId) {
        selectedOrg = orgsData.find(org => org.id === savedOrgId)
      }
      
      if (!selectedOrg && orgsData.length > 0) {
        selectedOrg = orgsData.find(org => org.is_platform_admin) || orgsData[0]
      }
      
      if (selectedOrg) {
        setCurrentOrganizationState(selectedOrg)
        setApiOrganization(selectedOrg.id)
        localStorage.setItem('currentOrganizationId', selectedOrg.id)
      }
      
      setInitialized(true)
    } catch (error) {
      console.error('Failed to initialize organization:', error)
    } finally {
      setLoading(false)
    }
  }, [loadOrganizations])

  useEffect(() => {
    initializeOrganization()
  }, [initializeOrganization])

  const switchOrganization = useCallback(async (org) => {
    setCurrentOrganizationState(org)
    setApiOrganization(org.id)
    localStorage.setItem('currentOrganizationId', org.id)
    
    await loadOrganizations()
  }, [loadOrganizations])

  const refreshOrganizations = useCallback(async () => {
    await loadOrganizations()
  }, [loadOrganizations])

  const isPlatformAdmin = currentOrganization?.is_platform_admin || false

  const value = {
    organizations,
    currentOrganization,
    loading,
    initialized,
    isPlatformAdmin,
    switchOrganization,
    loadOrganizations: refreshOrganizations,
  }

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  )
}

export default OrganizationContext
