import React, { useState, useEffect, useCallback } from 'react'
import { PageHeader } from '../common'
import { ssoApi, teamsApi } from '../../services'
import { usePermissions } from '../../hooks'
import './SSOSettings.css'

const PROVIDER_LABELS = {
  google: 'Google OAuth',
  microsoft: 'Microsoft Azure AD',
  okta: 'Okta',
  saml: 'SAML 2.0',
}

const PROVIDER_ICONS = {
  google: '🔍',
  microsoft: '🪟',
  okta: '🔐',
  saml: '🔒',
}

const SSOSettings = ({ currentOrganization }) => {
  const { settings } = usePermissions()
  const ssoPerms = settings.ssoConfigs
  const [configs, setConfigs] = useState([])
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [formData, setFormData] = useState({
    provider: 'google',
    is_enabled: true,
    client_id: '',
    client_secret: '',
    tenant_id: '',
    idp_entity_id: '',
    idp_sso_url: '',
    idp_x509_cert: '',
    sp_entity_id: '',
    allowed_domains: '',
    auto_provision_users: true,
    default_team_id: '',
  })

  const loadConfigs = useCallback(async () => {
    if (!currentOrganization?.id) return

    setLoading(true)
    try {
      const [configsRes, teamsRes] = await Promise.all([
        ssoApi.getConfigs(),
        teamsApi.getAll(),
      ])
      setConfigs(configsRes.data)
      setTeams(teamsRes.data || [])
    } catch (error) {
      console.error('Failed to load SSO configs:', error)
    } finally {
      setLoading(false)
    }
  }, [currentOrganization])

  useEffect(() => {
    loadConfigs()
  }, [loadConfigs])

  const handleCreateOrUpdate = async (e) => {
    e.preventDefault()

    const payload = {
      ...formData,
      allowed_domains: formData.allowed_domains
        ? formData.allowed_domains.split(',').map((d) => d.trim())
        : [],
    }

    try {
      if (editingConfig) {
        await ssoApi.updateConfig(editingConfig.id, payload)
      } else {
        await ssoApi.createConfig(payload)
      }

      await loadConfigs()
      setShowModal(false)
      resetForm()
    } catch (error) {
      const message = error.response?.data?.detail || error.message || 'Failed to save SSO config'
      alert(message)
      console.error('Failed to save SSO config:', error)
    }
  }

  const handleEdit = (config) => {
    setEditingConfig(config)
    setFormData({
      provider: config.provider,
      is_enabled: config.is_enabled,
      client_id: config.client_id || '',
      client_secret: '',
      tenant_id: config.tenant_id || '',
      idp_entity_id: config.idp_entity_id || '',
      idp_sso_url: config.idp_sso_url || '',
      idp_x509_cert: config.idp_x509_cert || '',
      sp_entity_id: config.sp_entity_id || '',
      allowed_domains: (config.allowed_domains || []).join(', '),
      auto_provision_users: config.auto_provision_users,
      default_team_id: config.default_team_id || '',
    })
    setShowModal(true)
  }

  const handleDelete = async (configId) => {
    if (!confirm('Are you sure you want to delete this SSO configuration?')) return

    try {
      await ssoApi.deleteConfig(configId)
      await loadConfigs()
    } catch (error) {
      const message = error.response?.data?.detail || error.message || 'Failed to delete SSO config'
      alert(message)
      console.error('Failed to delete SSO config:', error)
    }
  }

  const handleToggle = async (configId) => {
    try {
      await ssoApi.toggleConfig(configId)
      await loadConfigs()
    } catch (error) {
      const message = error.response?.data?.detail || error.message || 'Failed to toggle SSO config'
      alert(message)
      console.error('Failed to toggle SSO config:', error)
    }
  }

  const resetForm = () => {
    setEditingConfig(null)
    setFormData({
      provider: 'google',
      is_enabled: true,
      client_id: '',
      client_secret: '',
      tenant_id: '',
      idp_entity_id: '',
      idp_sso_url: '',
      idp_x509_cert: '',
      sp_entity_id: '',
      allowed_domains: '',
      auto_provision_users: true,
      default_team_id: '',
    })
  }

  const renderProviderFields = () => {
    const { provider } = formData

    if (provider === 'saml') {
      return (
        <>
          <div className="form-group">
            <label>IdP Entity ID *</label>
            <input
              type="text"
              value={formData.idp_entity_id}
              onChange={(e) => setFormData({ ...formData, idp_entity_id: e.target.value })}
              required
              placeholder="https://idp.example.com/entityid"
            />
          </div>

          <div className="form-group">
            <label>IdP SSO URL *</label>
            <input
              type="url"
              value={formData.idp_sso_url}
              onChange={(e) => setFormData({ ...formData, idp_sso_url: e.target.value })}
              required
              placeholder="https://idp.example.com/sso"
            />
          </div>

          <div className="form-group">
            <label>IdP X.509 Certificate *</label>
            <textarea
              value={formData.idp_x509_cert}
              onChange={(e) => setFormData({ ...formData, idp_x509_cert: e.target.value })}
              required
              rows={8}
              placeholder="-----BEGIN CERTIFICATE-----&#10;MIICmzCCAYMCBgF...&#10;-----END CERTIFICATE-----"
            />
            <small>Paste the X.509 certificate from your Identity Provider</small>
          </div>

          <div className="form-group">
            <label>SP Entity ID (optional)</label>
            <input
              type="text"
              value={formData.sp_entity_id}
              onChange={(e) => setFormData({ ...formData, sp_entity_id: e.target.value })}
              placeholder="https://your-app.com/saml/sp"
            />
            <small>Leave blank to auto-generate</small>
          </div>
        </>
      )
    } else {
      // OAuth2/OIDC fields
      return (
        <>
          <div className="form-group">
            <label>Client ID *</label>
            <input
              type="text"
              value={formData.client_id}
              onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
              required
              placeholder="your-client-id"
            />
          </div>

          <div className="form-group">
            <label>Client Secret *</label>
            <input
              type="password"
              value={formData.client_secret}
              onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
              required={!editingConfig}
              placeholder={editingConfig ? 'Leave blank to keep existing' : 'your-client-secret'}
            />
            {editingConfig && (
              <small>Leave blank to keep the existing secret</small>
            )}
          </div>

          {provider === 'microsoft' && (
            <div className="form-group">
              <label>Tenant ID *</label>
              <input
                type="text"
                value={formData.tenant_id}
                onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value })}
                required
                placeholder="your-tenant-id"
              />
            </div>
          )}
        </>
      )
    }
  }

  return (
    <div className="sso-settings">
      <PageHeader
        title="Single Sign-On (SSO)"
        subtitle="Configure SSO authentication for your organization"
        actionLabel={ssoPerms.canCreate ? "Add SSO Provider" : null}
        onAction={ssoPerms.canCreate ? () => {
          resetForm()
          setShowModal(true)
        } : null}
      />

      {loading ? (
        <div className="loading">Loading SSO configurations...</div>
      ) : configs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🔐</div>
          <h3>No SSO Configurations</h3>
          <p>Add an SSO provider to enable single sign-on for your organization</p>
        </div>
      ) : (
        <div className="sso-configs-list">
          {configs.map((config) => (
            <div key={config.id} className="sso-config-card">
              <div className="config-header">
                <div className="config-info">
                  <div className="config-icon">{PROVIDER_ICONS[config.provider]}</div>
                  <div>
                    <h3>{PROVIDER_LABELS[config.provider]}</h3>
                    <span className={`status-badge ${config.is_enabled ? 'enabled' : 'disabled'}`}>
                      {config.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>
                <div className="config-actions">
                  {ssoPerms.canEdit && (
                    <button
                      className={`toggle-btn ${config.is_enabled ? 'enabled' : ''}`}
                      onClick={() => handleToggle(config.id)}
                    >
                      {config.is_enabled ? 'Disable' : 'Enable'}
                    </button>
                  )}
                  {ssoPerms.canEdit && (
                    <button className="edit-btn" onClick={() => handleEdit(config)}>
                      Edit
                    </button>
                  )}
                  {ssoPerms.canDelete && (
                    <button className="delete-btn" onClick={() => handleDelete(config.id)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>

              <div className="config-details">
                {config.client_id && (
                  <div className="detail-row">
                    <span className="detail-label">Client ID:</span>
                    <span className="detail-value">{config.client_id}</span>
                  </div>
                )}
                {config.tenant_id && (
                  <div className="detail-row">
                    <span className="detail-label">Tenant ID:</span>
                    <span className="detail-value">{config.tenant_id}</span>
                  </div>
                )}
                {config.idp_entity_id && (
                  <div className="detail-row">
                    <span className="detail-label">IdP Entity ID:</span>
                    <span className="detail-value">{config.idp_entity_id}</span>
                  </div>
                )}
                {config.provider === 'saml' && currentOrganization?.slug && (
                  <div className="detail-row saml-urls">
                    <span className="detail-label">SAML URLs:</span>
                    <div className="detail-value saml-url-list">
                      <div className="saml-url-item">
                        <strong>SP-Initiated ACS:</strong>
                        <code>{`${window.location.origin}/api/auth/sso/saml/acs/${config.id}`}</code>
                      </div>
                      <div className="saml-url-item">
                        <strong>IdP-Initiated ACS:</strong>
                        <code>{`${window.location.origin}/api/auth/sso/saml/idp/${currentOrganization.slug}`}</code>
                      </div>
                      <small>Configure these URLs in your Identity Provider</small>
                    </div>
                  </div>
                )}
                {config.allowed_domains && config.allowed_domains.length > 0 && (
                  <div className="detail-row">
                    <span className="detail-label">Allowed Domains:</span>
                    <span className="detail-value">{config.allowed_domains.join(', ')}</span>
                  </div>
                )}
                <div className="detail-row">
                  <span className="detail-label">Auto-provision Users:</span>
                  <span className="detail-value">{config.auto_provision_users ? 'Yes' : 'No'}</span>
                </div>
                {config.auto_provision_users && config.default_team_name && (
                  <div className="detail-row">
                    <span className="detail-label">Default Team:</span>
                    <span className="detail-value">{config.default_team_name}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => { setShowModal(false); resetForm(); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingConfig ? 'Edit SSO Configuration' : 'Add SSO Provider'}</h2>
              <button className="close-btn" onClick={() => { setShowModal(false); resetForm(); }}>
                ×
              </button>
            </div>

            <form onSubmit={handleCreateOrUpdate}>
              <div className="form-group">
                <label>Provider *</label>
                <select
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  disabled={editingConfig}
                >
                  <option value="google">Google OAuth</option>
                  <option value="microsoft">Microsoft Azure AD</option>
                  <option value="okta">Okta</option>
                  <option value="saml">SAML 2.0</option>
                </select>
                {editingConfig && <small>Provider cannot be changed</small>}
              </div>

              {renderProviderFields()}

              <div className="form-group">
                <label>Allowed Email Domains (comma-separated)</label>
                <input
                  type="text"
                  value={formData.allowed_domains}
                  onChange={(e) => setFormData({ ...formData, allowed_domains: e.target.value })}
                  placeholder="example.com, company.com"
                />
                <small>Leave blank to allow all domains</small>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.auto_provision_users}
                    onChange={(e) =>
                      setFormData({ ...formData, auto_provision_users: e.target.checked })
                    }
                  />
                  Auto-provision users on first login
                </label>
              </div>

              {formData.auto_provision_users && (
                <div className="form-group">
                  <label>Default Team for New Users *</label>
                  <select
                    value={formData.default_team_id}
                    onChange={(e) => setFormData({ ...formData, default_team_id: e.target.value })}
                    required
                  >
                    <option value="">Select a team...</option>
                    {teams.map((team) => (
                      <option key={team.id} value={team.id}>
                        {team.name} ({team.role})
                      </option>
                    ))}
                  </select>
                  <small>New SSO users will be added to this team with its role permissions</small>
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={() => { setShowModal(false); resetForm(); }}>
                  Cancel
                </button>
                <button type="submit" className="submit-btn">
                  {editingConfig ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default SSOSettings
