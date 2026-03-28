import axios from 'axios'

const API_BASE = ''

const getCsrfToken = () => {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

const publicApi = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

let authToken = null
let currentUser = null

export const setAuthToken = (token) => {
  authToken = token
}

export const setCurrentUser = (user) => {
  currentUser = user
}

export const setCurrentOrganization = (organizationId) => {
  if (currentUser) {
    currentUser = { ...currentUser, organization_id: organizationId }
  }
}

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers['Authorization'] = `Bearer ${authToken}`
  }
  if (currentUser) {
    if (currentUser.organization_id) {
      config.headers['x-tenant-id'] = currentUser.organization_id
    }
    if (currentUser.id) {
      config.headers['x-user-id'] = currentUser.id
    }
  }
  
  const stateChangingMethods = ['post', 'put', 'patch', 'delete']
  if (stateChangingMethods.includes(config.method?.toLowerCase())) {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      config.headers['x-csrf-token'] = csrfToken
    }
  }
  
  return config
})

const AUTH_ENDPOINTS = ['/api/auth/me', '/api/auth/refresh', '/api/auth/login', '/api/auth/logout']

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requestUrl = error.config?.url || ''
    const isAuthEndpoint = AUTH_ENDPOINTS.some(endpoint => requestUrl.includes(endpoint))
    
    if (error.response?.status === 401 && !error.config._retry && !isAuthEndpoint) {
      error.config._retry = true
      try {
        await api.post('/api/auth/refresh', {})
        return api(error.config)
      } catch (refreshError) {
        setAuthToken(null)
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (email, password) => 
    axios.post(`${API_BASE}/api/auth/login`, { email, password }, { withCredentials: true }),
  
  refresh: (refreshToken) => 
    axios.post(`${API_BASE}/api/auth/refresh`, { refresh_token: refreshToken }, { withCredentials: true }),
  
  refreshWithCookies: () => 
    api.post('/api/auth/refresh', {}),
  
  logout: (refreshToken) => 
    api.post('/api/auth/logout', { refresh_token: refreshToken }),
  
  logoutWithCookies: () => 
    api.post('/api/auth/logout', {}),
  
  me: () => api.get('/api/auth/me'),
  
  changePassword: (currentPassword, newPassword) =>
    api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    }),
}

export const organizationsApi = {
  getAll: () => api.get('/api/organizations'),
  create: (data) => api.post('/api/organizations', data),
  update: (id, data) => api.put(`/api/organizations/${id}`, data),
  delete: (id) => api.delete(`/api/organizations/${id}`),
}

export const workspacesApi = {
  getAll: () => api.get('/api/workspaces'),
  getById: (id) => api.get(`/api/workspaces/${id}`),
  create: (data) => api.post('/api/workspaces', data),
  update: (id, data) => api.put(`/api/workspaces/${id}`, data),
  delete: (id) => api.delete(`/api/workspaces/${id}`),
}

export const agentsApi = {
  getAll: () => api.get('/api/available/agents'),
  create: (data) => api.post('/api/available/agents', data),
  update: (id, data) => api.put(`/api/available/agents/${id}`, data),
  delete: (id) => api.delete(`/api/available/agents/${id}`),
  getMcps: (agentId) => api.get(`/api/available/agents/${agentId}/mcps`),
  getHierarchyDefinitions: () => api.get('/api/available/agents/hierarchy/definitions'),
}

export const mcpsApi = {
  getAll: () => api.get('/api/available/mcps'),
  create: (data) => api.post('/api/available/mcps', data),
  update: (id, data) => api.put(`/api/available/mcps/${id}`, data),
  delete: (id) => api.delete(`/api/available/mcps/${id}`),
  getAgents: (mcpId) => api.get(`/api/available/mcps/${mcpId}/agents`),
}

