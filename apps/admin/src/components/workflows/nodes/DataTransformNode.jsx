import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const DataTransformNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node data-transform-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />
      <div className="compact-node-icon data-transform">
        <span className="icon-emoji">🔧</span>
      </div>
      <Handle type="source" position={Position.Right} className="compact-handle source" />
      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Data Transform'}</div>
          <div className="tooltip-detail">{data.config?.operation || 'parse_json'}</div>
        </div>
      )}
    </div>
  )
})

DataTransformNode.displayName = 'DataTransformNode'
export default DataTransformNode
