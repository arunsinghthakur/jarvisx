import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { JarvisLogo, AlertCircleIcon, EmailIcon, LockIcon, EyeIcon, EyeOffIcon } from '../common'
import { ssoApi } from '../../services/api'
import './Login.css'

const PROVIDER_CONFIG = {
  google: { icon: 'G', label: 'Google', color: '#4285f4' },
  microsoft: { icon: 'M', label: 'Microsoft', color: '#00a4ef' },
  okta: { icon: 'O', label: 'Okta', color: '#007dc1' },
  saml: { icon: 'S', label: 'SSO', color: '#6366f1' },
}

const Login = ({ onLogin, error: externalError, loading }) => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [ssoInfo, setSsoInfo] = useState(null)
  const [ssoLoading, setSsoLoading] = useState(false)

  const discoverSSO = useCallback(async (emailOrSlug, type = 'email') => {
    setSsoLoading(true)
    setError('')
    
    try {
      const params = type === 'email' ? { email: emailOrSlug } : { org_slug: emailOrSlug }
      const response = await ssoApi.discover(params)
      const data = response.data
      
      if (data.has_sso) {
        setSsoInfo(data)
        setStep('sso')
      } else {
        setStep('password')
      }
    } catch (err) {
      console.error('SSO discovery error:', err)
      setStep('password')
    } finally {
      setSsoLoading(false)
    }
  }, [])

  useEffect(() => {
    const orgSlug = searchParams.get('org')
    const errorParam = searchParams.get('error')
    
    if (errorParam) {
      setError('SSO authentication failed. Please try again.')
    }
    
    if (orgSlug) {
      discoverSSO(orgSlug, 'slug')
    }
  }, [searchParams, discoverSSO])

  const handleEmailContinue = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!email.trim()) {
      setError('Please enter your email address')
      return
    }
    
    if (!email.includes('@')) {
      setError('Please enter a valid email address')
      return
    }
    
    await discoverSSO(email.trim(), 'email')
  }

  const handleSSOLogin = async () => {
    if (!ssoInfo) return
    
    setError('')
    setSsoLoading(true)
    
    try {
      const returnUrl = sessionStorage.getItem('sso_return_url') || window.location.pathname + window.location.search
      sessionStorage.setItem('sso_return_url', returnUrl)
      
      const response = await ssoApi.initiate({
        organization_id: ssoInfo.organization_id,
        provider: ssoInfo.provider,
        redirect_uri: `${window.location.origin}/api/auth/sso/callback`,
        app_type: 'voice',
      })
      
      window.location.href = response.data.authorization_url
    } catch (err) {
      console.error('SSO initiation error:', err)
      setError(err.response?.data?.detail || 'Failed to initiate SSO login')
      setSsoLoading(false)
    }
  }

  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!password) {
      setError('Please enter your password')
      return
    }
    
    onLogin(email.trim(), password)
  }

  const handleBack = () => {
    setStep('email')
    setPassword('')
    setSsoInfo(null)
    setError('')
  }

  const handleUsePassword = () => {
    setStep('password')
    setError('')
  }

  const providerConfig = ssoInfo ? PROVIDER_CONFIG[ssoInfo.provider] || PROVIDER_CONFIG.saml : null

  return (
    <div className="voice-login-container">
      <div className="voice-login-card">
        <div className="voice-login-header">
          <div className="voice-login-logo">
            <JarvisLogo size={56} gradientId="jarvis-login-gradient" />
          </div>
          <h1>JarvisX</h1>
          <p>Voice Assistant</p>
        </div>

        {(error || externalError) && (
          <div className="voice-login-error">
            <AlertCircleIcon size={16} />
            <span>{error || externalError}</span>
          </div>
        )}

        {/* Step 1: Email Entry */}
        {step === 'email' && (
          <form onSubmit={handleEmailContinue} className="voice-login-form">
            <div className="voice-login-field">
              <div className="voice-input-wrapper">
                <span className="voice-input-icon"><EmailIcon size={18} /></span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  autoFocus
                  disabled={ssoLoading}
                />
              </div>
              <span className="voice-field-hint">We'll check if your organization uses SSO</span>
            </div>

            <button type="submit" className="voice-login-button" disabled={ssoLoading}>
              {ssoLoading ? 'Checking...' : 'Continue'}
            </button>
          </form>
        )}

        {/* Step 2a: SSO Login */}
        {step === 'sso' && ssoInfo && (
          <div className="voice-login-form">
            <div className="voice-email-display">
              <span>{email}</span>
              <button type="button" onClick={handleBack}>Change</button>
            </div>

            <div className="voice-sso-section">
              <div className="voice-sso-org">
                <div className="voice-org-badge">
                  {ssoInfo.organization_name?.charAt(0).toUpperCase()}
                </div>
                <div className="voice-org-details">
                  <span className="voice-org-name">{ssoInfo.organization_name}</span>
                  <span className="voice-org-hint">Sign in with your organization account</span>
                </div>
              </div>

              <button
                type="button"
                className="voice-sso-button"
                onClick={handleSSOLogin}
                disabled={ssoLoading}
                style={{ '--provider-color': providerConfig?.color }}
              >
                <span className="voice-provider-icon">{providerConfig?.icon}</span>
                {ssoLoading ? 'Redirecting...' : `Continue with ${ssoInfo.provider_label}`}
              </button>

              <div className="voice-divider">
                <span>or</span>
              </div>

              <button
                type="button"
                className="voice-password-fallback"
                onClick={handleUsePassword}
                disabled={ssoLoading}
              >
                Sign in with password instead
              </button>
            </div>
          </div>
        )}

        {/* Step 2b: Password Login */}
        {step === 'password' && (
          <form onSubmit={handlePasswordLogin} className="voice-login-form">
            <div className="voice-email-display">
              <span>{email}</span>
              <button type="button" onClick={handleBack}>Change</button>
            </div>

            <div className="voice-login-field">
              <div className="voice-input-wrapper">
                <span className="voice-input-icon"><LockIcon size={18} /></span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  autoFocus
                  disabled={loading}
                />
                <button
                  type="button"
                  className="voice-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <button type="submit" className="voice-login-button" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>

            <div className="voice-forgot-link">
              <button type="button" onClick={() => navigate('/forgot-password')}>
                Forgot password?
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default Login
