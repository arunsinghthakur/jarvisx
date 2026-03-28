import React, { useState, useEffect } from 'react'
import { complianceApi } from '../../services/api'
import './Compliance.css'

const ComplianceDashboard = () => {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      const response = await complianceApi.getDashboard()
      setDashboard(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load compliance dashboard')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'COMPLIANT':
        return 'compliance-status-badge compliant'
      case 'VIOLATIONS_DETECTED':
        return 'compliance-status-badge violations'
      case 'REVIEW_RECOMMENDED':
        return 'compliance-status-badge review'
      default:
        return 'compliance-status-badge'
    }
  }

  if (loading) {
    return <div className="compliance-loading">Loading compliance dashboard...</div>
  }

  if (error) {
    return <div className="compliance-error">{error}</div>
  }

  return (
    <div className="compliance-dashboard">
      <div className="compliance-header">
        <h2>Compliance Dashboard</h2>
        <button className="refresh-btn" onClick={loadDashboard}>
          Refresh
        </button>
      </div>

      <div className="compliance-status-card">
        <div className="status-header">
          <h3>Overall Compliance Status</h3>
          <span className={getStatusBadgeClass(dashboard?.compliance_status)}>
            {dashboard?.compliance_status?.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      <div className="compliance-metrics-grid">
        <div className="metric-card">
          <div className="metric-value">{dashboard?.metrics?.audit_events_7d || 0}</div>
          <div className="metric-label">Audit Events (7 days)</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{dashboard?.metrics?.policy_violations_7d || 0}</div>
          <div className="metric-label">Policy Violations</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{dashboard?.metrics?.pii_exposure_events_7d || 0}</div>
          <div className="metric-label">PII Exposure Events</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{dashboard?.quick_stats?.daily_average_events || 0}</div>
          <div className="metric-label">Daily Avg Events</div>
        </div>
      </div>

      <div className="compliance-config-summary">
        <h3>Configuration Status</h3>
        <div className="config-items">
          <div className={`config-item ${dashboard?.configuration?.pii_detection_enabled ? 'enabled' : 'disabled'}`}>
            <span className="config-icon">{dashboard?.configuration?.pii_detection_enabled ? '✓' : '✗'}</span>
            <span className="config-label">PII Detection</span>
          </div>
          <div className={`config-item ${dashboard?.configuration?.audit_enabled ? 'enabled' : 'disabled'}`}>
            <span className="config-icon">{dashboard?.configuration?.audit_enabled ? '✓' : '✗'}</span>
            <span className="config-label">Audit Logging</span>
          </div>
          <div className={`config-item ${dashboard?.configuration?.policy_enforcement_enabled ? 'enabled' : 'disabled'}`}>
            <span className="config-icon">{dashboard?.configuration?.policy_enforcement_enabled ? '✓' : '✗'}</span>
            <span className="config-label">Policy Enforcement</span>
          </div>
          <div className="config-item">
            <span className="config-value">{dashboard?.configuration?.retention_days} days</span>
            <span className="config-label">Data Retention</span>
          </div>
        </div>
      </div>

      <div className="compliance-custom-resources">
        <h3>Custom Resources</h3>
        <div className="resource-counts">
          <div className="resource-count">
            <span className="count">{dashboard?.metrics?.custom_pii_patterns || 0}</span>
            <span className="label">Custom PII Patterns</span>
          </div>
          <div className="resource-count">
            <span className="count">{dashboard?.metrics?.custom_policy_rules || 0}</span>
            <span className="label">Custom Policy Rules</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ComplianceDashboard
