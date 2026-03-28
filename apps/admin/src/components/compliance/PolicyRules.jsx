import React, { useState, useEffect } from 'react'
import { complianceApi } from '../../services/api'
import './Compliance.css'

const PolicyRules = () => {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'data_protection',
    rule_config: {},
    priority: 50
  })
  const [configJson, setConfigJson] = useState('{}')

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      setLoading(true)
      const response = await complianceApi.getPolicies(true)
      setRules(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load policy rules')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingRule(null)
    setFormData({
      name: '',
      description: '',
      rule_type: 'data_protection',
      rule_config: {},
      priority: 50
    })
    setConfigJson('{}')
    setShowModal(true)
  }

  const handleEdit = (rule) => {
    setEditingRule(rule)
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      rule_config: rule.rule_config,
      priority: rule.priority
    })
    setConfigJson(JSON.stringify(rule.rule_config, null, 2))
    setShowModal(true)
  }

  const handleDelete = async (rule) => {
    if (!window.confirm(`Delete policy "${rule.name}"?`)) return
    
    try {
      await complianceApi.deletePolicy(rule.id)
      loadRules()
    } catch (err) {
      setError('Failed to delete policy')
      console.error(err)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const config = JSON.parse(configJson)
      const data = { ...formData, rule_config: config }
      
      if (editingRule) {
        await complianceApi.updatePolicy(editingRule.id, data)
      } else {
        await complianceApi.createPolicy(data)
      }
      setShowModal(false)
      loadRules()
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON in rule configuration')
      } else {
        setError('Failed to save policy')
      }
      console.error(err)
    }
  }

  const handleToggleActive = async (rule) => {
    try {
      await complianceApi.updatePolicy(rule.id, { is_active: !rule.is_active })
      loadRules()
    } catch (err) {
      setError('Failed to update policy')
      console.error(err)
    }
  }

  const ruleTypes = [
    { value: 'data_protection', label: 'Data Protection' },
    { value: 'access_control', label: 'Access Control' },
    { value: 'governance', label: 'Governance' },
    { value: 'rate_limit', label: 'Rate Limit' },
    { value: 'content_filter', label: 'Content Filter' },
    { value: 'workflow_validation', label: 'Workflow Validation' }
  ]

  if (loading) {
    return <div className="compliance-loading">Loading policy rules...</div>
  }

  return (
    <div className="policy-rules">
      <div className="compliance-header">
        <h2>Policy Rules</h2>
        <button className="create-btn" onClick={handleCreate}>
          + Add Policy
        </button>
      </div>

      {error && <div className="compliance-error">{error}</div>}

      <div className="rules-grid">
        {rules.map(rule => (
          <div key={rule.id} className={`rule-card ${!rule.is_active ? 'inactive' : ''}`}>
            <div className="rule-header">
              <h4>{rule.name}</h4>
              <div className="rule-badges">
                <span className={`type-badge ${rule.rule_type}`}>
                  {rule.rule_type.replace(/_/g, ' ')}
                </span>
                {rule.is_system_rule ? (
                  <span className="system-badge">System</span>
                ) : (
                  <span className="custom-badge">Custom</span>
                )}
              </div>
            </div>
            {rule.description && (
              <p className="rule-description">{rule.description}</p>
            )}
            <div className="rule-meta">
              <span className="priority">Priority: {rule.priority}</span>
              <button 
                className={`status-toggle ${rule.is_active ? 'active' : 'inactive'}`}
                onClick={() => handleToggleActive(rule)}
                disabled={!rule.can_edit}
              >
                {rule.is_active ? 'Active' : 'Inactive'}
              </button>
            </div>
            <div className="rule-config">
              <details>
                <summary>Configuration</summary>
                <pre>{JSON.stringify(rule.rule_config, null, 2)}</pre>
              </details>
            </div>
            <div className="rule-actions">
              {rule.can_edit && (
                <button className="edit-btn" onClick={() => handleEdit(rule)}>
                  Edit
                </button>
              )}
              {rule.can_delete && (
                <button className="delete-btn" onClick={() => handleDelete(rule)}>
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content wide">
            <h3>{editingRule ? 'Edit Policy' : 'Create Policy'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Rule Type</label>
                  <select
                    value={formData.rule_type}
                    onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  >
                    {ruleTypes.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Priority (1-100)</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Configuration (JSON)</label>
                <textarea
                  value={configJson}
                  onChange={(e) => setConfigJson(e.target.value)}
                  rows={8}
                  className="code-input"
                  placeholder='{"key": "value"}'
                />
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="primary">
                  {editingRule ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default PolicyRules
