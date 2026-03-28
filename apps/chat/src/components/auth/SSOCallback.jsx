import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../../services/api'
import './Login.css'

const SSOCallback = () => {
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
        setTimeout(() => navigate('/'), 3000)
        return
      }

      if (success === 'true') {
        try {
          const response = await authApi.me()
          if (response.data) {
            setStatus('success')
            const returnUrl = sessionStorage.getItem('sso_return_url') || '/'
            sessionStorage.removeItem('sso_return_url')
            setTimeout(() => {
              window.location.href = returnUrl
            }, 1000)
          }
        } catch (err) {
          setStatus('error')
          setError('Failed to verify authentication')
          setTimeout(() => navigate('/'), 3000)
        }
        return
      }

      setStatus('error')
      setError('Invalid callback parameters')
      setTimeout(() => navigate('/'), 3000)
    }

    handleCallback()
  }, [searchParams, navigate])

  return (
    <div className="voice-login-container">
      <div className="voice-login-background">
        <div className="voice-orb voice-orb-1"></div>
        <div className="voice-orb voice-orb-2"></div>
        <div className="voice-orb voice-orb-3"></div>
      </div>

      <div className="voice-login-card">
        <div className="voice-login-header">
          <div className="voice-login-icon">
            <div style={{ fontSize: '48px' }}>
              {status === 'processing' && '⏳'}
              {status === 'success' && '✓'}
              {status === 'error' && '✕'}
            </div>
          </div>
          <h1 className="voice-login-title">
            {status === 'processing' && 'Signing in...'}
            {status === 'success' && 'Success!'}
            {status === 'error' && 'Error'}
          </h1>
          <p className="voice-login-subtitle">
            {status === 'processing' && 'Completing SSO authentication'}
            {status === 'success' && 'Redirecting to voice assistant...'}
            {status === 'error' && error}
          </p>
        </div>

        {status === 'processing' && (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '24px' }}>
            <div className="voice-login-spinner"></div>
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
