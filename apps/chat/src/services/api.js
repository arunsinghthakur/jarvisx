import axios from 'axios'

const API_BASE = ''

const getCsrfToken = () => {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

let authToken = null
let currentUser = null

export const setAuthToken = (token) => {
  authToken = token
}

export const getAuthToken = () => authToken

export const setCurrentUser = (user) => {
  currentUser = user
}

export const getCurrentUser = () => currentUser

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

const speechApi = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

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

speechApi.interceptors.request.use((config) => {
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
  
  forgotPassword: (email) => 
    axios.post(`${API_BASE}/api/teams/forgot-password`, { email }),
  
  verifyResetToken: (token) => 
    axios.get(`${API_BASE}/api/teams/reset-password/verify?token=${encodeURIComponent(token)}`),
  
  resetPassword: (token, password) => 
    axios.post(`${API_BASE}/api/teams/reset-password`, { token, password }),
}

export const ssoApi = {
  discover: (params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.email) queryParams.append('email', params.email)
    if (params.domain) queryParams.append('domain', params.domain)
    if (params.org_slug) queryParams.append('org_slug', params.org_slug)
    return axios.get(`${API_BASE}/api/auth/sso/discover?${queryParams.toString()}`)
  },
  initiate: (data) => axios.post(`${API_BASE}/api/auth/sso/initiate`, data),
}

export const chatbotApi = {
  getConfig: (workflowId, warmup = false) => {
    const url = warmup 
      ? `/api/chatbot/${workflowId}/config?warmup=true`
      : `/api/chatbot/${workflowId}/config`
    return api.get(url)
  },
  
  chat: (workflowId, data) => 
    api.post(`/api/chatbot/${workflowId}/chat`, data),
}

export const workspaceApi = {
  getConfig: (workspaceId) => 
    api.get(`/api/workspace-config/${workspaceId}`),
}

export const conversationsApi = {
  list: (workflowId, params = {}) => {
    const { limit = 30, offset = 0 } = params
    const queryParams = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    return api.get(`/api/chatbot/${workflowId}/conversations?${queryParams}`)
  },
  
  get: (workflowId, conversationId) => 
    api.get(`/api/chatbot/${workflowId}/conversations/${conversationId}`),
  
  update: (workflowId, conversationId, data) => 
    api.patch(`/api/chatbot/${workflowId}/conversations/${conversationId}`, data),
  
  delete: (workflowId, conversationId) => 
    api.delete(`/api/chatbot/${workflowId}/conversations/${conversationId}`),
  
  addMessage: (workflowId, conversationId, data) => 
    api.post(`/api/chatbot/${workflowId}/conversations/${conversationId}/messages`, data),
  
  addMessagesBulk: (workflowId, conversationId, messages) => 
    api.post(`/api/chatbot/${workflowId}/conversations/${conversationId}/messages/bulk`, messages),
}

export const speechApiClient = {
  transcribe: (audioBlob, options = {}) => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'audio.webm')
    if (options.workspaceId) {
      formData.append('workspace_id', options.workspaceId)
    }
    if (options.userId) {
      formData.append('user_id', options.userId)
    }
    
    const headers = {}
    if (options.workspaceId) {
      headers['x-workspace-id'] = options.workspaceId
    }
    if (options.userId) {
      headers['x-user-id'] = options.userId
    }
    
    return speechApi.post('/api/audio/transcribe-only', formData, { headers })
  },
  
  textToSpeech: (text, options = {}) => {
    const body = { text, voice: options.voice || null }
    if (options.workspaceId) {
      body.workspace_id = options.workspaceId
    }
    if (options.userId) {
      body.user_id = options.userId
    }
    
    const headers = {}
    if (options.workspaceId) {
      headers['x-workspace-id'] = options.workspaceId
    }
    if (options.userId) {
      headers['x-user-id'] = options.userId
    }
    
    return speechApi.post('/api/audio/tts', body, { 
      headers,
      responseType: 'blob'
    })
  },
}

export { API_BASE }
export default api
