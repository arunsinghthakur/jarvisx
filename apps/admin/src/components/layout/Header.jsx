import React from 'react'
import { JarvisLogo, LogoutIcon } from '../common'
import './Header.css'

function Header({ user, isPlatformAdmin, onLogout }) {
  return (
    <header className="App-header">
      <div className="header-content">
        <div className="header-brand">
          <div className="header-logo">
            <JarvisLogo size={32} gradientId="jarvis-header-gradient" />
          </div>
          <div className="header-text">
            <h1>JarvisX</h1>
            <span className="header-subtitle">Command Center</span>
          </div>
        </div>
        <div className="header-actions">
          <div className="user-info">
            <span className="user-name">{user?.first_name || user?.email}</span>
            <span className="user-org">
              {user?.organization_name}
              {isPlatformAdmin && <span className="platform-badge">Platform Admin</span>}
            </span>
          </div>
          <button className="logout-btn" onClick={onLogout} title="Sign out">
            <LogoutIcon size={18} />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
