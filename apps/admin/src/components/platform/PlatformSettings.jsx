import React, { useState, useEffect, useCallback } from 'react'
import { platformApi } from '../../services'
import './Platform.css'

const CATEGORY_LABELS = {
  tracing: 'Tracing & Observability',
  performance: 'Performance & Caching',
  auth: 'Authentication',
}

const ValueEditor = ({ setting, onSave }) => {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(setting.value)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      let parsed = value
      if (setting.value_type === 'int') parsed = parseInt(value, 10)
      else if (setting.value_type === 'float') parsed = parseFloat(value)
      else if (setting.value_type === 'bool') parsed = typeof value === 'boolean' ? value : value === 'true'
      await onSave(setting.category, setting.key, parsed)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <div className="setting-value-display" onClick={() => setEditing(true)}>
        {setting.value_type === 'bool' ? (
          <span className={`bool-badge ${setting.value ? 'on' : 'off'}`}>
            {String(setting.value)}
          </span>
        ) : (
          <span className="value-text">{String(setting.value)}</span>
        )}
        <span className="edit-hint">click to edit</span>
      </div>
    )
  }

  if (setting.value_type === 'bool') {
    return (
      <div className="setting-value-editor">
        <select value={String(value)} onChange={(e) => setValue(e.target.value)}>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
        <button className="btn-save-sm" onClick={handleSave} disabled={saving}>Save</button>
        <button className="btn-cancel-sm" onClick={() => { setEditing(false); setValue(setting.value) }}>Cancel</button>
      </div>
    )
  }

  return (
    <div className="setting-value-editor">
      <input
        type={setting.value_type === 'int' || setting.value_type === 'float' ? 'number' : 'text'}
        step={setting.value_type === 'float' ? '0.01' : undefined}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoFocus
      />
      <button className="btn-save-sm" onClick={handleSave} disabled={saving}>Save</button>
      <button className="btn-cancel-sm" onClick={() => { setEditing(false); setValue(setting.value) }}>Cancel</button>
    </div>
  )
}

const PlatformSettings = () => {
  const [settings, setSettings] = useState({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  const loadSettings = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await platformApi.getSettings()
      setSettings(res.data || {})
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { loadSettings() }, [loadSettings])

  const handleSave = async (category, key, value) => {
    try {
      await platformApi.updateSetting(category, key, value)
      setSuccessMsg(`Updated ${category}.${key}`)
      setTimeout(() => setSuccessMsg(null), 3000)
      loadSettings()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update setting')
    }
  }

  if (isLoading) {
    return <div className="platform-loading">Loading platform settings...</div>
  }

  return (
    <div className="platform-page">
      <div className="platform-header">
        <h1>Platform Settings</h1>
        <p className="platform-subtitle">Runtime-configurable operational settings. Changes take effect without service restarts.</p>
      </div>

      {error && <div className="platform-error">{error}</div>}
      {successMsg && <div className="platform-success">{successMsg}</div>}

      <div className="settings-categories">
        {Object.entries(settings).map(([category, items]) => (
          <div key={category} className="settings-category-card">
            <h2 className="category-title">{CATEGORY_LABELS[category] || category}</h2>
            <div className="settings-table">
              <div className="settings-table-header">
                <span>Setting</span>
                <span>Value</span>
                <span>Description</span>
              </div>
              {items.map((setting) => (
                <div key={setting.id} className="settings-row">
                  <div className="setting-key">
                    <code>{setting.key}</code>
                    <span className="setting-type">{setting.value_type}</span>
                  </div>
                  <div className="setting-value">
                    <ValueEditor setting={setting} onSave={handleSave} />
                  </div>
                  <div className="setting-description">
                    {setting.description || '-'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {Object.keys(settings).length === 0 && (
          <div className="empty-state">
            No platform settings found. Run the database migration to seed defaults.
          </div>
        )}
      </div>
    </div>
  )
}

export default PlatformSettings
