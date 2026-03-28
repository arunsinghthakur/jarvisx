import React, { useState, useEffect, useCallback } from 'react'
import { encryptionApi } from '../../services'
import './SSOSettings.css'

const EncryptionSettings = ({ currentOrganization }) => {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showRotateModal, setShowRotateModal] = useState(false)
  const [selectedKey, setSelectedKey] = useState(null)
  const [isOperating, setIsOperating] = useState(false)
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [generatePurpose, setGeneratePurpose] = useState('sso')

  const loadKeys = useCallback(async () => {
    if (!currentOrganization?.id) return

    setLoading(true)
    setError(null)
    try {
      const response = await encryptionApi.getKeys(currentOrganization.id)
      setKeys(response.data || [])
    } catch (err) {
      console.error('Failed to load encryption keys:', err)
      setError(err.response?.data?.detail || 'Failed to load encryption keys')
    } finally {
      setLoading(false)
    }
  }, [currentOrganization])

  useEffect(() => {
    loadKeys()
  }, [loadKeys])

  const handleGenerateKey = async () => {
    setIsOperating(true)
    try {
      await encryptionApi.generateKey(currentOrganization.id, generatePurpose)
      setShowGenerateModal(false)
      setGeneratePurpose('sso')
      loadKeys()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to generate key')
    } finally {
      setIsOperating(false)
    }
  }

  const handleRotateKey = async () => {
    if (!selectedKey) return

    setIsOperating(true)
    try {
      await encryptionApi.rotateKey(selectedKey.id)
      setShowRotateModal(false)
      setSelectedKey(null)
      loadKeys()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to rotate key')
    } finally {
      setIsOperating(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const getStatusBadge = (key) => {
    if (!key.is_active) return <span className="sso-badge sso-badge-inactive">Inactive</span>
    if (key.is_primary) return <span className="sso-badge sso-badge-enabled">Primary</span>
    return <span className="sso-badge sso-badge-disabled">Active</span>
  }

  const getPurposeLabel = (purpose) => {
    switch (purpose) {
      case 'sso': return 'SSO Credentials'
      case 'data': return 'Data Encryption'
      case 'backup': return 'Backup Encryption'
      default: return purpose
    }
  }

  if (loading) {
    return (
      <div className="sso-loading">
        <div className="sso-spinner"></div>
        <p>Loading encryption keys...</p>
      </div>
    )
  }

  return (
    <div className="sso-settings">
      <div className="sso-header">
        <div className="sso-header-content">
          <h3>Encryption Keys</h3>
          <p>Manage encryption keys used to protect sensitive data like SSO credentials and integration secrets.</p>
        </div>
        <button
          className="sso-add-btn"
          onClick={() => setShowGenerateModal(true)}
        >
          <span>+</span> Generate New Key
        </button>
      </div>

      {error && (
        <div className="sso-error">
          <span>Error: {error}</span>
        </div>
      )}

      <div className="sso-info-banner">
        <div className="sso-info-icon">🔐</div>
        <div className="sso-info-text">
          <strong>About Encryption Keys</strong>
          <p>
            Encryption keys protect your sensitive credentials. Each organization has its own keys, 
            isolated from others. Rotating keys creates a new key while keeping the old one active 
            for decryption until all data is re-encrypted.
          </p>
        </div>
      </div>

      {keys.length === 0 ? (
        <div className="sso-empty">
          <div className="sso-empty-icon">🔑</div>
          <h4>No Encryption Keys</h4>
          <p>Generate your first encryption key to secure sensitive data.</p>
          <button
            className="sso-add-btn"
            onClick={() => setShowGenerateModal(true)}
          >
            Generate Key
          </button>
        </div>
      ) : (
        <div className="sso-list">
          {keys.map((key) => (
            <div key={key.id} className={`sso-card ${!key.is_active ? 'sso-card-inactive' : ''}`}>
              <div className="sso-card-header">
                <div className="sso-card-title">
                  <span className="sso-provider-icon">🔑</span>
                  <div>
                    <h4>{getPurposeLabel(key.key_purpose)}</h4>
                    <span className="sso-card-subtitle">Version {key.key_version}</span>
                  </div>
                </div>
                <div className="sso-card-status">
                  {getStatusBadge(key)}
                </div>
              </div>

              <div className="sso-card-details">
                <div className="sso-detail-row">
                  <span className="sso-detail-label">Key ID</span>
                  <span className="sso-detail-value">
                    <code>{key.id.substring(0, 8)}...</code>
                  </span>
                </div>
                <div className="sso-detail-row">
                  <span className="sso-detail-label">Created</span>
                  <span className="sso-detail-value">{formatDate(key.created_at)}</span>
                </div>
                <div className="sso-detail-row">
                  <span className="sso-detail-label">Last Used</span>
                  <span className="sso-detail-value">{formatDate(key.last_used_at)}</span>
                </div>
                {key.rotated_at && (
                  <div className="sso-detail-row">
                    <span className="sso-detail-label">Rotated</span>
                    <span className="sso-detail-value">{formatDate(key.rotated_at)}</span>
                  </div>
                )}
              </div>

              <div className="sso-card-actions">
                {key.is_active && key.is_primary && (
                  <button
                    className="sso-action-btn sso-action-edit"
                    onClick={() => {
                      setSelectedKey(key)
                      setShowRotateModal(true)
                    }}
                  >
                    🔄 Rotate Key
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generate Key Modal */}
      {showGenerateModal && (
        <div className="sso-modal-overlay" onClick={() => setShowGenerateModal(false)}>
          <div className="sso-modal" onClick={(e) => e.stopPropagation()}>
            <div className="sso-modal-header">
              <h3>Generate Encryption Key</h3>
              <button className="sso-modal-close" onClick={() => setShowGenerateModal(false)}>×</button>
            </div>
            <div className="sso-modal-body">
              <div className="sso-form-group">
                <label>Purpose</label>
                <select
                  value={generatePurpose}
                  onChange={(e) => setGeneratePurpose(e.target.value)}
                  className="sso-input"
                >
                  <option value="sso">SSO Credentials</option>
                  <option value="data">Data Encryption</option>
                  <option value="backup">Backup Encryption</option>
                </select>
                <span className="sso-help-text">
                  Select what this key will be used to encrypt
                </span>
              </div>

              <div className="sso-info-box">
                <p>
                  <strong>Note:</strong> If a primary key already exists for this purpose, 
                  the new key will become the primary and the old key will remain active 
                  for decryption until data is re-encrypted.
                </p>
              </div>
            </div>
            <div className="sso-modal-footer">
              <button
                className="sso-btn sso-btn-secondary"
                onClick={() => setShowGenerateModal(false)}
                disabled={isOperating}
              >
                Cancel
              </button>
              <button
                className="sso-btn sso-btn-primary"
                onClick={handleGenerateKey}
                disabled={isOperating}
              >
                {isOperating ? 'Generating...' : 'Generate Key'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rotate Key Modal */}
      {showRotateModal && selectedKey && (
        <div className="sso-modal-overlay" onClick={() => setShowRotateModal(false)}>
          <div className="sso-modal" onClick={(e) => e.stopPropagation()}>
            <div className="sso-modal-header">
              <h3>Rotate Encryption Key</h3>
              <button className="sso-modal-close" onClick={() => setShowRotateModal(false)}>×</button>
            </div>
            <div className="sso-modal-body">
              <div className="sso-key-info">
                <p><strong>Purpose:</strong> {getPurposeLabel(selectedKey.key_purpose)}</p>
                <p><strong>Current Version:</strong> v{selectedKey.key_version}</p>
              </div>

              <div className="sso-warning-box">
                <p>
                  <strong>⚠️ Warning:</strong> This will create a new encryption key (v{selectedKey.key_version + 1}) 
                  and mark it as the primary key. The current key will remain active for decryption 
                  until all data is re-encrypted with the new key.
                </p>
              </div>

              <div className="sso-info-box">
                <p>
                  <strong>After rotation:</strong> Data encrypted with the old key will be automatically 
                  re-encrypted with the new key when accessed (lazy re-encryption).
                </p>
              </div>
            </div>
            <div className="sso-modal-footer">
              <button
                className="sso-btn sso-btn-secondary"
                onClick={() => setShowRotateModal(false)}
                disabled={isOperating}
              >
                Cancel
              </button>
              <button
                className="sso-btn sso-btn-warning"
                onClick={handleRotateKey}
                disabled={isOperating}
              >
                {isOperating ? 'Rotating...' : 'Rotate Key'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EncryptionSettings
