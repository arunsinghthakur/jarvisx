import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { passwordApi } from '../../lib/auth'
import { JarvisLogo, AlertCircleIcon, CheckCircleIcon, EmailIcon } from '../common'
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
      await passwordApi.forgotPassword(email)
      setSuccess(true)
    } catch (err) {
      setError(err.message || 'Failed to send reset email')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="voice-forgot-container">
        <div className="voice-forgot-card">
          <div className="voice-forgot-success">
            <div className="success-icon">
              <CheckCircleIcon size={48} />
            </div>
            <h2>Check Your Email</h2>
            <p>If an account exists for <strong>{email}</strong>, we've sent a password reset link.</p>
            <button className="voice-forgot-button" onClick={() => navigate('/')}>
              Back to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="voice-forgot-container">
      <div className="voice-forgot-card">
        <div className="voice-forgot-header">
          <div className="voice-forgot-logo">
            <JarvisLogo size={56} gradientId="jarvis-forgot-gradient" />
          </div>
          <h1>Forgot Password?</h1>
          <p>Enter your email to receive a reset link</p>
        </div>

        <form onSubmit={handleSubmit} className="voice-forgot-form">
          {error && (
            <div className="voice-forgot-error">
              <AlertCircleIcon size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="voice-forgot-field">
            <div className="voice-input-wrapper">
              <span className="voice-input-icon"><EmailIcon size={18} /></span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                required
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="voice-forgot-button" disabled={loading}>
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>

          <button type="button" className="voice-back-button" onClick={() => navigate('/')}>
            Back to Login
          </button>
        </form>
      </div>
    </div>
  )
}

export default ForgotPassword