export const billingApi = {
  getPlans: () => api.get('/api/billing/plans'),
  getPlan: (planId) => api.get(`/api/billing/plans/${planId}`),
  getSubscription: (organizationId) => api.get(`/api/billing/subscription/${organizationId}`),
  updateSubscription: (organizationId, data) => api.put(`/api/billing/subscription/${organizationId}`, data),
  getUsage: (organizationId, periodStart, periodEnd) => {
    const params = new URLSearchParams()
    if (periodStart) params.append('period_start', periodStart)
    if (periodEnd) params.append('period_end', periodEnd)
    return api.get(`/api/billing/usage/${organizationId}?${params.toString()}`)
  },
  getInvoices: (organizationId, limit = 12) => api.get(`/api/billing/invoices/${organizationId}?limit=${limit}`),
  getOverview: (organizationId) => api.get(`/api/billing/overview/${organizationId}`),
}

export const teamsApi = {
  getAll: () => api.get('/api/teams'),
  getById: (id) => api.get(`/api/teams/${id}`),
  create: (data) => api.post('/api/teams', data),
  update: (id, data) => api.put(`/api/teams/${id}`, data),
  delete: (id) => api.delete(`/api/teams/${id}`),
  
  getMembers: (teamId) => api.get(`/api/teams/${teamId}/members`),
  addMember: (teamId, data) => api.post(`/api/teams/${teamId}/members`, data),
  updateMember: (teamId, memberId, data) => api.put(`/api/teams/${teamId}/members/${memberId}`, data),
  removeMember: (teamId, memberId) => api.delete(`/api/teams/${teamId}/members/${memberId}`),
  
  getOrganizationUsers: (orgId) => api.get(`/api/teams/organization/${orgId}/users`),
  getOrganizationWorkspaces: (orgId) => api.get(`/api/teams/organization/${orgId}/workspaces`),
  inviteUser: (orgId, data) => api.post(`/api/teams/organization/${orgId}/users`, data),
}

