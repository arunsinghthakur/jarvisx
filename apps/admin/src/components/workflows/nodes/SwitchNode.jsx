import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const SwitchNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)
  const cases = data.config?.cases || []

  const getTooltipContent = () => {
    const lines = [data.label || 'Switch']
    if (data.config?.expression) {
      lines.push(`Expr: ${data.config.expression.substring(0, 40)}`)
    }
    cases.forEach(c => lines.push(`Case: ${c.label || c.value}`))
    lines.push('+ Default branch')
    return lines
  }

  const handleCount = cases.length + 1

  return (
    <div
      className={`compact-node switch-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon switch">
        <span className="icon-emoji">🔀</span>
      </div>

      <div className="compact-switch-handles">
        {cases.map((c, i) => (
          <Handle
            key={c.label || c.value}
            type="source"
            position={Position.Right}
            id={c.label || String(c.value)}
            className="compact-handle source"
            style={{ top: `${((i + 1) / (handleCount + 1)) * 100}%` }}
          />
        ))}
        <Handle
          type="source"
          position={Position.Right}
          id="default"
          className="compact-handle source"
          style={{ top: `${(handleCount / (handleCount + 1)) * 100}%` }}
        />
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

SwitchNode.displayName = 'SwitchNode'

export default SwitchNode
