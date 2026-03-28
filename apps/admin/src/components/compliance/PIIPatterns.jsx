import React, { useState, useEffect } from 'react'
import { complianceApi } from '../../services/api'
import './Compliance.css'

const PIIPatterns = () => {
  const [patterns, setPatterns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editingPattern, setEditingPattern] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    pattern_regex: '',
    category: 'contact',
    sensitivity: 'medium',
    mask_char: '*',
    mask_style: 'partial'
  })

  useEffect(() => {
    loadPatterns()
  }, [])

  const loadPatterns = async () => {
    try {
      setLoading(true)
      const response = await complianceApi.getPiiPatterns(true)
      setPatterns(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load PII patterns')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingPattern(null)
    setFormData({
      name: '',
      pattern_regex: '',
      category: 'contact',
      sensitivity: 'medium',
      mask_char: '*',
      mask_style: 'partial'
    })
    setShowModal(true)
  }

  const handleEdit = (pattern) => {
    setEditingPattern(pattern)
    setFormData({
      name: pattern.name,
      pattern_regex: pattern.pattern_regex,
      category: pattern.category,
      sensitivity: pattern.sensitivity,
      mask_char: pattern.mask_char,
      mask_style: pattern.mask_style
    })
    setShowModal(true)
  }

  const handleDelete = async (pattern) => {
    if (!window.confirm(`Delete pattern "${pattern.name}"?`)) return
    
    try {
      await complianceApi.deletePiiPattern(pattern.id)
      loadPatterns()
    } catch (err) {
      setError('Failed to delete pattern')
      console.error(err)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingPattern) {
        await complianceApi.updatePiiPattern(editingPattern.id, formData)
      } else {
        await complianceApi.createPiiPattern(formData)
      }
      setShowModal(false)
      loadPatterns()
    } catch (err) {
      setError('Failed to save pattern')
      console.error(err)
    }
  }

  const handleToggleActive = async (pattern) => {
    try {
      await complianceApi.updatePiiPattern(pattern.id, { is_active: !pattern.is_active })
      loadPatterns()
    } catch (err) {
      setError('Failed to update pattern')
      console.error(err)
    }
  }

  const categories = ['contact', 'financial', 'government_id', 'personal', 'technical', 'custom']
  const sensitivities = ['low', 'medium', 'high']
  const maskStyles = ['partial', 'full', 'hash']

  if (loading) {
    return <div className="compliance-loading">Loading PII patterns...</div>
  }

  return (
    <div className="pii-patterns">
      <div className="compliance-header">
        <h2>PII Detection Patterns</h2>
        <button className="create-btn" onClick={handleCreate}>
          + Add Pattern
        </button>
      </div>

      {error && <div className="compliance-error">{error}</div>}

      <div className="patterns-table-container">
        <table className="patterns-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Sensitivity</th>
              <th>Mask Style</th>
              <th>Type</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {patterns.map(pattern => (
              <tr key={pattern.id} className={!pattern.is_active ? 'inactive' : ''}>
                <td>
                  <div className="pattern-name">{pattern.name}</div>
                  <div className="pattern-regex">{pattern.pattern_regex}</div>
                </td>
                <td>
                  <span className={`category-badge ${pattern.category}`}>
                    {pattern.category}
                  </span>
                </td>
                <td>
                  <span className={`sensitivity-badge ${pattern.sensitivity}`}>
                    {pattern.sensitivity}
                  </span>
                </td>
                <td>{pattern.mask_style}</td>
                <td>
                  {pattern.is_system_pattern ? (
                    <span className="system-badge">System</span>
                  ) : (
                    <span className="custom-badge">Custom</span>
                  )}
                </td>
                <td>
                  <button 
                    className={`status-toggle ${pattern.is_active ? 'active' : 'inactive'}`}
                    onClick={() => handleToggleActive(pattern)}
                    disabled={!pattern.can_edit}
                  >
                    {pattern.is_active ? 'Active' : 'Inactive'}
                  </button>
                </td>
                <td className="actions">
                  {pattern.can_edit && (
                    <button className="edit-btn" onClick={() => handleEdit(pattern)}>
                      Edit
                    </button>
                  )}
                  {pattern.can_delete && (
                    <button className="delete-btn" onClick={() => handleDelete(pattern)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>{editingPattern ? 'Edit Pattern' : 'Create Pattern'}</h3>
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
                <label>Regex Pattern</label>
                <input
                  type="text"
                  value={formData.pattern_regex}
                  onChange={(e) => setFormData({ ...formData, pattern_regex: e.target.value })}
                  required
                  placeholder="e.g., \b\d{3}-\d{2}-\d{4}\b"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Sensitivity</label>
                  <select
                    value={formData.sensitivity}
                    onChange={(e) => setFormData({ ...formData, sensitivity: e.target.value })}
                  >
                    {sensitivities.map(sens => (
                      <option key={sens} value={sens}>{sens}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Mask Character</label>
                  <input
                    type="text"
                    maxLength={1}
                    value={formData.mask_char}
                    onChange={(e) => setFormData({ ...formData, mask_char: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Mask Style</label>
                  <select
                    value={formData.mask_style}
                    onChange={(e) => setFormData({ ...formData, mask_style: e.target.value })}
                  >
                    {maskStyles.map(style => (
                      <option key={style} value={style}>{style}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="primary">
                  {editingPattern ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default PIIPatterns
