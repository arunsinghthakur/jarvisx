import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, setAuthToken, setCurrentUser } from '../services/api'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const checkAuth = useCallback(async () => {
    try {
      const response = await authApi.me()
      setUser(response.data)
      setCurrentUser(response.data)
    } catch (err) {
      try {
        const refreshResponse = await authApi.refreshWithCookies()
        if (refreshResponse.data.access_token) {
          setAuthToken(refreshResponse.data.access_token)
        }
        
        const userResponse = await authApi.me()
        setUser(userResponse.data)
        setCurrentUser(userResponse.data)
      } catch (refreshErr) {
        setAuthToken(null)
        setUser(null)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = useCallback(async (username, password) => {
    setError(null)
    setLoading(true)
    
    try {
      const response = await authApi.login(username, password)
      const { user: userData } = response.data
      
      setUser(userData)
      setCurrentUser(userData)
      
      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed. Please try again.'
      setError(message)
      return { success: false, error: message }
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logoutWithCookies()
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      setAuthToken(null)
      setCurrentUser(null)
      setUser(null)
    }
  }, [])

  const refreshAuth = useCallback(async () => {
    try {
      await authApi.refreshWithCookies()
      return true
    } catch (err) {
      await logout()
      return false
    }
  }, [logout])

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    permissions: user?.permissions || {},
    isPlatformAdmin: user?.is_platform_admin || false,
    role: user?.role || 'viewer',
    login,
    logout,
    refreshAuth,
    clearError: () => setError(null),
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export default AuthContext

