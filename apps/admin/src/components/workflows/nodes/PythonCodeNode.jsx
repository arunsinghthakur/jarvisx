import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const PythonCodeNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node python-code-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />
      <div className="compact-node-icon python-code">
        <span className="icon-emoji">🐍</span>
      </div>
      <Handle type="source" position={Position.Right} className="compact-handle source" />
      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Python Code'}</div>
          <div className="tooltip-detail">Execute Python in sandbox</div>
        </div>
      )}
    </div>
  )
})

PythonCodeNode.displayName = 'PythonCodeNode'
export default PythonCodeNode
