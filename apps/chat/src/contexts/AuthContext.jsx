import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { checkAuth, login as authLogin, logout as authLogout } from '../lib/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const initAuth = useCallback(async () => {
    try {
      const userData = await checkAuth()
      setUser(userData)
    } catch (err) {
      console.error('Auth check failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    initAuth()
  }, [initAuth])

  const login = useCallback(async (email, password) => {
    setError(null)
    try {
      const userData = await authLogin(email, password)
      setUser(userData)
      return userData
    } catch (err) {
      const message = err.message || 'Login failed'
      setError(message)
      throw err
    }
  }, [])

  const logout = useCallback(async () => {
    await authLogout()
    setUser(null)
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    clearError,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext

