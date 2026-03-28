import { conversationsApi } from './api'

export async function listConversations(workflowId, options = {}) {
  if (!workflowId) {
    return { groups: [], has_more: false }
  }
  
  const { limit = 30, offset = 0 } = options
  
  const response = await conversationsApi.list(workflowId, { limit, offset })
  const data = response.data || []
  
  const grouped = groupConversationsByTime(data)
  return {
    groups: grouped,
    has_more: data.length >= limit,
  }
}

function groupConversationsByTime(conversations) {
  const now = new Date()
  const groups = {
    today: [],
    yesterday: [],
    previous_7_days: [],
    previous_30_days: [],
    older: [],
  }
  
  for (const conv of conversations) {
    const date = new Date(conv.updated_at || conv.created_at)
    const diffMs = now - date
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffDays === 0) {
      groups.today.push(conv)
    } else if (diffDays === 1) {
      groups.yesterday.push(conv)
    } else if (diffDays <= 7) {
      groups.previous_7_days.push(conv)
    } else if (diffDays <= 30) {
      groups.previous_30_days.push(conv)
    } else {
      groups.older.push(conv)
    }
  }
  
  return Object.entries(groups)
    .filter(([_, convs]) => convs.length > 0)
    .map(([group, conversations]) => ({ group, conversations }))
}

export async function createConversation(workflowId, title = null, messages = null) {
  return { id: null, title: title || 'New Chat' }
}

export async function getConversation(workflowId, conversationId) {
  const response = await conversationsApi.get(workflowId, conversationId)
  return response.data
}

export async function updateConversation(workflowId, conversationId, data) {
  const response = await conversationsApi.update(workflowId, conversationId, data)
  return response.data
}

export async function deleteConversation(workflowId, conversationId) {
  await conversationsApi.delete(workflowId, conversationId)
  return null
}

export async function addMessage(workflowId, conversationId, role, content, metadata = null) {
  const response = await conversationsApi.addMessage(workflowId, conversationId, {
    role,
    content,
    metadata,
  })
  return response.data
}

export async function addMessagesBulk(workflowId, conversationId, messages) {
  const response = await conversationsApi.addMessagesBulk(workflowId, conversationId, messages)
  return response.data
}

export function getTimeGroupLabel(group) {
  const labels = {
    today: 'Today',
    yesterday: 'Yesterday',
    previous_7_days: 'Previous 7 Days',
    previous_30_days: 'Previous 30 Days',
    older: 'Older',
  }
  return labels[group] || group
}

export function formatConversationDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}
