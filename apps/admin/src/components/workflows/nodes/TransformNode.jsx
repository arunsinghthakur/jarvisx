import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const TransformNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Transform']
    if (data.config?.code) {
      const truncated = data.config.code.length > 50 
        ? data.config.code.substring(0, 50) + '...' 
        : data.config.code
      lines.push(`Code: ${truncated}`)
    }
    return lines
  }

  return (
    <div 
      className={`compact-node transform-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon transform">
        <span className="icon-emoji">⚡</span>
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

TransformNode.displayName = 'TransformNode'

export default TransformNode
