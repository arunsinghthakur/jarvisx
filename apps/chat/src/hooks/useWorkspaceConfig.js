import { useState, useEffect, useCallback } from 'react'
import { extractWorkspaceIdFromPath, fetchWorkspaceConfig } from '../services'

const CHAT_MODE = {
  TEXT: 'text',
  VOICE: 'voice',
  BOTH: 'both',
}

export function useWorkspaceConfig() {
  const [workspaceId, setWorkspaceId] = useState(null)
  const [workspaceConfig, setWorkspaceConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [loadFailed, setLoadFailed] = useState(false)

  const loadConfig = useCallback(async () => {
    setLoading(true)
    setError(null)
    setLoadFailed(false)

    try {
      const extractedWorkspaceId = extractWorkspaceIdFromPath()
      
      if (!extractedWorkspaceId) {
        const message = 'Workspace ID is required in the URL (e.g., /workspace/{id} or /{id}).'
        setError(message)
        setLoadFailed(true)
        setLoading(false)
        return
      }

      setWorkspaceId(extractedWorkspaceId)
      const config = await fetchWorkspaceConfig(extractedWorkspaceId)
      setWorkspaceConfig(config)
    } catch (err) {
      console.error('Failed to load workspace configuration:', err)
      setLoadFailed(true)
      setError(`Failed to load workspace configuration: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  const chatMode = workspaceConfig?.chat_mode || CHAT_MODE.BOTH
  const voiceAllowed = chatMode === CHAT_MODE.VOICE || chatMode === CHAT_MODE.BOTH
  const textAllowed = chatMode === CHAT_MODE.TEXT || chatMode === CHAT_MODE.BOTH
  const botName = workspaceConfig?.voice_agent_name || 'JarvisX'

  return {
    workspaceId,
    workspaceConfig,
    loading,
    error,
    loadFailed,
    chatMode,
    voiceAllowed,
    textAllowed,
    botName,
    reload: loadConfig,
  }
}

