import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../../services/api'
import './Login.css'

const SSOCallback = ({ onLoginSuccess }) => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('processing')
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      const success = searchParams.get('success')
      const errorParam = searchParams.get('error')
      const errorMessage = searchParams.get('message')

      if (errorParam) {
        setStatus('error')
        setError(errorMessage || 'SSO authentication failed')
        setTimeout(() => navigate('/login'), 3000)
        return
      }

      if (success === 'true') {
        try {
          const response = await authApi.me()
          if (response.data) {
            setStatus('success')
            if (onLoginSuccess) {
              onLoginSuccess()
            }
            setTimeout(() => {
              window.location.href = '/dashboard'
            }, 1000)
          }
        } catch (err) {
          setStatus('error')
          setError('Failed to verify authentication')
          setTimeout(() => navigate('/login'), 3000)
        }
        return
      }

      setStatus('error')
      setError('Invalid callback parameters')
      setTimeout(() => navigate('/login'), 3000)
    }

    handleCallback()
  }, [searchParams, navigate, onLoginSuccess])

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-pattern"></div>
      </div>

      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <div style={{ fontSize: '48px' }}>
              {status === 'processing' && '⏳'}
              {status === 'success' && '✓'}
              {status === 'error' && '✕'}
            </div>
          </div>
          <h1>
            {status === 'processing' && 'Signing in...'}
            {status === 'success' && 'Success!'}
            {status === 'error' && 'Error'}
          </h1>
          <p className="login-subtitle">
            {status === 'processing' && 'Completing SSO authentication'}
            {status === 'success' && 'Redirecting to dashboard...'}
            {status === 'error' && error}
          </p>
        </div>

        {status === 'processing' && (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '24px' }}>
            <div className="login-spinner" style={{ width: '32px', height: '32px' }}></div>
          </div>
        )}

        {status === 'error' && (
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              Redirecting to login page...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default SSOCallback
