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

const SlackSettings = ({ currentOrganization }) => {
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
      const response = await integrationsApi.getAll(currentOrganization.id, 'slack')
      setIntegrations(response.data.integrations || [])
    } catch (err) {
      console.error('Failed to load Slack integrations:', err)
      setError('Failed to load Slack configurations')
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
    if (!window.confirm(`Delete Slack configuration "${integration.name}"?`)) return
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
        integration_type: 'slack',
        is_default: data.is_default,
        is_active: data.is_active,
        config: {
          default_channel: data.default_channel,
          bot_name: data.bot_name,
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
        <span>Loading Slack configurations...</span>
      </div>
    )
  }

  return (
    <div>
      <div className="integration-settings-header">
        <h3>Slack Settings</h3>
        <button className="btn btn-primary" onClick={handleCreate}>
          <PlusIcon /> Add Slack Config
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
              <path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z" />
              <path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z" />
              <path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5z" />
              <path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z" />
              <path d="M14 14.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5z" />
              <path d="M15.5 19H14v1.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5-.67-1.5-1.5-1.5z" />
              <path d="M10 9.5C10 8.67 9.33 8 8.5 8h-5C2.67 8 2 8.67 2 9.5S2.67 11 3.5 11h5c.83 0 1.5-.67 1.5-1.5z" />
              <path d="M8.5 5H10V3.5C10 2.67 9.33 2 8.5 2S7 2.67 7 3.5 7.67 5 8.5 5z" />
            </svg>
          </div>
          <h4>No Slack Configuration</h4>
          <p>Add a Slack webhook to enable notifications from your workflows.</p>
          <button className="btn btn-primary" onClick={handleCreate}>
            <PlusIcon /> Add Slack Config
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
                <span className="integration-type-badge slack">Slack</span>
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
                  <span className="integration-detail-label">Default Channel</span>
                  <span className="integration-detail-value">{integration.config?.default_channel || '-'}</span>
                </div>
                <div className="integration-detail">
                  <span className="integration-detail-label">Bot Name</span>
                  <span className="integration-detail-value">{integration.config?.bot_name || 'JarvisX'}</span>
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
        <SlackConfigModal
          integration={editingIntegration}
          onClose={handleModalClose}
          onSave={handleModalSave}
        />
      )}
    </div>
  )
}

const SlackConfigModal = ({ integration, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: integration?.name || '',
    webhook_url: integration?.has_sensitive_config ? '••••••••' : '',
    default_channel: integration?.config?.default_channel || '',
    bot_name: integration?.config?.bot_name || 'JarvisX',
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
          <h3>{integration ? 'Edit Slack Config' : 'Add Slack Config'}</h3>
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
                placeholder="e.g., Main Workspace"
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
                  placeholder="https://hooks.slack.com/services/..."
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
                Get this from Slack App Settings → Incoming Webhooks
              </span>
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label>Default Channel</label>
                <input
                  type="text"
                  value={formData.default_channel}
                  onChange={(e) => handleChange('default_channel', e.target.value)}
                  placeholder="#general"
                />
              </div>
              <div className="form-group">
                <label>Bot Name</label>
                <input
                  type="text"
                  value={formData.bot_name}
                  onChange={(e) => handleChange('bot_name', e.target.value)}
                  placeholder="JarvisX"
                />
              </div>
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

export default SlackSettings
