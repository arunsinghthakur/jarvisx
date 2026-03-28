import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ssoApi, authApi } from '../../services'
import './SSOLoginFlow.css'

const API_BASE = process.env.REACT_APP_ADMIN_API_BASE || process.env.REACT_APP_API_BASE || 'http://localhost:5002'

/**
 * Multi-Tenant SSO Login Flow
 *
 * This component demonstrates how to implement SSO discovery in a SAAS environment:
 * 1. User enters email OR accesses via org-specific URL
 * 2. System auto-detects if their organization has SSO
 * 3. Shows appropriate login method (SSO button or password field)
 *
 * Supports multiple discovery methods:
 * - Email domain: user@acme.com → detects Acme Corp
 * - URL parameter: /login?org=acme-corp → detects by slug
 * - Direct link: /login/acme-corp → detects by slug
 */
const SSOLoginFlow = () => {
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [step, setStep] = useState('email') // 'email', 'password', 'sso'
  const [ssoInfo, setSSOInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  /**
   * Check for organization in URL on component mount
   */
  useEffect(() => {
    const orgSlug = searchParams.get('org')
    if (orgSlug) {
      // Auto-discover SSO by organization slug
      discoverByOrgSlug(orgSlug)
    }
  }, [searchParams])

  /**
   * Discover SSO by organization slug
   */
  const discoverByOrgSlug = async (orgSlug) => {
    setLoading(true)
    setError(null)

    try {
      const response = await ssoApi.discover({ org_slug: orgSlug })
      const data = response.data

      if (data.has_sso) {
        setSSOInfo(data)
        setStep('sso')
      } else {
        setError(`Organization "${orgSlug}" does not have SSO configured`)
        setStep('email')
      }
    } catch (err) {
      console.error('SSO discovery error:', err)
      setError(err.response?.data?.detail || err.message || 'Organization not found')
      setStep('email')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Step 1: Discover SSO provider based on email domain
   */
  const handleEmailSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await ssoApi.discover({ email })
      const data = response.data

      if (data.has_sso) {
        // Organization has SSO configured
        setSSOInfo(data)
        setStep('sso')
      } else {
        // No SSO, use regular password login
        setStep('password')
      }
    } catch (err) {
      console.error('SSO discovery error:', err)
      // Fallback to password login on error
      setStep('password')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Step 2a: Initiate SSO login (if SSO available)
   */
  const handleSSOLogin = async () => {
    setError(null)
    setLoading(true)

    try {
      const response = await ssoApi.initiate({
        organization_id: ssoInfo.organization_id,
        provider: ssoInfo.provider,
        redirect_uri: `${API_BASE}/api/auth/sso/callback`,
      })

      const data = response.data

      // Redirect to identity provider
      window.location.href = data.authorization_url
    } catch (err) {
      console.error('SSO initiation error:', err)
      setError(err.response?.data?.detail || 'Failed to initiate SSO login. Please try again.')
      setLoading(false)
    }
  }

  /**
   * Step 2b: Regular password login (if no SSO)
   */
  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await authApi.login(email, password)
      const data = response.data

      // Store tokens (using camelCase keys for consistency with AuthContext)
      localStorage.setItem('accessToken', data.access_token)
      localStorage.setItem('refreshToken', data.refresh_token)

      // Redirect to dashboard
      window.location.href = '/dashboard'
    } catch (err) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || err.message || 'Invalid credentials')
      setLoading(false)
    }
  }

  /**
   * Reset to email entry
   */
  const handleBackToEmail = () => {
    setStep('email')
    setSSOInfo(null)
    setError(null)
  }

  return (
    <div className="sso-login-flow">
      <div className="login-card">
        <div className="login-header">
          <h1>Sign in to JarvisX</h1>
        </div>

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}

        {/* Step 1: Email Entry */}
        {step === 'email' && (
          <form onSubmit={handleEmailSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="email">Work Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoFocus
                disabled={loading}
              />
              <small>We'll check if your organization uses SSO</small>
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Checking...' : 'Continue'}
            </button>
          </form>
        )}

        {/* Step 2a: SSO Login */}
        {step === 'sso' && ssoInfo && (
          <div className="sso-login">
            <div className="sso-info">
              <div className="sso-icon">🔐</div>
              <h2>Sign in with SSO</h2>
              <p>
                Your organization <strong>{ssoInfo.organization_name}</strong> uses{' '}
                <strong>{ssoInfo.provider_label}</strong> for authentication.
              </p>
            </div>

            <button
              onClick={handleSSOLogin}
              className="btn-sso"
              disabled={loading}
            >
              {loading ? 'Redirecting...' : `Continue with ${ssoInfo.provider_label}`}
            </button>

            <button
              onClick={handleBackToEmail}
              className="btn-link"
              disabled={loading}
            >
              Use a different email
            </button>

            <div className="login-help">
              <p>
                You'll be redirected to your organization's login page. After signing in,
                you'll return to JarvisX.
              </p>
            </div>
          </div>
        )}

        {/* Step 2b: Password Login */}
        {step === 'password' && (
          <form onSubmit={handlePasswordLogin} className="login-form">
            <div className="form-group">
              <label htmlFor="email-display">Email</label>
              <div className="email-display">
                {email}
                <button
                  type="button"
                  onClick={handleBackToEmail}
                  className="btn-change"
                  disabled={loading}
                >
                  Change
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoFocus
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>

            <div className="login-footer">
              <a href="/forgot-password" className="btn-link">
                Forgot password?
              </a>
            </div>
          </form>
        )}

        <div className="login-divider">
          <span>or</span>
        </div>

        <div className="login-alternatives">
          <p>
            Don't have an account? <a href="/signup">Sign up</a>
          </p>
        </div>

        {step === 'email' && (
          <div className="login-help-text">
            <p>
              <strong>Organization login:</strong> Access via{' '}
              <code>/login?org=your-org-slug</code>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default SSOLoginFlow
