import React, { useState, useEffect } from 'react'
import { complianceApi } from '../../services/api'
import './Compliance.css'

const ComplianceSettings = () => {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await complianceApi.getConfig()
      setConfig(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load compliance configuration')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      await complianceApi.updateConfig(config)
      setSuccess('Configuration saved successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError('Failed to save configuration')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="compliance-loading">Loading configuration...</div>
  }

  return (
    <div className="compliance-settings">
      <div className="compliance-header">
        <h2>Compliance Settings</h2>
        <button 
          className="save-btn" 
          onClick={handleSave} 
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {error && <div className="compliance-error">{error}</div>}
      {success && <div className="compliance-success">{success}</div>}

      <div className="settings-section">
        <h3>PII Detection</h3>
        <div className="setting-group">
          <div className="setting-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={config?.pii_detection_enabled || false}
                onChange={(e) => handleChange('pii_detection_enabled', e.target.checked)}
              />
              <span className="toggle-text">Enable PII Detection</span>
            </label>
            <p className="setting-description">
              Automatically detect personally identifiable information in text
            </p>
          </div>

          <div className="setting-row">
            <label className="select-label">Sensitivity Level</label>
            <select
              value={config?.pii_sensitivity_level || 'medium'}
              onChange={(e) => handleChange('pii_sensitivity_level', e.target.value)}
            >
              <option value="low">Low - Detect only high-sensitivity PII</option>
              <option value="medium">Medium - Detect medium and high sensitivity</option>
              <option value="high">High - Detect all PII patterns</option>
            </select>
          </div>

          <div className="setting-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={config?.pii_mask_in_logs || false}
                onChange={(e) => handleChange('pii_mask_in_logs', e.target.checked)}
              />
              <span className="toggle-text">Mask PII in Audit Logs</span>
            </label>
            <p className="setting-description">
              Automatically mask detected PII before writing to audit logs
            </p>
          </div>

          <div className="setting-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={config?.pii_mask_in_responses || false}
                onChange={(e) => handleChange('pii_mask_in_responses', e.target.checked)}
              />
              <span className="toggle-text">Mask PII in Agent Responses</span>
            </label>
            <p className="setting-description">
              Mask PII in responses returned to users (may affect functionality)
            </p>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Audit Logging</h3>
        <div className="setting-group">
          <div className="setting-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={config?.audit_enabled || false}
                onChange={(e) => handleChange('audit_enabled', e.target.checked)}
              />
              <span className="toggle-text">Enable Audit Logging</span>
            </label>
            <p className="setting-description">
              Log all system activities for compliance and security monitoring
            </p>
          </div>

          <div className="setting-row">
            <label className="input-label">Data Retention (days)</label>
            <input
              type="number"
              min="1"
              max="365"
              value={config?.audit_retention_days || 90}
              onChange={(e) => handleChange('audit_retention_days', parseInt(e.target.value))}
            />
            <p className="setting-description">
              Automatically delete audit logs older than this many days
            </p>
          </div>

          <div className="setting-row">
            <label className="select-label">Log Level</label>
            <select
              value={config?.audit_log_level || 'standard'}
              onChange={(e) => handleChange('audit_log_level', e.target.value)}
            >
              <option value="minimal">Minimal - Critical events only</option>
              <option value="standard">Standard - All significant events</option>
              <option value="verbose">Verbose - All events with full details</option>
            </select>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Policy Enforcement</h3>
        <div className="setting-group">
          <div className="setting-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={config?.policy_enforcement_enabled || false}
                onChange={(e) => handleChange('policy_enforcement_enabled', e.target.checked)}
              />
              <span className="toggle-text">Enable Policy Enforcement</span>
            </label>
            <p className="setting-description">
              Enforce organizational policies and block non-compliant actions
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ComplianceSettings
