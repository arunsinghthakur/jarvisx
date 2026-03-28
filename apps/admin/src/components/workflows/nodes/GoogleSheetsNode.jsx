import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const GoogleSheetsNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node google-sheets-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />
      <div className="compact-node-icon google-sheets">
        <span className="icon-emoji">📊</span>
      </div>
      <Handle type="source" position={Position.Right} className="compact-handle source" />
      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Google Sheets'}</div>
          <div className="tooltip-detail">{data.config?.operation || 'read'}</div>
        </div>
      )}
    </div>
  )
})

GoogleSheetsNode.displayName = 'GoogleSheetsNode'
export default GoogleSheetsNode
