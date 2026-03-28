import { useState, useCallback } from 'react'
import { agentsApi } from '../services'

export function useAgentActions(loadAvailableAgents) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const createAgent = useCallback(async (newAgent) => {
    if (!newAgent.name) {
      setError('Agent Name is required')
      return false
    }
    
    if (newAgent.is_dynamic_agent) {
      if (!newAgent.system_prompt) {
        setError('System Prompt is required for dynamic agents')
        return false
      }
      if (!newAgent.llm_config_id) {
        setError('LLM Configuration is required for dynamic agents')
        return false
      }
    } else {
      if (!newAgent.default_url) {
        setError('Agent URL is required for external agents')
        return false
      }
      if (!newAgent.default_url.startsWith('http://') && !newAgent.default_url.startsWith('https://')) {
        setError('Agent URL must start with http:// or https://')
        return false
      }
    }
    
    setLoading(true)
    setError(null)
    try {
      const agentId = newAgent.id || newAgent.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
      
      await agentsApi.create({
        ...newAgent,
        id: agentId,
        is_custom_agent: true,
      })
      await loadAvailableAgents()
      return true
    } catch (err) {
      setError(`Failed to create agent: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableAgents])

  const updateAgent = useCallback(async (agentId, updates) => {
    setLoading(true)
    setError(null)
    try {
      await agentsApi.update(agentId, updates)
      await loadAvailableAgents()
      return true
    } catch (err) {
      setError(`Failed to update agent: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableAgents])

  const deleteAgent = useCallback(async (agentId) => {
    setLoading(true)
    setError(null)
    try {
      await agentsApi.delete(agentId)
      await loadAvailableAgents()
      return true
    } catch (err) {
      setError(`Failed to delete agent: ${err.response?.data?.detail || err.message}`)
      return false
    } finally {
      setLoading(false)
    }
  }, [loadAvailableAgents])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    createAgent,
    updateAgent,
    deleteAgent,
    clearError,
  }
}
