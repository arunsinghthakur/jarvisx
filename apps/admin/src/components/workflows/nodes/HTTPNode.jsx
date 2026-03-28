import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const HTTPNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getMethodBadge = () => {
    const method = data.config?.method || 'GET'
    return method
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'HTTP Request']
    if (data.config?.method) {
      lines.push(`Method: ${data.config.method}`)
    }
    if (data.config?.url) {
      const truncatedUrl = data.config.url.length > 40 
        ? data.config.url.substring(0, 40) + '...' 
        : data.config.url
      lines.push(`URL: ${truncatedUrl}`)
    }
    return lines
  }

  return (
    <div 
      className={`compact-node http-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon http">
        <span className="icon-emoji">🌐</span>
        {data.config?.method && (
          <span className={`method-indicator method-${data.config.method.toLowerCase()}`}>
            {data.config.method}
          </span>
        )}
      </div>
      
      {showTooltip && (
        <div className="node-tooltip">
          {getTooltipContent().map((line, i) => (
            <div key={i} className={i === 0 ? 'tooltip-title' : 'tooltip-detail'}>{line}</div>
          ))}
        </div>
      )}
      
      <Handle
        type="source"
        position={Position.Right}
        className="compact-handle source"
      />
    </div>
  )
})

HTTPNode.displayName = 'HTTPNode'

export default HTTPNode
