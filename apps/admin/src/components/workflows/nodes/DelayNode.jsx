import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const DelayNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Delay']
    const secs = data.config?.delay_seconds || 0
    const ms = data.config?.delay_ms || 0
    if (secs > 0) lines.push(`Wait: ${secs}s`)
    else if (ms > 0) lines.push(`Wait: ${ms}ms`)
    else lines.push('No delay configured')
    return lines
  }

  return (
    <div
      className={`compact-node delay-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon delay">
        <span className="icon-emoji">⏳</span>
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

DelayNode.displayName = 'DelayNode'

export default DelayNode
