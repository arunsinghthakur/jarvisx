import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ForEachNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'For Each']
    if (data.config?.array_field) {
      lines.push(`Over: {{input.${data.config.array_field}}}`)
    }
    lines.push('→ Body / Done branches')
    return lines
  }

  return (
    <div
      className={`compact-node foreach-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon foreach">
        <span className="icon-emoji">🔄</span>
      </div>

      <div className="compact-condition-handles">
        <Handle
          type="source"
          position={Position.Right}
          id="body"
          className="compact-handle source condition-true"
          style={{ top: '30%' }}
        />
        <Handle
          type="source"
          position={Position.Right}
          id="done"
          className="compact-handle source condition-false"
          style={{ top: '70%' }}
        />
      </div>

      <div className="compact-condition-labels">
        <span className="compact-condition-label true">→</span>
        <span className="compact-condition-label false">✓</span>
      </div>

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

ForEachNode.displayName = 'ForEachNode'

export default ForEachNode
