import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const JoinNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node join-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon join">
        <span className="icon-emoji">⑂</span>
      </div>

      <Handle type="source" position={Position.Right} className="compact-handle source" />

      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Join'}</div>
          <div className="tooltip-detail">Waits for all branches</div>
        </div>
      )}
    </div>
  )
})

JoinNode.displayName = 'JoinNode'

export default JoinNode
