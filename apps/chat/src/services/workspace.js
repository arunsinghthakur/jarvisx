import { chatbotApi, workspaceApi } from './api'

function isWorkflowWarmedUp(workflowId) {
  try {
    const warmedUp = JSON.parse(sessionStorage.getItem('warmedUpWorkflows') || '[]')
    return warmedUp.includes(workflowId)
  } catch {
    return false
  }
}

function markWorkflowWarmedUp(workflowId) {
  try {
    const warmedUp = JSON.parse(sessionStorage.getItem('warmedUpWorkflows') || '[]')
    if (!warmedUp.includes(workflowId)) {
      warmedUp.push(workflowId)
      sessionStorage.setItem('warmedUpWorkflows', JSON.stringify(warmedUp))
    }
  } catch {
    sessionStorage.setItem('warmedUpWorkflows', JSON.stringify([workflowId]))
  }
}

export const URL_TYPE = {
  WORKSPACE: 'workspace',
  CHATBOT: 'chatbot',
}

export function extractUrlInfo() {
  const path = window.location.pathname
  
  const chatbotMatch = path.match(/\/chatbot\/([^/]+)/)
  if (chatbotMatch) {
    return { type: URL_TYPE.CHATBOT, id: chatbotMatch[1] }
  }
  
  const workspaceMatch = path.match(/\/workspace\/([^/]+)/)
  if (workspaceMatch) {
    return { type: URL_TYPE.WORKSPACE, id: workspaceMatch[1] }
  }
  
  const segments = path.split('/').filter(Boolean)
  if (segments.length === 1) {
    return { type: URL_TYPE.WORKSPACE, id: segments[0] }
  }
  
  return { type: null, id: null }
}

export function extractWorkspaceIdFromPath() {
  const path = window.location.pathname
  const workspaceMatch = path.match(/\/workspace\/([^/]+)/)
  if (workspaceMatch) {
    return workspaceMatch[1]
  }
  const segments = path.split('/').filter(Boolean)
  if (segments.length === 1) {
    return segments[0]
  }
  return null
}

export function extractChatbotIdFromPath() {
  const path = window.location.pathname
  const chatbotMatch = path.match(/\/chatbot\/([^/]+)/)
  if (chatbotMatch) {
    return chatbotMatch[1]
  }
  return null
}

export async function fetchWorkspaceConfig(workspaceId) {
  if (!workspaceId) {
    throw new Error('Workspace ID is required')
  }

  try {
    const response = await workspaceApi.getConfig(workspaceId)
    return response.data
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error('Configuration not found')
    }
    if (error.response?.status === 403) {
      throw new Error('Access denied')
    }
    throw new Error('Failed to load configuration')
  }
}

export async function fetchChatbotConfig(workflowId, warmup = true) {
  if (!workflowId) {
    throw new Error('Workflow ID is required')
  }

  const shouldWarmup = warmup && !isWorkflowWarmedUp(workflowId)
  
  try {
    const response = await chatbotApi.getConfig(workflowId, shouldWarmup)
    
    if (shouldWarmup) {
      markWorkflowWarmedUp(workflowId)
    }
    
    return response.data
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error('Chatbot not found')
    }
    if (error.response?.status === 400) {
      throw new Error(error.response?.data?.detail || 'Invalid chatbot configuration')
    }
    if (error.response?.status === 403) {
      throw new Error('Access denied')
    }
    throw new Error('Failed to load chatbot configuration')
  }
}

export function getSpeechAgentUrl(config) {
  return config?.speech_agent_url || null
}
