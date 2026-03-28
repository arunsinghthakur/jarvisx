import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usersApi } from '../../services'
import { JarvisLogo, AlertCircleIcon, CheckCircleIcon } from '../common'
import './ForgotPassword.css'

const ForgotPassword = () => {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await usersApi.forgotPassword(email)
      setSuccess(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleBackToLogin = () => {
    navigate('/')
  }

  if (success) {
    return (
      <div className="forgot-password-container">
        <div className="forgot-password-background">
          <div className="forgot-password-pattern"></div>
        </div>
        <div className="forgot-password-card">
          <div className="forgot-password-success">
            <div className="success-icon">
              <CheckCircleIcon size={64} />
            </div>
            <h2>Check Your Email</h2>
            <p>If an account exists for <strong>{email}</strong>, we've sent a password reset link.</p>
            <p className="success-subtext">The link will expire in 60 minutes.</p>
            <button className="forgot-password-button" onClick={handleBackToLogin}>
              Back to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="forgot-password-container">
      <div className="forgot-password-background">
        <div className="forgot-password-pattern"></div>
      </div>
      <div className="forgot-password-card">
        <div className="forgot-password-header">
          <div className="forgot-password-logo">
            <JarvisLogo size={48} gradientId="jarvis-forgot-gradient" />
          </div>
          <h2>Forgot Password?</h2>
          <p>Enter your email and we'll send you a reset link.</p>
        </div>

        <form onSubmit={handleSubmit} className="forgot-password-form">
          {error && (
            <div className="form-error">
              <AlertCircleIcon size={16} />
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
            />
          </div>

          <button 
            type="submit" 
            className="forgot-password-button"
            disabled={loading}
          >
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>

          <button 
            type="button" 
            className="back-to-login-button"
            onClick={handleBackToLogin}
          >
            Back to Login
          </button>
        </form>
      </div>
    </div>
  )
}

export default ForgotPassword

