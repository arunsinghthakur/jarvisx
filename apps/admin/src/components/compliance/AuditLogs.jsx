import React, { useState, useEffect } from 'react'
import { complianceApi } from '../../services/api'
import './Compliance.css'

const AuditLogs = () => {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    event_type: '',
    event_category: '',
    days_back: 7,
    limit: 50,
    offset: 0
  })
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    loadLogs()
  }, [filters])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const response = await complianceApi.getAuditLogs(filters)
      setLogs(response.data.logs)
      setTotal(response.data.total)
      setError(null)
    } catch (err) {
      setError('Failed to load audit logs')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value, offset: 0 }))
  }

  const handleExport = async () => {
    try {
      setExporting(true)
      const response = await complianceApi.exportAuditLogs(filters.days_back)
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-report-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('Failed to export audit logs')
      console.error(err)
    } finally {
      setExporting(false)
    }
  }

  const handleNextPage = () => {
    setFilters(prev => ({ ...prev, offset: prev.offset + prev.limit }))
  }

  const handlePrevPage = () => {
    setFilters(prev => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }))
  }

  const eventCategories = [
    'authentication',
    'data_access',
    'data_modification',
    'agent_interaction',
    'workflow_execution',
    'admin_action',
    'policy_violation',
    'system'
  ]

  const eventTypes = [
    'login',
    'logout',
    'login_failed',
    'read',
    'create',
    'update',
    'delete',
    'export',
    'agent_call',
    'agent_response',
    'workflow_start',
    'workflow_complete',
    'workflow_failed',
    'config_change',
    'policy_evaluated',
    'policy_blocked',
    'pii_detected'
  ]

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className="audit-logs">
      <div className="compliance-header">
        <h2>Audit Logs</h2>
        <button 
          className="export-btn" 
          onClick={handleExport}
          disabled={exporting}
        >
          {exporting ? 'Exporting...' : 'Export Report'}
        </button>
      </div>

      {error && <div className="compliance-error">{error}</div>}

      <div className="filters-bar">
        <div className="filter-group">
          <label>Event Category</label>
          <select
            value={filters.event_category}
            onChange={(e) => handleFilterChange('event_category', e.target.value)}
          >
            <option value="">All Categories</option>
            {eventCategories.map(cat => (
              <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Event Type</label>
          <select
            value={filters.event_type}
            onChange={(e) => handleFilterChange('event_type', e.target.value)}
          >
            <option value="">All Types</option>
            {eventTypes.map(type => (
              <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Time Range</label>
          <select
            value={filters.days_back}
            onChange={(e) => handleFilterChange('days_back', parseInt(e.target.value))}
          >
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      <div className="logs-summary">
        Showing {logs.length} of {total} events
      </div>

      {loading ? (
        <div className="compliance-loading">Loading logs...</div>
      ) : (
        <>
          <div className="logs-table-container">
            <table className="logs-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Category</th>
                  <th>Type</th>
                  <th>User</th>
                  <th>Resource</th>
                  <th>Outcome</th>
                  <th>PII</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} className={log.outcome === 'blocked' ? 'blocked' : ''}>
                    <td className="timestamp">{formatTimestamp(log.created_at)}</td>
                    <td>
                      <span className={`category-badge ${log.event_category}`}>
                        {log.event_category?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{log.event_type?.replace(/_/g, ' ')}</td>
                    <td className="user-id">{log.user_id || '-'}</td>
                    <td className="resource">
                      {log.resource_type ? (
                        <span>{log.resource_type}/{log.resource_id?.substring(0, 8)}</span>
                      ) : log.agent_id ? (
                        <span>agent/{log.agent_id}</span>
                      ) : '-'}
                    </td>
                    <td>
                      <span className={`outcome-badge ${log.outcome}`}>
                        {log.outcome || '-'}
                      </span>
                    </td>
                    <td>
                      {log.pii_detected ? (
                        <span className="pii-badge">Yes</span>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button 
              onClick={handlePrevPage} 
              disabled={filters.offset === 0}
            >
              Previous
            </button>
            <span className="page-info">
              Page {Math.floor(filters.offset / filters.limit) + 1} of {Math.ceil(total / filters.limit)}
            </span>
            <button 
              onClick={handleNextPage}
              disabled={filters.offset + filters.limit >= total}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default AuditLogs
