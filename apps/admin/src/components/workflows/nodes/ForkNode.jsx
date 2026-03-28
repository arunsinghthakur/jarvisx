import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ForkNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)
  const branchCount = Math.max(parseInt(data.config?.branches || '2', 10), 2)

  return (
    <div
      className={`compact-node fork-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon fork">
        <span className="icon-emoji">⑃</span>
      </div>

      {Array.from({ length: branchCount }, (_, i) => (
        <Handle
          key={`branch_${i}`}
          type="source"
          position={Position.Right}
          id={`branch_${i}`}
          className="compact-handle source"
          style={{ top: `${((i + 1) / (branchCount + 1)) * 100}%` }}
        />
      ))}

      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Fork'}</div>
          <div className="tooltip-detail">{branchCount} parallel branches</div>
        </div>
      )}
    </div>
  )
})

ForkNode.displayName = 'ForkNode'

export default ForkNode
