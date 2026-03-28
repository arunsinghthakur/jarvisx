import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const LoopNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Loop']
    if (data.config?.max_iterations) {
      lines.push(`Max: ${data.config.max_iterations} iterations`)
    }
    if (data.config?.break_condition) {
      const truncated = data.config.break_condition.length > 40
        ? data.config.break_condition.substring(0, 40) + '...'
        : data.config.break_condition
      lines.push(`Break: ${truncated}`)
    }
    lines.push('→ Loop / Done branches')
    return lines
  }

  return (
    <div
      className={`compact-node loop-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon loop">
        <span className="icon-emoji">🔁</span>
      </div>

      <div className="compact-condition-handles">
        <Handle
          type="source"
          position={Position.Right}
          id="loop"
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
        <span className="compact-condition-label true">↺</span>
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

LoopNode.displayName = 'LoopNode'

export default LoopNode
