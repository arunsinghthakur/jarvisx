import { 
  authApi as apiAuthApi, 
  setAuthToken as apiSetAuthToken, 
  getAuthToken as apiGetAuthToken,
  setCurrentUser as apiSetCurrentUser
} from '../services/api'

export const setAuthToken = apiSetAuthToken
export const getAuthToken = apiGetAuthToken

export const checkAuth = async () => {
  try {
    const response = await apiAuthApi.me()
    const user = response.data
    apiSetCurrentUser(user)
    return user
  } catch (err) {
    try {
      await apiAuthApi.refreshWithCookies()
      
      const meResponse = await apiAuthApi.me()
      const user = meResponse.data
      apiSetCurrentUser(user)
      return user
    } catch (refreshErr) {
      setAuthToken(null)
      return null
    }
  }
}

export const login = async (email, password) => {
  const response = await apiAuthApi.login(email, password)
  const { user } = response.data
  
  apiSetCurrentUser(user)
  
  return user
}

export const logout = async () => {
  try {
    await apiAuthApi.logoutWithCookies()
  } catch (err) {
    console.error('Logout error:', err)
  }
  
  setAuthToken(null)
  apiSetCurrentUser(null)
}

export const passwordApi = {
  forgotPassword: async (email) => {
    const response = await apiAuthApi.forgotPassword(email)
    return response.data
  },
  
  verifyResetToken: async (token) => {
    const response = await apiAuthApi.verifyResetToken(token)
    return response.data
  },
  
  resetPassword: async (token, password) => {
    const response = await apiAuthApi.resetPassword(token, password)
    return response.data
  }
}

