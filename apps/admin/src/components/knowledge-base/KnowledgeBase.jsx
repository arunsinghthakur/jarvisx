import React, { useState, useEffect, useCallback, useRef } from 'react'
import { knowledgeBaseApi } from '../../services'
import {
  PlusIcon,
  EditIcon,
  TrashIcon,
  SearchIcon,
  AlertCircleIcon,
  RefreshIcon,
  UploadIcon,
  DocumentIcon,
  SnippetIcon,
  KnowledgeBaseIcon,
} from '../common'
import { usePermissions } from '../../hooks'
import './KnowledgeBase.css'

const KnowledgeBase = ({ organizations = [], isPlatformAdmin, currentOrganization }) => {
  const { knowledgeBase: kbPerms } = usePermissions()
  const [selectedOrganization, setSelectedOrganization] = useState(null)
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showSnippetModal, setShowSnippetModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [editingEntry, setEditingEntry] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (currentOrganization && !selectedOrganization) {
      setSelectedOrganization(currentOrganization)
    }
  }, [currentOrganization, selectedOrganization])

  const loadData = useCallback(async () => {
    if (!selectedOrganization) return
    setLoading(true)
    setError(null)
    try {
      const [entriesRes, statsRes] = await Promise.all([
        knowledgeBaseApi.getEntries(selectedOrganization.id),
        knowledgeBaseApi.getStats(selectedOrganization.id),
      ])
      setEntries(entriesRes.data.entries || [])
      setStats(statsRes.data)
    } catch (err) {
      console.error('Failed to load knowledge base:', err)
      setError('Failed to load knowledge base')
    } finally {
      setLoading(false)
    }
  }, [selectedOrganization])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim() || !selectedOrganization) return
    
    setSearching(true)
    setSearchResults(null)
    try {
      const res = await knowledgeBaseApi.search(selectedOrganization.id, searchQuery)
      setSearchResults(res.data)
    } catch (err) {
      console.error('Search failed:', err)
      setError('Search failed')
    } finally {
      setSearching(false)
    }
  }

  const handleCreateSnippet = () => {
    setEditingEntry(null)
    setShowSnippetModal(true)
  }

  const handleEditSnippet = async (entry) => {
    try {
      const contentRes = await knowledgeBaseApi.getEntryContent(selectedOrganization.id, entry.id)
      setEditingEntry({ ...entry, content: contentRes.data.content })
      setShowSnippetModal(true)
    } catch (err) {
      setError('Failed to load entry content')
    }
  }

  const handleDelete = async (entry) => {
    if (!window.confirm(`Delete "${entry.title}"?`)) return
    try {
      await knowledgeBaseApi.deleteEntry(selectedOrganization.id, entry.id)
      loadData()
    } catch (err) {
      setError('Failed to delete entry')
    }
  }

  const handleSaveSnippet = async (formData) => {
    try {
      if (editingEntry) {
        await knowledgeBaseApi.updateSnippet(selectedOrganization.id, editingEntry.id, formData)
      } else {
        await knowledgeBaseApi.createSnippet(selectedOrganization.id, formData)
      }
      setShowSnippetModal(false)
      loadData()
    } catch (err) {
      throw err
    }
  }

  const handleUploadDocument = async (file, title) => {
    try {
      await knowledgeBaseApi.uploadDocument(selectedOrganization.id, file, title)
      setShowUploadModal(false)
      loadData()
    } catch (err) {
      throw err
    }
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const availableOrganizations = currentOrganization ? [currentOrganization] : []

  return (
    <div className="kb-container">
      <div className="kb-header">
        <div className="kb-header-left">
          <h2>Knowledge Base</h2>
          <p>Store and search your organization's knowledge for AI-powered retrieval</p>
        </div>
        <div className="kb-header-right">
        </div>
      </div>

      {error && (
        <div className="kb-error-banner">
          <AlertCircleIcon size={16} />
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {selectedOrganization && (
        <div className="kb-org-info" style={{ 
          background: '#f0f9ff', 
          border: '1px solid #bae6fd', 
          borderRadius: '8px', 
          padding: '12px 16px',
          marginBottom: '20px',
          fontSize: '0.9rem',
          color: '#0369a1'
        }}>
          <strong>Organization:</strong> {selectedOrganization.name}
          <span style={{ marginLeft: '16px', color: '#64748b' }}>
            Knowledge base is shared across all workspaces in this organization
          </span>
        </div>
      )}

      {stats && (
        <div className="kb-stats">
          <div className="kb-stat-card">
            <div className="kb-stat-value">{stats.total_entries}</div>
            <div className="kb-stat-label">Total Entries</div>
          </div>
          <div className="kb-stat-card">
            <div className="kb-stat-value">{stats.total_chunks}</div>
            <div className="kb-stat-label">Text Chunks</div>
          </div>
          <div className="kb-stat-card">
            <div className="kb-stat-value">{stats.entries_by_type?.document || 0}</div>
            <div className="kb-stat-label">Documents</div>
          </div>
          <div className="kb-stat-card">
            <div className="kb-stat-value">{stats.entries_by_type?.snippet || 0}</div>
            <div className="kb-stat-label">Snippets</div>
          </div>
        </div>
      )}

      <div className="kb-actions">
        {kbPerms.canCreate && (
          <>
            <button className="btn-primary" onClick={handleCreateSnippet}>
              <PlusIcon size={16} />
              Add Snippet
            </button>
            <button className="btn-secondary" onClick={() => setShowUploadModal(true)}>
              <UploadIcon size={16} />
              Upload Document
            </button>
          </>
        )}
        <button className="btn-secondary" onClick={loadData} disabled={loading}>
          <RefreshIcon size={16} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      <div className="kb-search-section">
        <h3>Search Knowledge Base</h3>
        <form className="kb-search-form" onSubmit={handleSearch}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Ask a question or search for content..."
          />
          <button type="submit" className="btn-primary" disabled={searching || !searchQuery.trim()}>
            {searching ? <RefreshIcon size={16} className="spinning" /> : <SearchIcon size={16} />}
            Search
          </button>
        </form>
        
        {searchResults && (
          <div className="kb-search-results">
            {searchResults.results.length === 0 ? (
              <p style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>
                No results found for "{searchResults.query}"
              </p>
            ) : (
              searchResults.results.map((result, idx) => (
                <div key={idx} className="kb-search-result">
                  <div className="kb-search-result-header">
                    <span className="kb-search-result-title">{result.entry_title}</span>
                    <span className="kb-search-result-score">
                      {(result.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <div className="kb-search-result-content">{result.chunk_content}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="kb-entries-section">
        <h3>All Entries ({entries.length})</h3>
        
        {loading ? (
          <div className="kb-loading">
            <div className="loading-spinner"></div>
            <span>Loading entries...</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="kb-empty-state">
            <div className="kb-empty-icon">
              <KnowledgeBaseIcon size={64} />
            </div>
            <h3>No Knowledge Base Entries</h3>
            <p>{kbPerms.canCreate ? 'Add snippets or upload documents to build your organization\'s knowledge base.' : 'No entries available in the knowledge base.'}</p>
            {kbPerms.canCreate && (
              <button className="btn-primary" onClick={handleCreateSnippet}>
                <PlusIcon size={16} />
                Add Your First Entry
              </button>
            )}
          </div>
        ) : (
          <div className="kb-entries-grid">
            {entries.map(entry => (
              <div key={entry.id} className="kb-entry-card">
                <div className="kb-entry-header">
                  <span className={`kb-entry-type ${entry.entry_type}`}>
                    {entry.entry_type === 'document' ? <DocumentIcon size={12} /> : <SnippetIcon size={12} />}
                    {entry.entry_type}
                  </span>
                  <div className="kb-entry-actions">
                    {kbPerms.canEdit && entry.entry_type === 'snippet' && (
                      <button className="btn-icon" onClick={() => handleEditSnippet(entry)} title="Edit">
                        <EditIcon size={14} />
                      </button>
                    )}
                    {kbPerms.canDelete && (
                      <button className="btn-icon danger" onClick={() => handleDelete(entry)} title="Delete">
                        <TrashIcon size={14} />
                      </button>
                    )}
                  </div>
                </div>
                <div className="kb-entry-title">{entry.title}</div>
                <div className="kb-entry-preview">{entry.content_preview}</div>
                <div className="kb-entry-meta">
                  <span>{entry.chunk_count} chunks</span>
                  <span>{formatDate(entry.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showSnippetModal && (
        <SnippetModal
          entry={editingEntry}
          onSave={handleSaveSnippet}
          onClose={() => setShowSnippetModal(false)}
        />
      )}

      {showUploadModal && (
        <UploadModal
          onUpload={handleUploadDocument}
          onClose={() => setShowUploadModal(false)}
        />
      )}
    </div>
  )
}

const SnippetModal = ({ entry, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    title: entry?.title || '',
    content: entry?.content || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.content.trim()) {
      setError('Title and content are required')
      return
    }
    setSaving(true)
    setError(null)
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
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{entry ? 'Edit Snippet' : 'Add Snippet'}</h3>
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
              <label>Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., Company FAQ, Product Guidelines"
                required
              />
            </div>
            <div className="form-group">
              <label>Content *</label>
              <textarea
                value={formData.content}
                onChange={e => setFormData({ ...formData, content: e.target.value })}
                placeholder="Enter the knowledge content here..."
                required
              />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (entry ? 'Update' : 'Create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const UploadModal = ({ onUpload, onClose }) => {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      validateAndSetFile(droppedFile)
    }
  }

  const validateAndSetFile = (f) => {
    const allowedTypes = ['.txt', '.md', '.pdf']
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!allowedTypes.includes(ext)) {
      setError(`File type not supported. Allowed: ${allowedTypes.join(', ')}`)
      return
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('File size exceeds 10MB limit')
      return
    }
    setFile(f)
    setError(null)
    if (!title) {
      setTitle(f.name.replace(/\.[^/.]+$/, ''))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }
    setUploading(true)
    setError(null)
    try {
      await onUpload(file, title || file.name)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload')
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Upload Document</h3>
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
              <label>Document Title (optional)</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Leave empty to use filename"
              />
            </div>
            <div className="form-group">
              <label>File *</label>
              <div
                className={`file-upload-area ${dragging ? 'dragging' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.pdf"
                  onChange={(e) => e.target.files[0] && validateAndSetFile(e.target.files[0])}
                />
                <div className="file-upload-icon">
                  <UploadIcon size={48} />
                </div>
                <p>Drag & drop a file here, or click to browse</p>
                <p className="file-types">Supported: .txt, .md, .pdf (max 10MB)</p>
              </div>
              {file && (
                <div className="selected-file">
                  <DocumentIcon size={24} />
                  <div className="selected-file-info">
                    <div className="selected-file-name">{file.name}</div>
                    <div className="selected-file-size">{formatFileSize(file.size)}</div>
                  </div>
                  <button type="button" className="btn-icon danger" onClick={() => setFile(null)}>
                    <TrashIcon size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={uploading || !file}>
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default KnowledgeBase
