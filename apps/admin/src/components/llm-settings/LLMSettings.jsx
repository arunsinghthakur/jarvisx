import React, { useState, useEffect, useCallback } from 'react'
import { llmConfigsApi } from '../../services'
import {
  PlusIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  AlertCircleIcon,
  RefreshIcon,
  StarIcon,
} from '../common'
import { usePermissions } from '../../hooks'
import './LLMSettings.css'

const LLMSettings = ({ currentOrganization }) => {
  const { settings } = usePermissions()
  const llmPerms = settings.llmConfigs
  const [configs, setConfigs] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [testingConfig, setTestingConfig] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)

  const loadConfigs = useCallback(async () => {
    if (!currentOrganization?.id) return
    setLoading(true)
    setError(null)
    try {
      const [configsRes, providersRes] = await Promise.all([
        llmConfigsApi.getAll(currentOrganization.id),
        llmConfigsApi.getProviders(currentOrganization.id),
      ])
      setConfigs(configsRes.data.configs || [])
      setProviders(providersRes.data.providers || [])
    } catch (err) {
      console.error('Failed to load LLM configs:', err)
      setError('Failed to load LLM configurations')
    } finally {
      setLoading(false)
    }
  }, [currentOrganization])

  useEffect(() => {
    loadConfigs()
  }, [loadConfigs])

  const handleCreate = () => {
    setEditingConfig(null)
    setShowModal(true)
  }

  const handleEdit = (config) => {
    setEditingConfig(config)
    setShowModal(true)
  }

  const handleDelete = async (config) => {
    if (!window.confirm(`Delete LLM configuration "${config.name}"?`)) return
    try {
      await llmConfigsApi.delete(currentOrganization.id, config.id)
      loadConfigs()
    } catch (err) {
      console.error('Failed to delete config:', err)
      setError('Failed to delete configuration')
    }
  }

  const handleSetDefault = async (config) => {
    try {
      await llmConfigsApi.setDefault(currentOrganization.id, config.id)
      loadConfigs()
    } catch (err) {
      console.error('Failed to set default:', err)
      setError('Failed to set as default')
    }
  }

  const handleTest = async (config) => {
    setTestingConfig(config.id)
    setTestResult(null)
    try {
      const res = await llmConfigsApi.test(currentOrganization.id, config.id)
      setTestResult({ configId: config.id, ...res.data })
    } catch (err) {
      setTestResult({ configId: config.id, success: false, message: err.message })
    } finally {
      setTestingConfig(null)
    }
  }

  const handleSave = async (formData) => {
    try {
      if (editingConfig) {
        await llmConfigsApi.update(currentOrganization.id, editingConfig.id, formData)
      } else {
        await llmConfigsApi.create(currentOrganization.id, formData)
      }
      setShowModal(false)
      loadConfigs()
    } catch (err) {
      throw err
    }
  }

  const getProviderInfo = (providerId) => {
    return providers.find(p => p.id === providerId) || { name: providerId }
  }

  const getProviderColor = (providerId) => {
    const colors = {
      openai: '#10a37f',
      anthropic: '#cc785c',
      azure_openai: '#0078d4',
      google_vertex: '#4285f4',
      litellm: '#8b5cf6',
      custom: '#6b7280',
    }
    return colors[providerId] || '#6b7280'
  }

  if (!currentOrganization) {
    return (
      <div className="llm-settings-container">
        <div className="llm-loading">
          <span>No organization selected</span>
        </div>
      </div>
    )
  }

  return (
    <div className="llm-settings-container">
      <div className="llm-settings-header">
        <div className="llm-settings-header-left">
          <h2>LLM Providers</h2>
          <p>Configure LLM providers for your organization's AI-powered agents</p>
        </div>
        <div className="llm-settings-header-right">
          {llmPerms.canCreate && (
            <button className="btn-primary" onClick={handleCreate}>
              <PlusIcon size={16} />
              Add LLM Config
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="llm-error-banner">
          <AlertCircleIcon size={16} />
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading ? (
        <div className="llm-loading">
          <div className="loading-spinner"></div>
          <span>Loading configurations...</span>
        </div>
      ) : configs.length === 0 ? (
        <div className="llm-empty-state">
          <div className="llm-empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
              <circle cx="7.5" cy="14.5" r="1.5"/>
              <circle cx="16.5" cy="14.5" r="1.5"/>
            </svg>
          </div>
          <h3>No LLM Configurations</h3>
          <p>Add your own LLM provider to power the AI agents with your API keys.</p>
          {llmPerms.canCreate && (
            <button className="btn-primary" onClick={handleCreate}>
              <PlusIcon size={16} />
              Add Your First LLM
            </button>
          )}
        </div>
      ) : (
        <div className="llm-configs-grid">
          {configs.map(config => (
            <div key={config.id} className={`llm-config-card ${config.is_default ? 'default' : ''} ${!config.is_active ? 'inactive' : ''}`}>
              {config.is_default && (
                <div className="default-badge">
                  <StarIcon size={12} />
                  Default
                </div>
              )}
              <div className="config-header">
                <div 
                  className="provider-badge"
                  style={{ backgroundColor: `${getProviderColor(config.provider)}20`, color: getProviderColor(config.provider) }}
                >
                  {getProviderInfo(config.provider).name}
                </div>
                <div className="config-actions">
                  <button 
                    className="btn-icon" 
                    onClick={() => handleTest(config)}
                    disabled={testingConfig === config.id}
                    title="Test connection"
                  >
                    {testingConfig === config.id ? (
                      <RefreshIcon size={14} className="spinning" />
                    ) : (
                      <RefreshIcon size={14} />
                    )}
                  </button>
                  {llmPerms.canEdit && (
                    <button className="btn-icon" onClick={() => handleEdit(config)} title="Edit">
                      <EditIcon size={14} />
                    </button>
                  )}
                  {llmPerms.canDelete && (
                    <button className="btn-icon danger" onClick={() => handleDelete(config)} title="Delete">
                      <TrashIcon size={14} />
                    </button>
                  )}
                </div>
              </div>
              <h3 className="config-name">{config.name}</h3>
              <div className="config-details">
                <div className="config-detail">
                  <span className="detail-label">Model</span>
                  <span className="detail-value">{config.model_name}</span>
                </div>
                <div className="config-detail">
                  <span className="detail-label">Purpose</span>
                  <span className="detail-value purpose-badge">
                    {config.additional_config?.purpose || 'General (Agents)'}
                  </span>
                </div>
                <div className="config-detail">
                  <span className="detail-label">Max Tokens</span>
                  <span className="detail-value">{config.max_tokens.toLocaleString()}</span>
                </div>
                <div className="config-detail">
                  <span className="detail-label">Temperature</span>
                  <span className="detail-value">{config.temperature}</span>
                </div>
                <div className="config-detail">
                  <span className="detail-label">API Key</span>
                  <span className="detail-value">
                    {config.has_api_key ? '••••••••' : <span className="no-key">Not set</span>}
                  </span>
                </div>
              </div>
              {config.api_base_url && (
                <div className="config-url">
                  <span className="detail-label">Base URL</span>
                  <span className="detail-value url">{config.api_base_url}</span>
                </div>
              )}
              {testResult && testResult.configId === config.id && (
                <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                  {testResult.success ? <CheckIcon size={14} /> : <AlertCircleIcon size={14} />}
                  {testResult.message}
                </div>
              )}
              {!config.is_default && config.is_active && llmPerms.canEdit && (
                <button className="btn-set-default" onClick={() => handleSetDefault(config)}>
                  Set as Default
                </button>
              )}
              {!config.is_active && (
                <div className="inactive-badge">Inactive</div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <LLMConfigModal
          config={editingConfig}
          providers={providers}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

const PURPOSE_OPTIONS = [
  { value: 'a2a_agents', label: 'AI Agents (Default)', description: 'Used by orchestrator and sub-agents for general AI tasks' },
  { value: 'tts', label: 'Text-to-Speech (TTS)', description: 'Used for voice synthesis in voice chat features' },
  { value: 'stt', label: 'Speech-to-Text (STT)', description: 'Used for voice transcription in voice chat features' },
  { value: 'embedding', label: 'Embeddings', description: 'Used for knowledge base vector embeddings' },
]

const LLMConfigModal = ({ config, providers, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    name: config?.name || '',
    provider: config?.provider || 'openai',
    api_base_url: config?.api_base_url || '',
    api_key: '',
    model_name: config?.model_name || '',
    max_tokens: config?.max_tokens || 4096,
    temperature: config?.temperature || 0.7,
    is_default: config?.is_default || false,
    is_active: config?.is_active ?? true,
    purpose: config?.additional_config?.purpose || 'a2a_agents',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [showApiKey, setShowApiKey] = useState(false)

  const selectedProvider = providers.find(p => p.id === formData.provider)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const { purpose, ...rest } = formData
      const submitData = {
        ...rest,
        additional_config: {
          ...(config?.additional_config || {}),
          purpose: purpose,
        }
      }
      if (config && !submitData.api_key) {
        delete submitData.api_key
      }
      await onSave(submitData)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content llm-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{config ? 'Edit LLM Configuration' : 'Add LLM Configuration'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="form-error">
                <AlertCircleIcon size={16} />
                {error}
              </div>
            )}

            <div className="form-group">
              <label>Configuration Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Production GPT-4, Development Claude"
                required
              />
            </div>

            <div className="form-group">
              <label>Purpose *</label>
              <select
                value={formData.purpose}
                onChange={e => setFormData({ ...formData, purpose: e.target.value })}
                className="purpose-select"
              >
                {PURPOSE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <span className="form-hint">
                {PURPOSE_OPTIONS.find(o => o.value === formData.purpose)?.description}
              </span>
            </div>

            <div className="form-group">
              <label>Provider *</label>
              <div className="provider-grid">
                {providers.map(provider => (
                  <button
                    key={provider.id}
                    type="button"
                    className={`provider-option ${formData.provider === provider.id ? 'selected' : ''}`}
                    onClick={() => setFormData({ 
                      ...formData, 
                      provider: provider.id,
                      model_name: provider.default_models[0] || formData.model_name,
                    })}
                  >
                    <span className="provider-name">{provider.name}</span>
                    <span className="provider-desc">{provider.description}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label>
                API Base URL {selectedProvider?.requires_base_url ? '*' : '(optional - for custom/self-hosted endpoints)'}
              </label>
              <input
                type="url"
                value={formData.api_base_url}
                onChange={e => setFormData({ ...formData, api_base_url: e.target.value })}
                placeholder={selectedProvider?.requires_base_url 
                  ? "https://your-endpoint.openai.azure.com/" 
                  : "Leave empty for default provider URL, or enter custom endpoint"
                }
                required={selectedProvider?.requires_base_url}
              />
              {!selectedProvider?.requires_base_url && (
                <span className="form-hint">
                  Use this if you're running a self-hosted LLM, using a proxy, or have a custom API endpoint
                </span>
              )}
            </div>

            {selectedProvider?.requires_api_key && (
              <div className="form-group">
                <label>
                  API Key {config ? '(leave empty to keep existing)' : '*'}
                </label>
                <div className="api-key-input">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={formData.api_key}
                    onChange={e => setFormData({ ...formData, api_key: e.target.value })}
                    placeholder={config?.has_api_key ? '••••••••' : 'sk-...'}
                    required={!config && selectedProvider?.requires_api_key}
                  />
                  <button
                    type="button"
                    className="toggle-visibility"
                    onClick={() => setShowApiKey(!showApiKey)}
                  >
                    {showApiKey ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>
            )}

            <div className="form-group">
              <label>Model Name *</label>
              {selectedProvider?.default_models?.length > 0 ? (
                <>
                  <select
                    value={selectedProvider.default_models.includes(formData.model_name) ? formData.model_name : '__custom__'}
                    onChange={e => {
                      if (e.target.value === '__custom__') {
                        setFormData({ ...formData, model_name: '' })
                      } else {
                        setFormData({ ...formData, model_name: e.target.value })
                      }
                    }}
                  >
                    <option value="">Select a model</option>
                    {selectedProvider.default_models.map(model => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                    <option value="__custom__">Custom model...</option>
                  </select>
                  {(!selectedProvider.default_models.includes(formData.model_name) || formData.model_name === '') && (
                    <input
                      type="text"
                      value={formData.model_name}
                      onChange={e => setFormData({ ...formData, model_name: e.target.value })}
                      placeholder="Enter custom model name (e.g., gpt-4-custom, my-fine-tuned-model)"
                      required
                      style={{ marginTop: '8px' }}
                    />
                  )}
                </>
              ) : (
                <input
                  type="text"
                  value={formData.model_name}
                  onChange={e => setFormData({ ...formData, model_name: e.target.value })}
                  placeholder="e.g., gpt-4o, claude-3-5-sonnet"
                  required
                />
              )}
              <span className="form-hint">
                For self-hosted or custom endpoints, enter the model name as configured on your server
              </span>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Max Tokens</label>
                <input
                  type="number"
                  value={formData.max_tokens}
                  onChange={e => setFormData({ ...formData, max_tokens: parseInt(e.target.value) || 4096 })}
                  min="1"
                  max="128000"
                />
              </div>
              <div className="form-group">
                <label>Temperature ({formData.temperature})</label>
                <input
                  type="range"
                  value={formData.temperature}
                  onChange={e => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                  min="0"
                  max="2"
                  step="0.1"
                />
              </div>
            </div>

            <div className="form-row checkboxes">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={e => setFormData({ ...formData, is_default: e.target.checked })}
                />
                Set as default configuration
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={e => setFormData({ ...formData, is_active: e.target.checked })}
                />
                Active
              </label>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (config ? 'Update' : 'Create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default LLMSettings
