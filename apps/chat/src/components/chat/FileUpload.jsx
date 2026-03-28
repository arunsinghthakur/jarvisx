import React, { useState, useRef, useCallback } from 'react'
import './FileUpload.css'

const ALLOWED_TYPES = {
  'application/pdf': { icon: '📕', label: 'PDF', category: 'document' },
  'text/plain': { icon: '📝', label: 'Text', category: 'text' },
  'text/csv': { icon: '📊', label: 'CSV', category: 'text' },
  'text/markdown': { icon: '📋', label: 'Markdown', category: 'text' },
  'application/json': { icon: '{ }', label: 'JSON', category: 'text' },
  'image/png': { icon: '🖼️', label: 'PNG', category: 'image' },
  'image/jpeg': { icon: '🖼️', label: 'JPEG', category: 'image' },
  'image/gif': { icon: '🖼️', label: 'GIF', category: 'image' },
  'image/webp': { icon: '🖼️', label: 'WebP', category: 'image' },
  'image/bmp': { icon: '🖼️', label: 'BMP', category: 'image' },
  'image/tiff': { icon: '🖼️', label: 'TIFF', category: 'image' },
  'audio/mpeg': { icon: '🎵', label: 'MP3', category: 'audio' },
  'audio/mp3': { icon: '🎵', label: 'MP3', category: 'audio' },
  'audio/wav': { icon: '🎵', label: 'WAV', category: 'audio' },
  'audio/x-wav': { icon: '🎵', label: 'WAV', category: 'audio' },
  'audio/ogg': { icon: '🎵', label: 'OGG', category: 'audio' },
  'audio/flac': { icon: '🎵', label: 'FLAC', category: 'audio' },
  'audio/aac': { icon: '🎵', label: 'AAC', category: 'audio' },
  'audio/mp4': { icon: '🎵', label: 'M4A', category: 'audio' },
  'audio/webm': { icon: '🎵', label: 'WebM Audio', category: 'audio' },
  'video/mp4': { icon: '🎬', label: 'MP4', category: 'video' },
  'video/webm': { icon: '🎬', label: 'WebM', category: 'video' },
  'video/quicktime': { icon: '🎬', label: 'MOV', category: 'video' },
  'video/x-msvideo': { icon: '🎬', label: 'AVI', category: 'video' },
  'video/x-matroska': { icon: '🎬', label: 'MKV', category: 'video' },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: '📗', label: 'Excel', category: 'document' },
  'application/vnd.ms-excel': { icon: '📗', label: 'Excel', category: 'document' },
  'application/msword': { icon: '📘', label: 'Word', category: 'document' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: '📘', label: 'Word', category: 'document' },
  'application/vnd.ms-powerpoint': { icon: '📙', label: 'PowerPoint', category: 'document' },
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': { icon: '📙', label: 'PowerPoint', category: 'document' },
}

const MAX_FILE_SIZE = 50 * 1024 * 1024

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getFileTypeInfo(mimeType) {
  return ALLOWED_TYPES[mimeType] || { icon: '📎', label: 'File' }
}

export function FileUpload({ onFileSelect, onFileRemove, selectedFiles = [], disabled = false, multiple = true }) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const validateFile = useCallback((file) => {
    if (!Object.keys(ALLOWED_TYPES).includes(file.type)) {
      return `File type "${file.type || 'unknown'}" is not supported`
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds ${formatFileSize(MAX_FILE_SIZE)} limit`
    }
    return null
  }, [])

  const handleFiles = useCallback((files) => {
    setError(null)
    const validFiles = []
    const errors = []

    Array.from(files).forEach(file => {
      const validationError = validateFile(file)
      if (validationError) {
        errors.push(`${file.name}: ${validationError}`)
      } else {
        validFiles.push(file)
      }
    })

    if (errors.length > 0) {
      setError(errors.join('\n'))
    }

    if (validFiles.length > 0 && onFileSelect) {
      onFileSelect(multiple ? validFiles : [validFiles[0]])
    }
  }, [validateFile, onFileSelect, multiple])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) setIsDragging(true)
  }, [disabled])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (!disabled && e.dataTransfer.files?.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }, [disabled, handleFiles])

  const handleClick = useCallback(() => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click()
    }
  }, [disabled])

  const handleInputChange = useCallback((e) => {
    if (e.target.files?.length > 0) {
      handleFiles(e.target.files)
      e.target.value = ''
    }
  }, [handleFiles])

  const handleRemove = useCallback((index) => {
    if (onFileRemove) {
      onFileRemove(index)
    }
  }, [onFileRemove])

  return (
    <div className="file-upload-container">
      <div
        className={`file-upload-dropzone ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={Object.keys(ALLOWED_TYPES).join(',')}
          onChange={handleInputChange}
          disabled={disabled}
          className="file-input-hidden"
        />
        
        <div className="dropzone-content">
          <svg className="upload-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="dropzone-text">
            <span className="dropzone-primary">Click to upload</span> or drag and drop
          </p>
          <p className="dropzone-hint">
            Images, Documents, Audio, Video (max {formatFileSize(MAX_FILE_SIZE)})
          </p>
        </div>
      </div>

      {error && (
        <div className="file-upload-error">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="file-upload-list">
          {selectedFiles.map((file, index) => {
            const typeInfo = getFileTypeInfo(file.type)
            return (
              <div key={`${file.name}-${index}`} className="file-upload-item">
                <span className="file-icon">{typeInfo.icon}</span>
                <div className="file-info">
                  <span className="file-name">{file.name}</span>
                  <span className="file-meta">
                    {typeInfo.label} • {formatFileSize(file.size)}
                  </span>
                </div>
                <button
                  className="file-remove-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleRemove(index)
                  }}
                  title="Remove file"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = reader.result.split(',')[1]
      resolve({
        filename: file.name,
        content: base64,
        mime_type: file.type,
        size_bytes: file.size,
        category: ALLOWED_TYPES[file.type]?.category || 'unknown',
      })
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export async function filesToBase64(files) {
  return Promise.all(files.map(fileToBase64))
}

export { ALLOWED_TYPES, MAX_FILE_SIZE, formatFileSize, getFileTypeInfo }
