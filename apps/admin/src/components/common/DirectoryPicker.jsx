import React, { useState, useEffect, useCallback } from 'react'
import { platformApi } from '../../services/api'
import './DirectoryPicker.css'

function DirectoryPicker({ value, onChange, placeholder = 'Select directory' }) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentPath, setCurrentPath] = useState('')
  const [directories, setDirectories] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [canGoUp, setCanGoUp] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)

  const loadDirectories = useCallback(async (path = '') => {
    setLoading(true)
    setError(null)
    try {
      const response = await platformApi.browseDirectories(path)
      setDirectories(response.data.directories || [])
      setCurrentPath(response.data.current_path || '')
      setCanGoUp(response.data.can_go_up || false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load directories')
      setDirectories([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      loadDirectories(value || '')
    }
  }, [isOpen, loadDirectories])

  const handleOpen = () => {
    setIsOpen(true)
  }

  const handleClose = () => {
    setIsOpen(false)
    setShowNewFolder(false)
    setNewFolderName('')
  }

  const handleSelect = (dir) => {
    loadDirectories(dir.path)
  }

  const handleGoUp = () => {
    if (currentPath) {
      const parts = currentPath.split('/')
      parts.pop()
      const parentPath = parts.join('/')
      loadDirectories(parentPath)
    }
  }

  const handleConfirm = () => {
    onChange(currentPath || 'workflow_outputs')
    handleClose()
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return
    
    const newPath = currentPath ? `${currentPath}/${newFolderName.trim()}` : newFolderName.trim()
    try {
      await platformApi.browseDirectories(newPath)
      loadDirectories(currentPath)
      setShowNewFolder(false)
      setNewFolderName('')
    } catch (err) {
      setError('Failed to create folder')
    }
  }

  return (
    <div className="directory-picker">
      <div className="picker-input" onClick={handleOpen}>
        <span className="folder-icon">📁</span>
        <span className="picker-value">{value || placeholder}</span>
        <span className="picker-arrow">▼</span>
      </div>

      {isOpen && (
        <div className="picker-modal-overlay" onClick={handleClose}>
          <div className="picker-modal" onClick={e => e.stopPropagation()}>
            <div className="picker-header">
              <h3>Select Directory</h3>
              <button className="close-btn" onClick={handleClose}>×</button>
            </div>

            <div className="picker-path">
              <span className="path-label">Current:</span>
              <span className="path-value">/{currentPath || '(root)'}</span>
            </div>

            {error && (
              <div className="picker-error">{error}</div>
            )}

            <div className="picker-content">
              {loading ? (
                <div className="picker-loading">
                  <div className="loading-spinner" />
                  <span>Loading...</span>
                </div>
              ) : (
                <div className="directory-list">
                  {canGoUp && (
                    <div className="directory-item parent" onClick={handleGoUp}>
                      <span className="folder-icon">📂</span>
                      <span className="folder-name">..</span>
                    </div>
                  )}
                  {directories.length === 0 && !canGoUp ? (
                    <div className="directory-empty">
                      <span>No subdirectories</span>
                    </div>
                  ) : (
                    directories.map((dir) => (
                      <div
                        key={dir.path}
                        className="directory-item"
                        onClick={() => handleSelect(dir)}
                      >
                        <span className="folder-icon">📁</span>
                        <span className="folder-name">{dir.name}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {showNewFolder ? (
              <div className="new-folder-form">
                <input
                  type="text"
                  value={newFolderName}
                  onChange={e => setNewFolderName(e.target.value)}
                  placeholder="New folder name"
                  autoFocus
                  onKeyDown={e => {
                    if (e.key === 'Enter') handleCreateFolder()
                    if (e.key === 'Escape') setShowNewFolder(false)
                  }}
                />
                <button onClick={handleCreateFolder}>Create</button>
                <button onClick={() => setShowNewFolder(false)}>Cancel</button>
              </div>
            ) : (
              <button 
                className="new-folder-btn" 
                onClick={() => setShowNewFolder(true)}
              >
                + New Folder
              </button>
            )}

            <div className="picker-actions">
              <button className="btn-secondary" onClick={handleClose}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleConfirm}>
                Select: /{currentPath || '(root)'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DirectoryPicker