export const healthApi = {
  checkAdminApi: async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`, { timeout: 5000 })
      return { status: 'online', data: response.data }
    } catch (error) {
      return { status: 'offline', error: error.message }
    }
  },
  
  checkAgent: async (agentId) => {
    try {
      const response = await api.get(`/api/available/agents/${agentId}/health`, { timeout: 10000 })
      return response.data
    } catch (error) {
      return { status: 'offline', error: error.message }
    }
  },

  checkAllAgents: async () => {
    try {
      const response = await api.get('/api/available/agents/health/all', { timeout: 30000 })
      return response.data
    } catch (error) {
      console.error('Failed to check all agents health:', error)
      return {}
    }
  },
}

export const llmConfigsApi = {
  getProviders: (organizationId) => api.get(`/api/organizations/${organizationId}/llm-configs/providers`),
  getAll: (organizationId) => api.get(`/api/organizations/${organizationId}/llm-configs`),
  getById: (organizationId, configId) => api.get(`/api/organizations/${organizationId}/llm-configs/${configId}`),
  create: (organizationId, data) => api.post(`/api/organizations/${organizationId}/llm-configs`, data),
  update: (organizationId, configId, data) => api.put(`/api/organizations/${organizationId}/llm-configs/${configId}`, data),
  delete: (organizationId, configId) => api.delete(`/api/organizations/${organizationId}/llm-configs/${configId}`),
  setDefault: (organizationId, configId) => api.post(`/api/organizations/${organizationId}/llm-configs/${configId}/set-default`),
  test: (organizationId, configId) => api.post(`/api/organizations/${organizationId}/llm-configs/${configId}/test`),
}

export const usersApi = {
  getByOrganization: (orgId) => api.get(`/api/teams/organization/${orgId}/users`),
  invite: (orgId, data) => api.post(`/api/teams/organization/${orgId}/users`, data),
  update: (userId, data) => api.put(`/api/users/${userId}`, data),
  delete: (userId) => api.delete(`/api/users/${userId}`),
  verifyEmail: (token) => publicApi.get(`/api/teams/verify-email?token=${encodeURIComponent(token)}`),
  setPassword: (token, password) => publicApi.post('/api/teams/set-password', { token, password }),
  resendVerification: (userId) => api.post('/api/teams/resend-verification', { user_id: userId }),
  forgotPassword: (email) => publicApi.post('/api/teams/forgot-password', { email }),
  verifyResetToken: (token) => publicApi.get(`/api/teams/reset-password/verify?token=${encodeURIComponent(token)}`),
  resetPassword: (token, password) => publicApi.post('/api/teams/reset-password', { token, password }),
}

export const workflowsApi = {
  getAll: (workspaceId) => api.get(`/api/workflows?workspace_id=${workspaceId}`),
  getById: (workflowId) => api.get(`/api/workflows/${workflowId}`),
  create: (workspaceId, data) => api.post(`/api/workflows?workspace_id=${workspaceId}`, data),
  update: (workflowId, data) => api.put(`/api/workflows/${workflowId}`, data),
  delete: (workflowId) => api.delete(`/api/workflows/${workflowId}`),
  execute: (workflowId, data = {}) => api.post(`/api/workflows/${workflowId}/execute`, data),
  getExecutions: (workflowId, limit = 50) => api.get(`/api/workflows/${workflowId}/executions?limit=${limit}`),
  getExecution: (executionId) => api.get(`/api/workflows/executions/${executionId}`),
  getDeadLetters: (workflowId, status, limit = 50) => {
    const params = new URLSearchParams()
    if (workflowId) params.append('workflow_id', workflowId)
    if (status) params.append('status', status)
    params.append('limit', limit)
    return api.get(`/api/workflows/dead-letters?${params.toString()}`)
  },
  retryDeadLetter: (id) => api.post(`/api/workflows/dead-letters/${id}/retry`),
  discardDeadLetter: (id) => api.post(`/api/workflows/dead-letters/${id}/discard`),
  getVersions: (workflowId) => api.get(`/api/workflows/${workflowId}/versions`),
  getVersion: (workflowId, versionId) => api.get(`/api/workflows/${workflowId}/versions/${versionId}`),
  restoreVersion: (workflowId, versionId) => api.post(`/api/workflows/${workflowId}/versions/${versionId}/restore`),
  debugStart: (workflowId, triggerData = {}) => api.post(`/api/workflows/${workflowId}/debug/start`, triggerData),
  debugStep: (workflowId, executionId) => api.post(`/api/workflows/${workflowId}/debug/${executionId}/step`),
  debugResume: (workflowId, executionId, breakpoints = []) => api.post(`/api/workflows/${workflowId}/debug/${executionId}/resume`, { breakpoints }),
  debugState: (workflowId, executionId) => api.get(`/api/workflows/${workflowId}/debug/${executionId}/state`),
  debugInject: (workflowId, executionId, data) => api.post(`/api/workflows/${workflowId}/debug/${executionId}/inject`, data),
  debugStop: (workflowId, executionId) => api.post(`/api/workflows/${workflowId}/debug/${executionId}/stop`),
  exportWorkflow: (workflowId) => api.get(`/api/workflows/${workflowId}/export`),
  importWorkflow: (workspaceId, data) => api.post(`/api/workflows/import?workspace_id=${workspaceId}`, data),
}

export const dashboardApi = {
  getStats: () => api.get('/api/dashboard/stats'),
  getActivity: (limit = 20) => api.get(`/api/dashboard/activity?limit=${limit}`),
  getExecutionTrends: (days = 7) => api.get(`/api/dashboard/execution-trends?days=${days}`),
  getCostSummary: () => api.get('/api/dashboard/costs'),
  getCostsByWorkflow: (days = 30) => api.get(`/api/dashboard/costs/by-workflow?days=${days}`),
  getCostsByAgent: (days = 30) => api.get(`/api/dashboard/costs/by-agent?days=${days}`),
  getCostTrends: (days = 30) => api.get(`/api/dashboard/costs/trends?days=${days}`),
}

export const platformApi = {
  getOverview: () => api.get('/api/platform/overview'),
  getOrganizations: (skip = 0, limit = 50, includeInactive = true) => 
    api.get(`/api/platform/organizations?skip=${skip}&limit=${limit}&include_inactive=${includeInactive}`),
  getUsageTrends: (days = 30) => api.get(`/api/platform/usage-trends?days=${days}`),
  getPlatformBilling: () => api.get('/api/platform/billing'),
  browseDirectories: (path = '') => api.get(`/api/platform/browse-directories?path=${encodeURIComponent(path)}`),
  browseFiles: (path = '', extensions = '') => {
    const params = new URLSearchParams()
    if (path) params.append('path', path)
    if (extensions) params.append('extensions', extensions)
    return api.get(`/api/platform/browse-files?${params.toString()}`)
  },
  getSettings: () => api.get('/api/platform/settings'),
  getSettingsCategory: (category) => api.get(`/api/platform/settings/${category}`),
  updateSetting: (category, key, value) => api.put(`/api/platform/settings/${category}/${key}`, { value }),
}

export const templateApi = {
  getAll: (category, search) => {
    const params = new URLSearchParams()
    if (category) params.append('category', category)
    if (search) params.append('search', search)
    return api.get(`/api/workflow-templates?${params.toString()}`)
  },
  getById: (id) => api.get(`/api/workflow-templates/${id}`),
  create: (data) => api.post('/api/workflow-templates', data),
  use: (id, workspaceId, name) => api.post(`/api/workflow-templates/${id}/use`, { workspace_id: workspaceId, name }),
}

export const knowledgeBaseApi = {
  getStats: (organizationId) => api.get(`/api/organizations/${organizationId}/knowledge-base/stats`),
  getEntries: (organizationId, params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.entry_type) queryParams.append('entry_type', params.entry_type)
    if (params.skip) queryParams.append('skip', params.skip)
    if (params.limit) queryParams.append('limit', params.limit)
    const query = queryParams.toString()
    return api.get(`/api/organizations/${organizationId}/knowledge-base/entries${query ? `?${query}` : ''}`)
  },
  getEntry: (organizationId, entryId) => api.get(`/api/organizations/${organizationId}/knowledge-base/entries/${entryId}`),
  getEntryContent: (organizationId, entryId) => api.get(`/api/organizations/${organizationId}/knowledge-base/entries/${entryId}/content`),
  createSnippet: (organizationId, data) => api.post(`/api/organizations/${organizationId}/knowledge-base/snippets`, data),
  updateSnippet: (organizationId, entryId, data) => api.put(`/api/organizations/${organizationId}/knowledge-base/snippets/${entryId}`, data),
  uploadDocument: (organizationId, file, title) => {
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    return api.post(`/api/organizations/${organizationId}/knowledge-base/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deleteEntry: (organizationId, entryId) => api.delete(`/api/organizations/${organizationId}/knowledge-base/entries/${entryId}`),
  search: (organizationId, query, limit = 5, threshold = 0.7) => 
    api.post(`/api/organizations/${organizationId}/knowledge-base/search`, { query, limit, similarity_threshold: threshold }),
}

