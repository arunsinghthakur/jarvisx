import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { passwordApi } from '../../lib/auth'
import { JarvisLogo, AlertCircleIcon, CheckCircleIcon, LockIcon, EyeIcon, EyeOffIcon } from '../common'
import './ResetPassword.css'

const ResetPassword = () => {
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
      setError('Invalid reset link')
      return
    }

    const verifyToken = async () => {
      try {
        const response = await passwordApi.verifyResetToken(token)
        setUserInfo(response)
        setStep('reset')
      } catch (err) {
        setStep('error')
        setError(err.message || 'Invalid or expired reset link')
      }
    }

    verifyToken()
  }, [token])

  const handleResetPassword = async (e) => {
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
      await passwordApi.resetPassword(token, password)
      setStep('success')
    } catch (err) {
      setError(err.message || 'Failed to reset password')
    } finally {
      setSubmitting(false)
    }
  }

  if (step === 'verifying') {
    return (
      <div className="voice-reset-container">
        <div className="voice-reset-card">
          <div className="voice-reset-loading">
            <div className="voice-reset-logo">
              <JarvisLogo size={56} gradientId="jarvis-reset-gradient" />
            </div>
            <h2>Verifying...</h2>
            <div className="voice-reset-spinner"></div>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'error') {
    return (
      <div className="voice-reset-container">
        <div className="voice-reset-card">
          <div className="voice-reset-error-state">
            <AlertCircleIcon size={48} />
            <h2>Link Invalid</h2>
            <p>{error}</p>
            <button className="voice-reset-button" onClick={() => navigate('/forgot-password')}>
              Request New Link
            </button>
            <button className="voice-back-button" onClick={() => navigate('/')}>
              Back to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'reset') {
    return (
      <div className="voice-reset-container">
        <div className="voice-reset-card">
          <div className="voice-reset-header">
            <div className="voice-reset-logo">
              <JarvisLogo size={56} gradientId="jarvis-reset-gradient" />
            </div>
            <h1>Reset Password</h1>
            {userInfo?.email && <p className="email-text">{userInfo.email}</p>}
          </div>

          <form onSubmit={handleResetPassword} className="voice-reset-form">
            {error && (
              <div className="voice-reset-error">
                <AlertCircleIcon size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="voice-reset-field">
              <div className="voice-input-wrapper">
                <span className="voice-input-icon"><LockIcon size={18} /></span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="New Password"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  className="voice-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <div className="voice-reset-field">
              <div className="voice-input-wrapper">
                <span className="voice-input-icon"><LockIcon size={18} /></span>
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm Password"
                  required
                />
                <button
                  type="button"
                  className="voice-password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <p className="password-hint">Password must be at least 8 characters</p>

            <button type="submit" className="voice-reset-button" disabled={submitting}>
              {submitting ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (step === 'success') {
    return (
      <div className="voice-reset-container">
        <div className="voice-reset-card">
          <div className="voice-reset-success">
            <div className="success-icon">
              <CheckCircleIcon size={48} />
            </div>
            <h2>Password Reset!</h2>
            <p>Your password has been reset successfully.</p>
            <button className="voice-reset-button" onClick={() => navigate('/')}>
              Sign In
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default ResetPassword

