import React from 'react'
import { JarvisLogo } from './Icons'
import './LoadingFallback.css'

const LoadingFallback = ({ message = 'Loading...', fullScreen = true }) => {
  return (
    <div className={`loading-fallback ${fullScreen ? 'full-screen' : ''}`}>
      <div className="loading-content">
        <div className="loading-logo">
          <JarvisLogo size={64} gradientId="loading-gradient" />
        </div>
        <div className="loading-spinner-ring">
          <div className="spinner-segment"></div>
          <div className="spinner-segment"></div>
          <div className="spinner-segment"></div>
        </div>
        <p className="loading-message">{message}</p>
      </div>
    </div>
  )
}

export const SectionLoader = ({ message = 'Loading content...' }) => (
  <div className="section-loader">
    <div className="section-loader-spinner"></div>
    <p>{message}</p>
  </div>
)

export const CardLoader = () => (
  <div className="card-loader">
    <div className="card-loader-shimmer"></div>
  </div>
)

export default LoadingFallback
