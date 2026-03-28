import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { usersApi } from '../../services'
import { JarvisLogo, AlertCircleIcon, CheckCircleIcon, EyeIcon, EyeOffIcon } from '../common'
import './EmailVerification.css'

const EmailVerification = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  
  const [step, setStep] = useState('verifying')
  const [error, setError] = useState('')
  const [userInfo, setUserInfo] = useState(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!token) {
      setStep('error')
      setError('Invalid verification link')
      return
    }

    const verifyToken = async () => {
      try {
        const response = await usersApi.verifyEmail(token)
        setUserInfo(response.data)
        setStep('set-password')
      } catch (err) {
        setStep('error')
        setError(err.response?.data?.detail || 'Verification failed. The link may have expired.')
      }
    }

    verifyToken()
  }, [token])

  const handleSetPassword = async (e) => {
    e.preventDefault()
    setError('')

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setSubmitting(true)
    try {
      await usersApi.setPassword(token, password)
      setStep('success')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to set password. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleGoToLogin = () => {
    navigate('/')
  }

  if (step === 'verifying') {
    return (
      <div className="verification-container">
        <div className="verification-background">
          <div className="verification-pattern"></div>
        </div>
        <div className="verification-card">
          <div className="verification-loading-state">
            <div className="verification-logo">
              <JarvisLogo size={48} gradientId="jarvis-verify-gradient" />
            </div>
            <h2>Verifying your email...</h2>
            <div className="verification-spinner-large"></div>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'error') {
    return (
      <div className="verification-container">
        <div className="verification-background">
          <div className="verification-pattern"></div>
        </div>
        <div className="verification-card">
          <div className="verification-error-state">
            <AlertCircleIcon size={48} />
            <h2>Verification Failed</h2>
            <p>{error}</p>
            <p className="error-subtext">Please contact your administrator to resend the verification email.</p>
            <button className="verification-button" onClick={handleGoToLogin}>
              Go to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'set-password') {
    return (
      <div className="verification-container">
        <div className="verification-background">
          <div className="verification-pattern"></div>
        </div>
        <div className="verification-card">
          <div className="verification-header">
            <div className="verification-logo">
              <JarvisLogo size={48} gradientId="jarvis-verify-gradient" />
            </div>
            <h2>Set Your Password</h2>
            {userInfo?.first_name && (
              <p className="welcome-text">Welcome, {userInfo.first_name}!</p>
            )}
            <p className="email-text">{userInfo?.email}</p>
          </div>

          <form onSubmit={handleSetPassword} className="password-form">
            {error && <div className="form-error">{error}</div>}
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <p className="password-hint">Password must be at least 8 characters</p>

            <button 
              type="submit" 
              className="verification-button"
              disabled={submitting}
            >
              {submitting ? 'Activating...' : 'Activate Account'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (step === 'success') {
    return (
      <div className="verification-container">
        <div className="verification-background">
          <div className="verification-pattern"></div>
        </div>
        <div className="verification-card">
          <div className="verification-success-state">
            <div className="success-icon">
              <CheckCircleIcon size={64} />
            </div>
            <h2>Account Activated!</h2>
            <p>Your account has been set up successfully.</p>
            <p className="success-subtext">You can now sign in with your email and password.</p>
            <button className="verification-button" onClick={handleGoToLogin}>
              Sign In
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default EmailVerification
