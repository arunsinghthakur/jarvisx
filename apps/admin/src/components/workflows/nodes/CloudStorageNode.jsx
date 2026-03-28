import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const CloudStorageNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node cloud-storage-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />
      <div className="compact-node-icon cloud-storage">
        <span className="icon-emoji">☁️</span>
      </div>
      <Handle type="source" position={Position.Right} className="compact-handle source" />
      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Cloud Storage'}</div>
          <div className="tooltip-detail">{data.config?.provider || 's3'} / {data.config?.operation || 'download'}</div>
        </div>
      )}
    </div>
  )
})

CloudStorageNode.displayName = 'CloudStorageNode'
export default CloudStorageNode
