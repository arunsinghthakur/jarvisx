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

const EmailSettings = ({ currentOrganization }) => {
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
      const response = await integrationsApi.getAll(currentOrganization.id, 'email')
      setIntegrations(response.data.integrations || [])
    } catch (err) {
      console.error('Failed to load email integrations:', err)
      setError('Failed to load email configurations')
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
    if (!window.confirm(`Delete email configuration "${integration.name}"?`)) return
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
        integration_type: 'email',
        is_default: data.is_default,
        is_active: data.is_active,
        config: {
          smtp_host: data.smtp_host,
          smtp_port: parseInt(data.smtp_port, 10) || 587,
          smtp_user: data.smtp_user,
          from_email: data.from_email,
          from_name: data.from_name,
          use_tls: data.use_tls,
        }
      }
      if (data.smtp_password && data.smtp_password !== '••••••••') {
        payload.config.smtp_password = data.smtp_password
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
        <span>Loading email configurations...</span>
      </div>
    )
  }

  return (
    <div>
      <div className="integration-settings-header">
        <h3>Email / SMTP Settings</h3>
        <button className="btn btn-primary" onClick={handleCreate}>
          <PlusIcon /> Add Email Config
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
              <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h4>No Email Configuration</h4>
          <p>Add SMTP settings to enable email sending from your workflows.</p>
          <button className="btn btn-primary" onClick={handleCreate}>
            <PlusIcon /> Add Email Config
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
                <span className="integration-type-badge email">SMTP</span>
                <div className="integration-card-actions">
                  <button
                    className="btn-icon"
                    onClick={() => handleTest(integration)}
                    disabled={testingId === integration.id}
                    title="Test connection"
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
                  <span className="integration-detail-label">SMTP Host</span>
                  <span className="integration-detail-value">{integration.config?.smtp_host || '-'}</span>
                </div>
                <div className="integration-detail">
                  <span className="integration-detail-label">Port</span>
                  <span className="integration-detail-value">{integration.config?.smtp_port || 587}</span>
                </div>
                <div className="integration-detail">
                  <span className="integration-detail-label">From Email</span>
                  <span className="integration-detail-value">{integration.config?.from_email || '-'}</span>
                </div>
                <div className="integration-detail">
                  <span className="integration-detail-label">TLS</span>
                  <span className="integration-detail-value">{integration.config?.use_tls ? 'Enabled' : 'Disabled'}</span>
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
        <EmailConfigModal
          integration={editingIntegration}
          onClose={handleModalClose}
          onSave={handleModalSave}
        />
      )}
    </div>
  )
}

const EmailConfigModal = ({ integration, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: integration?.name || '',
    smtp_host: integration?.config?.smtp_host || '',
    smtp_port: integration?.config?.smtp_port || 587,
    smtp_user: integration?.config?.smtp_user || '',
    smtp_password: integration?.has_sensitive_config ? '••••••••' : '',
    from_email: integration?.config?.from_email || '',
    from_name: integration?.config?.from_name || 'JarvisX',
    use_tls: integration?.config?.use_tls !== false,
    is_default: integration?.is_default || false,
    is_active: integration?.is_active !== false,
  })
  const [showPassword, setShowPassword] = useState(false)
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
          <h3>{integration ? 'Edit Email Config' : 'Add Email Config'}</h3>
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
                placeholder="e.g., Gmail SMTP"
                required
              />
            </div>

            <div className="form-group">
              <label>SMTP Host *</label>
              <input
                type="text"
                value={formData.smtp_host}
                onChange={(e) => handleChange('smtp_host', e.target.value)}
                placeholder="smtp.gmail.com"
                required
              />
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label>SMTP Port</label>
                <input
                  type="number"
                  value={formData.smtp_port}
                  onChange={(e) => handleChange('smtp_port', e.target.value)}
                  placeholder="587"
                />
              </div>
              <div className="form-group">
                <label>SMTP Username</label>
                <input
                  type="text"
                  value={formData.smtp_user}
                  onChange={(e) => handleChange('smtp_user', e.target.value)}
                  placeholder="your-email@gmail.com"
                />
              </div>
            </div>

            <div className="form-group">
              <label>SMTP Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.smtp_password}
                  onChange={(e) => handleChange('smtp_password', e.target.value)}
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  className="toggle-visibility"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              <span className="form-hint">For Gmail, use an App Password instead of your account password.</span>
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label>From Email *</label>
                <input
                  type="email"
                  value={formData.from_email}
                  onChange={(e) => handleChange('from_email', e.target.value)}
                  placeholder="noreply@yourcompany.com"
                  required
                />
              </div>
              <div className="form-group">
                <label>From Name</label>
                <input
                  type="text"
                  value={formData.from_name}
                  onChange={(e) => handleChange('from_name', e.target.value)}
                  placeholder="JarvisX"
                />
              </div>
            </div>

            <div className="form-row checkboxes">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.use_tls}
                  onChange={(e) => handleChange('use_tls', e.target.checked)}
                />
                Use TLS
              </label>
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

export default EmailSettings
