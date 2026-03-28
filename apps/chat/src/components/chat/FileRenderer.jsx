import React, { useState, useCallback, useMemo } from 'react'
import './FileRenderer.css'

const FILE_ICONS = {
  pdf: '📄',
  doc: '📝',
  docx: '📝',
  xls: '📊',
  xlsx: '📊',
  csv: '📊',
  txt: '📝',
  json: '{ }',
  png: '🖼️',
  jpg: '🖼️',
  jpeg: '🖼️',
  gif: '🖼️',
  webp: '🖼️',
  svg: '🖼️',
  zip: '📦',
  default: '📎',
}

function getFileIcon(filename) {
  if (!filename) return FILE_ICONS.default
  const ext = filename.split('.').pop()?.toLowerCase()
  return FILE_ICONS[ext] || FILE_ICONS.default
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function isImageFile(mimeType) {
  return mimeType?.startsWith('image/')
}

function isTextFile(mimeType) {
  return mimeType?.startsWith('text/') || mimeType === 'application/json'
}

export function FileRenderer({ config }) {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const { filename, mimeType, data, size, downloadable = true, previewable = true } = config || {}

  const dataUrl = useMemo(() => {
    if (!data) return null
    if (data.startsWith('data:')) return data
    return `data:${mimeType || 'application/octet-stream'};base64,${data}`
  }, [data, mimeType])

  const textContent = useMemo(() => {
    if (!isTextFile(mimeType) || !data) return null
    try {
      if (data.startsWith('data:')) {
        const base64 = data.split(',')[1]
        return atob(base64)
      }
      return atob(data)
    } catch {
      return null
    }
  }, [data, mimeType])

  const handleDownload = useCallback(() => {
    if (!dataUrl || !filename) return
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [dataUrl, filename])

  const handleCopy = useCallback(async () => {
    if (!textContent) return
    try {
      await navigator.clipboard.writeText(textContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [textContent])

  if (!config || !filename) {
    return <div className="file-error">No file data provided</div>
  }

  const icon = getFileIcon(filename)
  const isImage = isImageFile(mimeType)
  const isText = isTextFile(mimeType)
  const canPreview = previewable && (isImage || isText) && data

  return (
    <div className="file-renderer">
      <div className="file-card">
        <div className="file-card-icon">{icon}</div>
        <div className="file-card-info">
          <span className="file-card-name">{filename}</span>
          <span className="file-card-meta">
            {mimeType && <span className="file-type">{mimeType.split('/')[1]?.toUpperCase()}</span>}
            {size && <span className="file-size">{formatFileSize(size)}</span>}
          </span>
        </div>
        <div className="file-card-actions">
          {canPreview && (
            <button
              className="file-action-btn"
              onClick={() => setIsPreviewOpen(!isPreviewOpen)}
              title={isPreviewOpen ? 'Hide preview' : 'Show preview'}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {isPreviewOpen ? (
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24M1 1l22 22" />
                ) : (
                  <>
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </>
                )}
              </svg>
            </button>
          )}
          {isText && textContent && (
            <button
              className={`file-action-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopy}
              title="Copy content"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {copied ? (
                  <polyline points="20 6 9 17 4 12" />
                ) : (
                  <>
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </>
                )}
              </svg>
            </button>
          )}
          {downloadable && dataUrl && (
            <button
              className="file-action-btn download"
              onClick={handleDownload}
              title="Download file"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {isPreviewOpen && canPreview && (
        <div className="file-preview">
          {isImage && dataUrl && (
            <img src={dataUrl} alt={filename} className="file-preview-image" />
          )}
          {isText && textContent && (
            <pre className="file-preview-text">{textContent}</pre>
          )}
        </div>
      )}
    </div>
  )
}

export { getFileIcon, formatFileSize, isImageFile, isTextFile }
