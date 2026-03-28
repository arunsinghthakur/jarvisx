import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const WebhookResponseNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Webhook Response']
    if (data.config?.status_code) {
      lines.push(`Status: ${data.config.status_code}`)
    }
    return lines
  }

  return (
    <div
      className={`compact-node webhook-response-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon webhook-response">
        <span className="icon-emoji">↩️</span>
      </div>

      <Handle type="source" position={Position.Right} className="compact-handle source" />

      {showTooltip && (
        <div className="node-tooltip">
          {getTooltipContent().map((line, i) => (
            <div key={i} className={i === 0 ? 'tooltip-title' : 'tooltip-detail'}>{line}</div>
          ))}
        </div>
      )}
    </div>
  )
})

WebhookResponseNode.displayName = 'WebhookResponseNode'

export default WebhookResponseNode
