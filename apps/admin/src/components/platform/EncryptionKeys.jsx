import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { RefreshIcon, PlusIcon, ViewIcon, TrashIcon } from '../common'
import './Platform.css'

const EncryptionKeys = () => {
  const [keys, setKeys] = useState([])
  const [organizations, setOrganizations] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedOrg, setSelectedOrg] = useState('')
  const [selectedPurpose, setSelectedPurpose] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [showRotateModal, setShowRotateModal] = useState(false)
  const [selectedKey, setSelectedKey] = useState(null)
  const [isOperating, setIsOperating] = useState(false)
  const [showReencryptModal, setShowReencryptModal] = useState(false)
  const [reencryptStatus, setReencryptStatus] = useState(null)

  // Generate key form state
  const [generateForm, setGenerateForm] = useState({
    organization_id: '',
    purpose: 'sso'
  })

  // Rotate key form state
  const [rotateForm, setRotateForm] = useState({
    re_encrypt_data: false
  })

  const loadKeys = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (selectedOrg) params.append('organization_id', selectedOrg)
      if (selectedPurpose) params.append('purpose', selectedPurpose)
      if (includeInactive) params.append('include_inactive', 'true')

      const response = await fetch(`/api/admin/encryption-keys/?${params}`, {
        credentials: 'include'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to load encryption keys')
      }

      const data = await response.json()
      setKeys(data)
    } catch (err) {
      console.error('Failed to load encryption keys:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [selectedOrg, selectedPurpose, includeInactive])

  const loadOrganizations = useCallback(async () => {
    try {
      const response = await fetch('/api/platform/organizations?limit=1000', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setOrganizations(data.organizations || [])
      }
    } catch (err) {
      console.error('Failed to load organizations:', err)
    }
  }, [])

  useEffect(() => {
    loadKeys()
    loadOrganizations()
  }, [loadKeys, loadOrganizations])

  const handleGenerateKey = async () => {
    if (!generateForm.organization_id) {
      alert('Please select an organization')
      return
    }

    setIsOperating(true)
    try {
      const response = await fetch('/api/admin/encryption-keys/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(generateForm)
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to generate key')
      }

      setShowGenerateModal(false)
      setGenerateForm({ organization_id: '', purpose: 'sso' })
      loadKeys()
      alert('Encryption key generated successfully')
    } catch (err) {
      alert(err.message)
    } finally {
      setIsOperating(false)
    }
  }

  const handleRotateKey = async () => {
    if (!selectedKey) return

    setIsOperating(true)
    try {
      const response = await fetch(`/api/admin/encryption-keys/${selectedKey.id}/rotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(rotateForm)
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to rotate key')
      }

      setShowRotateModal(false)
      setSelectedKey(null)
      setRotateForm({ re_encrypt_data: false })
      loadKeys()
      alert('Encryption key rotated successfully')
    } catch (err) {
      alert(err.message)
    } finally {
      setIsOperating(false)
    }
  }

  const handleDeactivateKey = async (keyId) => {
    if (!confirm('Are you sure you want to deactivate this key? This action cannot be undone.')) {
      return
    }

    try {
      const response = await fetch(`/api/admin/encryption-keys/${keyId}`, {
        method: 'DELETE',
        credentials: 'include'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to deactivate key')
      }

      loadKeys()
      alert('Encryption key deactivated successfully')
    } catch (err) {
      alert(err.message)
    }
  }

  const checkReencryptionStatus = async (orgId, keyVersion) => {
    try {
      const response = await fetch(
        `/api/admin/encryption-keys/reencryption/status/${orgId}?key_version=${keyVersion}`,
        { credentials: 'include' }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to check status')
      }

      const status = await response.json()
      setReencryptStatus(status)
      setShowReencryptModal(true)
    } catch (err) {
      alert(err.message)
    }
  }

  const handleReencrypt = async () => {
    if (!reencryptStatus) return

    if (!confirm(
      `This will re-encrypt ${reencryptStatus.total_remaining} records. This may take some time. Continue?`
    )) {
      return
    }

    setIsOperating(true)
    try {
      const response = await fetch(
        `/api/admin/encryption-keys/reencryption/run/${reencryptStatus.organization_id}?old_key_version=${reencryptStatus.old_key_version}`,
        {
          method: 'POST',
          credentials: 'include'
        }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to run re-encryption')
      }

      const result = await response.json()
      alert(
        `Re-encryption completed!\n` +
        `Success: ${result.total_success}\n` +
        `Errors: ${result.total_errors}`
      )
      setShowReencryptModal(false)
      setReencryptStatus(null)
      loadKeys()
    } catch (err) {
      alert(err.message)
    } finally {
      setIsOperating(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const getStatusBadge = (key) => {
    if (!key.is_active) return <span className="badge badge-inactive">Inactive</span>
    if (key.is_primary) return <span className="badge badge-primary">Primary</span>
    return <span className="badge badge-active">Active</span>
  }

  const getPurposeIcon = (purpose) => {
    switch (purpose) {
      case 'sso': return '🔐'
      case 'data': return '💾'
      case 'backup': return '🔄'
      default: return '🔑'
    }
  }

  if (error && !keys.length) {
    return (
      <div className="platform-dashboard">
        <div className="platform-error">
          <h2>Access Denied</h2>
          <p>{error}</p>
          <p className="text-muted">Platform Administrator access required</p>
        </div>
      </div>
    )
  }

  return (
    <div className="platform-dashboard">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="platform-container"
      >
        {/* Header */}
        <div className="platform-header">
          <div>
            <h1>Encryption Key Management</h1>
            <p className="text-muted">
              Manage per-organization encryption keys for secure data storage
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowGenerateModal(true)}
          >
            <PlusIcon size={16} />
            Generate New Key
          </button>
        </div>

        {/* Filters */}
        <div className="filters-section">
          <div className="filter-group">
            <label>Organization</label>
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="form-control"
            >
              <option value="">All Organizations</option>
              {organizations.map(org => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Purpose</label>
            <select
              value={selectedPurpose}
              onChange={(e) => setSelectedPurpose(e.target.value)}
              className="form-control"
            >
              <option value="">All Purposes</option>
              <option value="sso">SSO</option>
              <option value="data">Data</option>
              <option value="backup">Backup</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Include Inactive Keys
            </label>
          </div>

          <button
            className="btn btn-secondary"
            onClick={loadKeys}
            disabled={isLoading}
            title="Refresh"
          >
            <RefreshIcon size={16} className={isLoading ? 'spinning' : ''} />
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {/* Keys Table */}
        {isLoading && !keys.length ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading encryption keys...</p>
          </div>
        ) : keys.length === 0 ? (
          <div className="empty-state">
            <p>No encryption keys found</p>
            <button
              className="btn btn-primary"
              onClick={() => setShowGenerateModal(true)}
            >
              Generate First Key
            </button>
          </div>
        ) : (
          <div className="keys-table-container">
            <table className="keys-table">
              <thead>
                <tr>
                  <th>Organization</th>
                  <th>Purpose</th>
                  <th>Key Name</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Last Used</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map(key => (
                  <tr key={key.id} className={!key.is_active ? 'inactive-row' : ''}>
                    <td>
                      <div className="org-cell">
                        {key.organization_name || 'Unknown'}
                      </div>
                    </td>
                    <td>
                      <div className="purpose-cell">
                        <span className="purpose-icon">{getPurposeIcon(key.key_purpose)}</span>
                        {key.key_purpose}
                      </div>
                    </td>
                    <td>
                      <code className="key-name">{key.key_name}</code>
                    </td>
                    <td>
                      <span className="version-badge">v{key.key_version}</span>
                    </td>
                    <td>{getStatusBadge(key)}</td>
                    <td className="date-cell">{formatDate(key.created_at)}</td>
                    <td className="date-cell">{formatDate(key.last_used_at)}</td>
                    <td>
                      <div className="action-buttons">
                        {key.is_active && key.is_primary && (
                          <button
                            className="btn-icon"
                            onClick={() => {
                              setSelectedKey(key)
                              setShowRotateModal(true)
                            }}
                            title="Rotate Key"
                            style={{ color: 'var(--accent-amber)' }}
                          >
                            <RefreshIcon size={16} />
                          </button>
                        )}
                        {key.is_active && !key.is_primary && (
                          <>
                            <button
                              className="btn-icon"
                              onClick={() => checkReencryptionStatus(key.organization_id, key.key_version)}
                              title="Check Status"
                              style={{ color: 'var(--accent-blue)' }}
                            >
                              <ViewIcon size={16} />
                            </button>
                            <button
                              className="btn-icon btn-danger"
                              onClick={() => handleDeactivateKey(key.id)}
                              title="Deactivate"
                            >
                              <TrashIcon size={16} />
                            </button>
                          </>
                        )}
                        {key.rotated_at && !key.is_active && (
                          <button
                            className="btn-icon"
                            onClick={() => checkReencryptionStatus(key.organization_id, key.key_version)}
                            title="Check Status"
                          >
                            <ViewIcon size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Stats Summary */}
        {keys.length > 0 && (
          <div className="stats-summary">
            <div className="stat-card">
              <div className="stat-value">{keys.filter(k => k.is_active).length}</div>
              <div className="stat-label">Active Keys</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{keys.filter(k => k.is_primary).length}</div>
              <div className="stat-label">Primary Keys</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{keys.filter(k => k.key_purpose === 'sso').length}</div>
              <div className="stat-label">SSO Keys</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{new Set(keys.map(k => k.organization_id)).size}</div>
              <div className="stat-label">Organizations</div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Generate Key Modal */}
      {showGenerateModal && (
        <div className="modal-overlay" onClick={() => setShowGenerateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Generate Encryption Key</h2>
              <button className="close-btn" onClick={() => setShowGenerateModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Organization *</label>
                <select
                  value={generateForm.organization_id}
                  onChange={(e) => setGenerateForm({ ...generateForm, organization_id: e.target.value })}
                  className="form-control"
                  required
                >
                  <option value="">Select Organization</option>
                  {organizations.map(org => (
                    <option key={org.id} value={org.id}>{org.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Purpose *</label>
                <select
                  value={generateForm.purpose}
                  onChange={(e) => setGenerateForm({ ...generateForm, purpose: e.target.value })}
                  className="form-control"
                >
                  <option value="sso">SSO (Single Sign-On)</option>
                  <option value="data">Data Encryption</option>
                  <option value="backup">Backup Encryption</option>
                </select>
              </div>
              <div className="info-box">
                <p><strong>Note:</strong> A new Fernet key will be generated and encrypted with the master key. If a primary key already exists for this organization and purpose, it will be marked as inactive.</p>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowGenerateModal(false)}
                disabled={isOperating}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleGenerateKey}
                disabled={isOperating || !generateForm.organization_id}
              >
                {isOperating ? 'Generating...' : 'Generate Key'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Re-encryption Status Modal */}
      {showReencryptModal && reencryptStatus && (
        <div className="modal-overlay" onClick={() => setShowReencryptModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Re-encryption Status</h2>
              <button className="close-btn" onClick={() => setShowReencryptModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="key-info">
                <p><strong>Organization ID:</strong> {reencryptStatus.organization_id}</p>
                <p><strong>Old Key Version:</strong> v{reencryptStatus.old_key_version}</p>
              </div>

              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-value">{reencryptStatus.sso_configs_remaining}</div>
                  <div className="stat-label">SSO Configs</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{reencryptStatus.integrations_remaining}</div>
                  <div className="stat-label">Integrations</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{reencryptStatus.total_remaining}</div>
                  <div className="stat-label">Total Records</div>
                </div>
              </div>

              {reencryptStatus.needs_reencryption ? (
                <div className="warning-box">
                  <p><strong>Action Required:</strong> {reencryptStatus.total_remaining} records still need to be re-encrypted with the new key.</p>
                  <p>You can either:</p>
                  <ul>
                    <li><strong>Lazy re-encryption:</strong> Records will be re-encrypted automatically when accessed (recommended)</li>
                    <li><strong>Bulk re-encryption:</strong> Re-encrypt all records now (may take time)</li>
                  </ul>
                </div>
              ) : (
                <div className="info-box">
                  <p><strong>✓ Complete:</strong> All records have been re-encrypted with the new key.</p>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowReencryptModal(false)}
                disabled={isOperating}
              >
                Close
              </button>
              {reencryptStatus.needs_reencryption && (
                <button
                  className="btn btn-primary"
                  onClick={handleReencrypt}
                  disabled={isOperating}
                >
                  {isOperating ? 'Re-encrypting...' : 'Run Bulk Re-encryption'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Rotate Key Modal */}
      {showRotateModal && selectedKey && (
        <div className="modal-overlay" onClick={() => setShowRotateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Rotate Encryption Key</h2>
              <button className="close-btn" onClick={() => setShowRotateModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="key-info">
                <p><strong>Organization:</strong> {selectedKey.organization_name}</p>
                <p><strong>Purpose:</strong> {selectedKey.key_purpose}</p>
                <p><strong>Current Version:</strong> v{selectedKey.key_version}</p>
              </div>
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={rotateForm.re_encrypt_data}
                    onChange={(e) => setRotateForm({ ...rotateForm, re_encrypt_data: e.target.checked })}
                  />
                  Re-encrypt existing data with new key
                </label>
                <p className="help-text">
                  (Currently not implemented - data will remain encrypted with old key)
                </p>
              </div>
              <div className="warning-box">
                <p><strong>Warning:</strong> This will create a new key and mark the current key as rotated. Make sure to test thoroughly after rotation.</p>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowRotateModal(false)}
                disabled={isOperating}
              >
                Cancel
              </button>
              <button
                className="btn btn-warning"
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

export default EncryptionKeys
