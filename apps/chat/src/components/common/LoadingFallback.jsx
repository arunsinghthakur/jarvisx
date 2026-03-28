import React from 'react'
import './LoadingFallback.css'

const LoadingFallback = ({ message = 'Loading...' }) => {
  return (
    <div className="voice-loading-fallback">
      <div className="voice-loading-content">
        <div className="voice-loading-logo">
          <svg width="64" height="64" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#voice-loading-gradient)"/>
            <circle cx="16" cy="16" r="4" fill="white" className="pulse-circle"/>
            <circle cx="16" cy="16" r="2" fill="url(#voice-loading-gradient)"/>
            <path d="M16 8v4M16 20v4M8 16h4M20 16h4" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round" className="rotate-lines"/>
            <defs>
              <linearGradient id="voice-loading-gradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1"/>
                <stop offset="1" stopColor="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="voice-loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p className="voice-loading-message">{message}</p>
      </div>
    </div>
  )
}

export default LoadingFallback

