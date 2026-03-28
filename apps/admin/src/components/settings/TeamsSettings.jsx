import React, { useState, useEffect, useCallback } from 'react'
import { integrationsApi } from '../../services'
import {
  PlusIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  AlertCircleIcon,
  RefreshIcon,
  StarIcon,
} from '../common'

const TeamsSettings = ({ currentOrganization }) => {
  const [integrations, setIntegrations] = useState([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingIntegration, setEditingIntegration] = useState(null)
  const [testingId, setTestingId] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)

  const loadIntegrations = useCallback(async () => {
    if (!currentOrganization?.id) return
    setLoading(true)
    setError(null)
    try {
      const response = await integrationsApi.getAll(currentOrganization.id, 'teams')
      setIntegrations(response.data.integrations || [])
    } catch (err) {
      console.error('Failed to load Teams integrations:', err)
      setError('Failed to load Teams configurations')
    } finally {
      setLoading(false)
    }
  }, [currentOrganization])

  useEffect(() => {
    loadIntegrations()
  }, [loadIntegrations])

  const handleCreate = () => {
    setEditingIntegration(null)
    setShowModal(true)
  }

  const handleEdit = (integration) => {
    setEditingIntegration(integration)
    setShowModal(true)
  }

  const handleDelete = async (integration) => {
    if (!window.confirm(`Delete Teams configuration "${integration.name}"?`)) return
    try {
      await integrationsApi.delete(currentOrganization.id, integration.id)
      loadIntegrations()
    } catch (err) {
      console.error('Failed to delete integration:', err)
      setError('Failed to delete configuration')
    }
  }

  const handleSetDefault = async (integration) => {
    try {
      await integrationsApi.setDefault(currentOrganization.id, integration.id)
      loadIntegrations()
    } catch (err) {
      console.error('Failed to set default:', err)
      setError('Failed to set as default')
    }
  }

  const handleTest = async (integration) => {
    setTestingId(integration.id)
    setTestResult(null)
    try {
      const response = await integrationsApi.test(currentOrganization.id, integration.id)
      setTestResult({ id: integration.id, ...response.data })
    } catch (err) {
      setTestResult({ id: integration.id, success: false, message: err.message })
    } finally {
      setTestingId(null)
    }
  }

  const handleModalClose = () => {
    setShowModal(false)
    setEditingIntegration(null)
  }

  const handleModalSave = async (data) => {
    try {
      const payload = {
        name: data.name,
        integration_type: 'teams',
        is_default: data.is_default,
        is_active: data.is_active,
        config: {
          card_theme_color: data.card_theme_color,
        }
      }
      if (data.webhook_url && data.webhook_url !== '••••••••') {
        payload.config.webhook_url = data.webhook_url
      }

      if (editingIntegration) {
        await integrationsApi.update(currentOrganization.id, editingIntegration.id, payload)
      } else {
        await integrationsApi.create(currentOrganization.id, payload)
      }
      loadIntegrations()
      handleModalClose()
    } catch (err) {
      throw err
    }
  }

  if (loading) {
    return (
      <div className="integration-loading">
        <div className="loading-spinner" />
        <span>Loading Teams configurations...</span>
      </div>
    )
  }

  return (
    <div>
      <div className="integration-settings-header">
        <h3>Microsoft Teams Settings</h3>
        <button className="btn btn-primary" onClick={handleCreate}>
          <PlusIcon /> Add Teams Config
        </button>
      </div>

      {error && (
        <div className="integration-error-banner">
          <AlertCircleIcon />
          <span>{error}</span>
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      {integrations.length === 0 ? (
        <div className="integration-empty-state">
          <div className="integration-empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h4>No Teams Configuration</h4>
          <p>Add a Microsoft Teams webhook to enable notifications from your workflows.</p>
          <button className="btn btn-primary" onClick={handleCreate}>
            <PlusIcon /> Add Teams Config
          </button>
        </div>
      ) : (
        <div className="integrations-grid">
          {integrations.map((integration) => (
            <div
              key={integration.id}
              className={`integration-card ${integration.is_default ? 'default' : ''} ${!integration.is_active ? 'inactive' : ''}`}
            >
              {integration.is_default && (
                <div className="integration-default-badge">
                  <StarIcon /> Default
                </div>
              )}
              
              <div className="integration-card-header">
                <span className="integration-type-badge teams">Teams</span>
                <div className="integration-card-actions">
                  <button
                    className="btn-icon"
                    onClick={() => handleTest(integration)}
                    disabled={testingId === integration.id}
                    title="Test webhook"
                  >
                    <RefreshIcon className={testingId === integration.id ? 'spinning' : ''} />
                  </button>
                  <button className="btn-icon" onClick={() => handleEdit(integration)} title="Edit">
                    <EditIcon />
                  </button>
                  <button className="btn-icon danger" onClick={() => handleDelete(integration)} title="Delete">
                    <TrashIcon />
                  </button>
                </div>
              </div>

              <h4 className="integration-name">{integration.name}</h4>

              <div className="integration-details">
                <div className="integration-detail">
                  <span className="integration-detail-label">Webhook URL</span>
                  <span className="integration-detail-value sensitive">
                    {integration.has_sensitive_config ? '••••••••' : 'Not configured'}
                  </span>
                </div>
                <div className="integration-detail">
                  <span className="integration-detail-label">Theme Color</span>
                  <span className="integration-detail-value" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        width: '16px',
                        height: '16px',
                        borderRadius: '4px',
                        backgroundColor: `#${integration.config?.card_theme_color || '6366f1'}`,
                      }}
                    />
                    #{integration.config?.card_theme_color || '6366f1'}
                  </span>
                </div>
              </div>

              {testResult && testResult.id === integration.id && (
                <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                  {testResult.success ? <CheckIcon /> : <AlertCircleIcon />}
                  <span>{testResult.message}</span>
                </div>
              )}

              {integration.is_active && !integration.is_default && (
                <button className="btn-set-default" onClick={() => handleSetDefault(integration)}>
                  Set as Default
                </button>
              )}

              {!integration.is_active && (
                <div className="inactive-badge">Inactive</div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <TeamsConfigModal
          integration={editingIntegration}
          onClose={handleModalClose}
          onSave={handleModalSave}
        />
      )}
    </div>
  )
}

const TeamsConfigModal = ({ integration, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: integration?.name || '',
    webhook_url: integration?.has_sensitive_config ? '••••••••' : '',
    card_theme_color: integration?.config?.card_theme_color || '6366f1',
    is_default: integration?.is_default || false,
    is_active: integration?.is_active !== false,
  })
  const [showWebhook, setShowWebhook] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      await onSave(formData)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal integration-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{integration ? 'Edit Teams Config' : 'Add Teams Config'}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="form-error">
                <AlertCircleIcon />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label>Configuration Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="e.g., Engineering Team"
                required
              />
            </div>

            <div className="form-group">
              <label>Webhook URL *</label>
              <div className="password-input-wrapper">
                <input
                  type={showWebhook ? 'text' : 'password'}
                  value={formData.webhook_url}
                  onChange={(e) => handleChange('webhook_url', e.target.value)}
                  placeholder="https://outlook.office.com/webhook/..."
                  required={!integration}
                />
                <button
                  type="button"
                  className="toggle-visibility"
                  onClick={() => setShowWebhook(!showWebhook)}
                >
                  {showWebhook ? 'Hide' : 'Show'}
                </button>
              </div>
              <span className="form-hint">
                Get this from Teams Channel Settings → Connectors → Incoming Webhook
              </span>
            </div>

            <div className="form-group">
              <label>Card Theme Color</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="color"
                  value={`#${formData.card_theme_color}`}
                  onChange={(e) => handleChange('card_theme_color', e.target.value.slice(1))}
                  style={{ width: '48px', height: '38px', padding: '2px', cursor: 'pointer' }}
                />
                <input
                  type="text"
                  value={formData.card_theme_color}
                  onChange={(e) => handleChange('card_theme_color', e.target.value.replace('#', ''))}
                  placeholder="6366f1"
                  style={{ flex: 1 }}
                  maxLength={6}
                />
              </div>
              <span className="form-hint">
                Hex color code for the message card accent (without #)
              </span>
            </div>

            <div className="form-row checkboxes">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => handleChange('is_default', e.target.checked)}
                />
                Set as Default
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => handleChange('is_active', e.target.checked)}
                />
                Active
              </label>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (integration ? 'Update' : 'Create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default TeamsSettings
