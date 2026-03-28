import React, { useState, useEffect, useCallback } from 'react'
import LLMSettings from '../llm-settings/LLMSettings'
import EmailSettings from './EmailSettings'
import SlackSettings from './SlackSettings'
import TeamsSettings from './TeamsSettings'
import SSOSettings from './SSOSettings'
import EncryptionSettings from './EncryptionSettings'
import { integrationsApi, llmConfigsApi, ssoApi, encryptionApi } from '../../services'
import './Settings.css'

const TABS = [
  {
    id: 'llm',
    label: 'LLM Providers',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
    ),
  },
  {
    id: 'email',
    label: 'Email / SMTP',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
        <polyline points="22,6 12,13 2,6" />
      </svg>
    ),
  },
  {
    id: 'slack',
    label: 'Slack',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z" />
        <path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z" />
        <path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5z" />
        <path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z" />
        <path d="M14 14.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5z" />
        <path d="M15.5 19H14v1.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5-.67-1.5-1.5-1.5z" />
        <path d="M10 9.5C10 8.67 9.33 8 8.5 8h-5C2.67 8 2 8.67 2 9.5S2.67 11 3.5 11h5c.83 0 1.5-.67 1.5-1.5z" />
        <path d="M8.5 5H10V3.5C10 2.67 9.33 2 8.5 2S7 2.67 7 3.5 7.67 5 8.5 5z" />
      </svg>
    ),
  },
  {
    id: 'teams',
    label: 'Microsoft Teams',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: 'sso',
    label: 'Single Sign-On',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    id: 'encryption',
    label: 'Encryption',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
  },
]

const Settings = ({ currentOrganization }) => {
  const [activeTab, setActiveTab] = useState('llm')
  const [counts, setCounts] = useState({ llm: 0, email: 0, slack: 0, teams: 0, sso: 0, encryption: 0 })

  const loadCounts = useCallback(async () => {
    if (!currentOrganization?.id) return

    try {
      const [llmRes, integrationsRes, ssoRes, encryptionRes] = await Promise.all([
        llmConfigsApi.getAll(currentOrganization.id).catch(() => ({ data: { configs: [] } })),
        integrationsApi.getAll(currentOrganization.id).catch(() => ({ data: { integrations: [] } })),
        ssoApi.getConfigs().catch(() => ({ data: [] })),
        encryptionApi.getKeys(currentOrganization.id).catch(() => ({ data: [] })),
      ])

      const integrations = integrationsRes.data.integrations || []
      const ssoConfigs = Array.isArray(ssoRes.data) ? ssoRes.data : []
      const encryptionKeys = Array.isArray(encryptionRes.data) ? encryptionRes.data : []

      setCounts({
        llm: (llmRes.data.configs || []).length,
        email: integrations.filter((i) => i.integration_type === 'email').length,
        slack: integrations.filter((i) => i.integration_type === 'slack').length,
        teams: integrations.filter((i) => i.integration_type === 'teams').length,
        sso: ssoConfigs.length,
        encryption: encryptionKeys.filter(k => k.is_active).length,
      })
    } catch (err) {
      console.error('Failed to load counts:', err)
    }
  }, [currentOrganization])

  useEffect(() => {
    loadCounts()
  }, [loadCounts])

  const renderTabContent = () => {
    switch (activeTab) {
      case 'llm':
        return <LLMSettings currentOrganization={currentOrganization} />
      case 'email':
        return <EmailSettings currentOrganization={currentOrganization} />
      case 'slack':
        return <SlackSettings currentOrganization={currentOrganization} />
      case 'teams':
        return <TeamsSettings currentOrganization={currentOrganization} />
      case 'sso':
        return <SSOSettings currentOrganization={currentOrganization} />
      case 'encryption':
        return <EncryptionSettings currentOrganization={currentOrganization} />
      default:
        return null
    }
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <div className="settings-header-left">
          <h2>Settings</h2>
          <p>Configure integrations for your organization's workflows and agents.</p>
        </div>
      </div>

      <div className="settings-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            {tab.label}
            {counts[tab.id] > 0 && (
              <span className="settings-tab-count">{counts[tab.id]}</span>
            )}
          </button>
        ))}
      </div>

      <div className="settings-content">
        {renderTabContent()}
      </div>
    </div>
  )
}

export default Settings
