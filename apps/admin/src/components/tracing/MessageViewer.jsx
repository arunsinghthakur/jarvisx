import React, { useState, useMemo } from 'react'
import { CopyIcon } from '../common/Icons'

const MessageViewer = ({ data, title, defaultView = 'pretty' }) => {
  const [viewMode, setViewMode] = useState(defaultView)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const textToCopy = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const parseMessages = useMemo(() => {
    if (!data) return null
    
    if (Array.isArray(data)) {
      const hasRoles = data.some(item => item && typeof item === 'object' && item.role)
      if (hasRoles) {
        return data.filter(msg => msg && typeof msg === 'object')
      }
    }
    
    if (typeof data === 'object' && !Array.isArray(data)) {
      if (data.messages && Array.isArray(data.messages)) {
        return data.messages.filter(msg => msg && typeof msg === 'object')
      }
    }
    
    return null
  }, [data])

  const renderMessageContent = (content) => {
    if (!content) return null
    
    if (typeof content === 'string') {
      return <span className="message-text">{content}</span>
    }
    
    if (Array.isArray(content)) {
      return content.map((part, idx) => {
        if (typeof part === 'string') {
          return <span key={idx} className="message-text">{part}</span>
        }
        if (part.type === 'text') {
          return <span key={idx} className="message-text">{part.text}</span>
        }
        if (part.type === 'image_url' || part.type === 'image') {
          return (
            <div key={idx} className="message-image">
              <span className="image-placeholder">[Image]</span>
            </div>
          )
        }
        return <pre key={idx} className="message-json">{JSON.stringify(part, null, 2)}</pre>
      })
    }
    
    return <pre className="message-json">{JSON.stringify(content, null, 2)}</pre>
  }

  const renderPrettyView = () => {
    if (parseMessages) {
      return (
        <div className="messages-list">
          {parseMessages.map((msg, index) => (
            <div key={index} className={`message-item role-${msg.role || 'unknown'}`}>
              <div className="message-role">
                <span className={`role-badge ${msg.role || 'unknown'}`}>
                  {msg.role || 'unknown'}
                </span>
                {msg.name && <span className="message-name">{msg.name}</span>}
              </div>
              <div className="message-content">
                {renderMessageContent(msg.content)}
              </div>
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="tool-calls">
                  <div className="tool-calls-header">Tool Calls</div>
                  {msg.tool_calls.map((tool, toolIdx) => (
                    <div key={toolIdx} className="tool-call-item">
                      <span className="tool-name">{tool.function?.name || tool.name || 'Unknown'}</span>
                      {tool.function?.arguments && (
                        <pre className="tool-arguments">
                          {typeof tool.function.arguments === 'string' 
                            ? tool.function.arguments 
                            : JSON.stringify(tool.function.arguments, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )
    }

    if (typeof data === 'string') {
      return <div className="plain-text-content">{data}</div>
    }

    return (
      <pre className="json-content">
        {JSON.stringify(data, null, 2)}
      </pre>
    )
  }

  const renderJsonView = () => {
    const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
    return (
      <pre className="json-content">
        {jsonString}
      </pre>
    )
  }

  if (data === null || data === undefined) {
    return (
      <div className="message-viewer empty">
        <span className="empty-text">No data</span>
      </div>
    )
  }

  return (
    <div className="message-viewer">
      <div className="viewer-header">
        {title && <span className="viewer-title">{title}</span>}
        <div className="viewer-controls">
          <div className="view-toggle">
            <button
              className={`toggle-btn ${viewMode === 'pretty' ? 'active' : ''}`}
              onClick={() => setViewMode('pretty')}
            >
              Pretty
            </button>
            <button
              className={`toggle-btn ${viewMode === 'json' ? 'active' : ''}`}
              onClick={() => setViewMode('json')}
            >
              JSON
            </button>
          </div>
          <button className="copy-btn" onClick={handleCopy} title="Copy to clipboard">
            <CopyIcon size={14} />
            {copied && <span className="copied-text">Copied!</span>}
          </button>
        </div>
      </div>
      <div className="viewer-content">
        {viewMode === 'pretty' ? renderPrettyView() : renderJsonView()}
      </div>
    </div>
  )
}

export default MessageViewer