export const complianceApi = {
  getConfig: () => api.get('/api/compliance/config'),
  updateConfig: (data) => api.put('/api/compliance/config', data),
  
  getPiiPatterns: (includeSystem = true) => 
    api.get(`/api/compliance/pii-patterns?include_system=${includeSystem}`),
  createPiiPattern: (data) => api.post('/api/compliance/pii-patterns', data),
  updatePiiPattern: (id, data) => api.put(`/api/compliance/pii-patterns/${id}`, data),
  deletePiiPattern: (id) => api.delete(`/api/compliance/pii-patterns/${id}`),
  
  getPolicies: (includeSystem = true, ruleType = null) => {
    const params = new URLSearchParams()
    params.append('include_system', includeSystem)
    if (ruleType) params.append('rule_type', ruleType)
    return api.get(`/api/compliance/policies?${params.toString()}`)
  },
  createPolicy: (data) => api.post('/api/compliance/policies', data),
  updatePolicy: (id, data) => api.put(`/api/compliance/policies/${id}`, data),
  deletePolicy: (id) => api.delete(`/api/compliance/policies/${id}`),
  
  getAuditLogs: (params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.event_type) queryParams.append('event_type', params.event_type)
    if (params.event_category) queryParams.append('event_category', params.event_category)
    if (params.user_id) queryParams.append('user_id', params.user_id)
    if (params.days_back) queryParams.append('days_back', params.days_back)
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.offset) queryParams.append('offset', params.offset)
    return api.get(`/api/compliance/audit-logs?${queryParams.toString()}`)
  },
  exportAuditLogs: (daysBack = 30) => 
    api.get(`/api/compliance/audit-logs/export?days_back=${daysBack}`),
  
  scanPii: (text) => api.post('/api/compliance/pii/scan', { text }),
  
  getDashboard: () => api.get('/api/compliance/dashboard'),
}

