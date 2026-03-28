import React, { useState, useEffect, useCallback } from 'react'
import { platformApi } from '../../services/api'
import './FilePicker.css'

function FilePicker({ value, onChange, placeholder = 'Select file', extensions = '' }) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentPath, setCurrentPath] = useState('')
  const [files, setFiles] = useState([])
  const [directories, setDirectories] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [canGoUp, setCanGoUp] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)

  const loadFiles = useCallback(async (path = '') => {
    setLoading(true)
    setError(null)
    try {
      const response = await platformApi.browseFiles(path, extensions)
      setFiles(response.data.files || [])
      setDirectories(response.data.directories || [])
      setCurrentPath(response.data.current_path || '')
      setCanGoUp(response.data.can_go_up || false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load files')
      setFiles([])
      setDirectories([])
    } finally {
      setLoading(false)
    }
  }, [extensions])

  useEffect(() => {
    if (isOpen) {
      const initialPath = value ? value.substring(0, value.lastIndexOf('/')) : ''
      loadFiles(initialPath)
    }
  }, [isOpen, loadFiles])

  const handleOpen = () => {
    setIsOpen(true)
    setSelectedFile(value || null)
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedFile(null)
  }

  const handleDirectoryClick = (dir) => {
    loadFiles(dir.path)
    setSelectedFile(null)
  }

  const handleFileClick = (file) => {
    setSelectedFile(file.path)
  }

  const handleGoUp = () => {
    if (currentPath) {
      const parts = currentPath.split('/')
      parts.pop()
      const parentPath = parts.join('/')
      loadFiles(parentPath)
      setSelectedFile(null)
    }
  }

  const handleConfirm = () => {
    if (selectedFile) {
      onChange(selectedFile)
      handleClose()
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (ext) => {
    const icons = {
      txt: '📝',
      json: '{ }',
      md: '📋',
      csv: '📊',
      yaml: '⚙️',
      yml: '⚙️',
      xml: '📄',
      log: '📃',
      pdf: '📕',
      doc: '📘',
      docx: '📘',
      xls: '📗',
      xlsx: '📗',
      ppt: '📙',
      pptx: '📙',
      jpg: '🖼️',
      jpeg: '🖼️',
      png: '🖼️',
      gif: '🖼️',
      webp: '🖼️',
      bmp: '🖼️',
      tiff: '🖼️',
      mp3: '🎵',
      wav: '🎵',
      ogg: '🎵',
      flac: '🎵',
      aac: '🎵',
      m4a: '🎵',
      mp4: '🎬',
      webm: '🎬',
      avi: '🎬',
      mov: '🎬',
      mkv: '🎬',
    }
    return icons[ext] || '📄'
  }

  return (
    <div className="file-picker">
      <div className="picker-input" onClick={handleOpen}>
        <span className="file-icon">📄</span>
        <span className="picker-value">{value || placeholder}</span>
        <span className="picker-arrow">▼</span>
      </div>

      {isOpen && (
        <div className="picker-modal-overlay" onClick={handleClose}>
          <div className="picker-modal file-picker-modal" onClick={e => e.stopPropagation()}>
            <div className="picker-header">
              <h3>Select File</h3>
              <button className="close-btn" onClick={handleClose}>×</button>
            </div>

            <div className="picker-path">
              <span className="path-label">Location:</span>
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
                <div className="file-list">
                  {canGoUp && (
                    <div className="file-item directory" onClick={handleGoUp}>
                      <span className="file-icon">📂</span>
                      <span className="file-name">..</span>
                    </div>
                  )}
                  {directories.map((dir) => (
                    <div
                      key={dir.path}
                      className="file-item directory"
                      onClick={() => handleDirectoryClick(dir)}
                    >
                      <span className="file-icon">📁</span>
                      <span className="file-name">{dir.name}</span>
                    </div>
                  ))}
                  {files.length === 0 && directories.length === 0 && !canGoUp ? (
                    <div className="file-empty">
                      <span>No files found{extensions ? ` with extensions: ${extensions}` : ''}</span>
                    </div>
                  ) : (
                    files.map((file) => (
                      <div
                        key={file.path}
                        className={`file-item file ${selectedFile === file.path ? 'selected' : ''}`}
                        onClick={() => handleFileClick(file)}
                        onDoubleClick={() => {
                          onChange(file.path)
                          handleClose()
                        }}
                      >
                        <span className="file-icon">{getFileIcon(file.extension)}</span>
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">{formatFileSize(file.size_bytes)}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="picker-actions">
              <button className="btn-secondary" onClick={handleClose}>
                Cancel
              </button>
              <button 
                className="btn-primary" 
                onClick={handleConfirm}
                disabled={!selectedFile}
              >
                Select File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default FilePicker
