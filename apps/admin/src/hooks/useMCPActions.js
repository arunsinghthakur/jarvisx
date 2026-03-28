import { useState, useCallback } from 'react'
import { mcpsApi } from '../services'

export function useMCPActions(loadAvailableMcps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const createMCP = useCallback(async (newMCP) => {
    if (!newMCP.id || !newMCP.name) {
      setError('MCP Server ID and Name are required')
      return false
    }
    setLoading(true)
    setError(null)
    try {
      await mcpsApi.create({
        ...newMCP,
        default_config: newMCP.default_config || {},
      })
      await loadAvailableMcps()
      return true
    } catch (err) {
      setError(`Failed to create MCP server: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableMcps])

  const updateMCP = useCallback(async (mcpId, updates) => {
    setLoading(true)
    setError(null)
    try {
      await mcpsApi.update(mcpId, updates)
      await loadAvailableMcps()
      return true
    } catch (err) {
      setError(`Failed to update MCP server: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableMcps])

  const deleteMCP = useCallback(async (mcpId) => {
    setLoading(true)
    setError(null)
    try {
      await mcpsApi.delete(mcpId)
      await loadAvailableMcps()
      return true
    } catch (err) {
      setError(`Failed to delete MCP server: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableMcps])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    createMCP,
    updateMCP,
    deleteMCP,
    clearError,
  }
}
