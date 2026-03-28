import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { usersApi } from '../../services'
import { JarvisLogo, AlertCircleIcon, CheckCircleIcon, EyeIcon, EyeOffIcon } from '../common'
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
        const response = await usersApi.verifyResetToken(token)
        setUserInfo(response.data)
        setStep('reset')
      } catch (err) {
        setStep('error')
        setError(err.response?.data?.detail || 'Invalid or expired reset link.')
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
      await usersApi.resetPassword(token, password)
      setStep('success')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleGoToLogin = () => {
    navigate('/')
  }

  if (step === 'verifying') {
    return (
      <div className="reset-password-container">
        <div className="reset-password-background">
          <div className="reset-password-pattern"></div>
        </div>
        <div className="reset-password-card">
          <div className="reset-password-loading">
            <div className="reset-password-logo">
              <JarvisLogo size={48} gradientId="jarvis-reset-gradient" />
            </div>
            <h2>Verifying reset link...</h2>
            <div className="reset-password-spinner"></div>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'error') {
    return (
      <div className="reset-password-container">
        <div className="reset-password-background">
          <div className="reset-password-pattern"></div>
        </div>
        <div className="reset-password-card">
          <div className="reset-password-error">
            <AlertCircleIcon size={48} />
            <h2>Reset Link Invalid</h2>
            <p>{error}</p>
            <p className="error-subtext">Please request a new password reset link.</p>
            <button className="reset-password-button" onClick={() => navigate('/forgot-password')}>
              Request New Link
            </button>
            <button className="back-button" onClick={handleGoToLogin}>
              Back to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'reset') {
    return (
      <div className="reset-password-container">
        <div className="reset-password-background">
          <div className="reset-password-pattern"></div>
        </div>
        <div className="reset-password-card">
          <div className="reset-password-header">
            <div className="reset-password-logo">
              <JarvisLogo size={48} gradientId="jarvis-reset-gradient" />
            </div>
            <h2>Reset Password</h2>
            {userInfo?.email && (
              <p className="email-text">{userInfo.email}</p>
            )}
          </div>

          <form onSubmit={handleResetPassword} className="reset-password-form">
            {error && <div className="form-error">{error}</div>}
            
            <div className="form-group">
              <label htmlFor="password">New Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
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
                  placeholder="Confirm new password"
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
              className="reset-password-button"
              disabled={submitting}
            >
              {submitting ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (step === 'success') {
    return (
      <div className="reset-password-container">
        <div className="reset-password-background">
          <div className="reset-password-pattern"></div>
        </div>
        <div className="reset-password-card">
          <div className="reset-password-success">
            <div className="success-icon">
              <CheckCircleIcon size={64} />
            </div>
            <h2>Password Reset!</h2>
            <p>Your password has been reset successfully.</p>
            <p className="success-subtext">You can now sign in with your new password.</p>
            <button className="reset-password-button" onClick={handleGoToLogin}>
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