export const tracingApi = {
  getTraces: (params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.offset) queryParams.append('offset', params.offset)
    if (params.start_time) queryParams.append('start_time', params.start_time)
    if (params.end_time) queryParams.append('end_time', params.end_time)
    if (params.name_filter) queryParams.append('name_filter', params.name_filter)
    if (params.status) queryParams.append('status', params.status)
    if (params.tags && params.tags.length > 0) {
      params.tags.forEach(tag => queryParams.append('tags', tag))
    }
    return api.get(`/api/tracing/traces?${queryParams.toString()}`)
  },
  getTrace: (traceId) => api.get(`/api/tracing/traces/${traceId}`),
  getObservations: (traceId) => api.get(`/api/tracing/traces/${traceId}/observations`),
  getStats: (days = 7) => api.get(`/api/tracing/stats?days=${days}`),
}

export const integrationsApi = {
  getTypes: (organizationId) => api.get(`/api/organizations/${organizationId}/integrations/types`),
  getAll: (organizationId, integrationType = null) => {
    const params = integrationType ? `?integration_type=${integrationType}` : ''
    return api.get(`/api/organizations/${organizationId}/integrations${params}`)
  },
  getById: (organizationId, integrationId) => api.get(`/api/organizations/${organizationId}/integrations/${integrationId}`),
  create: (organizationId, data) => api.post(`/api/organizations/${organizationId}/integrations`, data),
  update: (organizationId, integrationId, data) => api.put(`/api/organizations/${organizationId}/integrations/${integrationId}`, data),
  delete: (organizationId, integrationId) => api.delete(`/api/organizations/${organizationId}/integrations/${integrationId}`),
  setDefault: (organizationId, integrationId) => api.post(`/api/organizations/${organizationId}/integrations/${integrationId}/set-default`),
  test: (organizationId, integrationId) => api.post(`/api/organizations/${organizationId}/integrations/${integrationId}/test`),
}

export const ssoApi = {
  getConfigs: () => api.get('/api/sso/configs'),
  getConfig: (configId) => api.get(`/api/sso/configs/${configId}`),
  getConfigWithSecret: (configId) => api.get(`/api/sso/configs/${configId}/with-secret`),
  createConfig: (data) => api.post('/api/sso/configs', data),
  updateConfig: (configId, data) => api.put(`/api/sso/configs/${configId}`, data),
  deleteConfig: (configId) => api.delete(`/api/sso/configs/${configId}`),
  toggleConfig: (configId) => api.post(`/api/sso/configs/${configId}/toggle`),
  
  discover: (params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.email) queryParams.append('email', params.email)
    if (params.domain) queryParams.append('domain', params.domain)
    if (params.org_slug) queryParams.append('org_slug', params.org_slug)
    return publicApi.get(`/api/auth/sso/discover?${queryParams.toString()}`)
  },
  initiate: (data) => publicApi.post('/api/auth/sso/initiate', data),
}

export const encryptionApi = {
  getKeys: (organizationId, includeInactive = false) => {
    const params = new URLSearchParams()
    params.append('organization_id', organizationId)
    if (includeInactive) params.append('include_inactive', 'true')
    return api.get(`/api/admin/encryption-keys/?${params.toString()}`)
  },
  generateKey: (organizationId, purpose = 'sso') => 
    api.post('/api/admin/encryption-keys/generate', { organization_id: organizationId, purpose }),
  rotateKey: (keyId) => 
    api.post(`/api/admin/encryption-keys/${keyId}/rotate`, {}),
  getReencryptionStatus: (organizationId, keyVersion) => 
    api.get(`/api/admin/encryption-keys/reencryption/status/${organizationId}?key_version=${keyVersion}`),
  runReencryption: (organizationId, oldKeyVersion) => 
    api.post(`/api/admin/encryption-keys/reencryption/run/${organizationId}?old_key_version=${oldKeyVersion}`),
}

export default api
