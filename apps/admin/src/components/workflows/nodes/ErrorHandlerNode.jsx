import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ErrorHandlerNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className={`compact-node error-handler-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon error-handler">
        <span className="icon-emoji">🛡️</span>
      </div>

      <div className="compact-condition-handles">
        <Handle
          type="source"
          position={Position.Right}
          id="try"
          className="compact-handle source condition-true"
          style={{ top: '30%' }}
        />
        <Handle
          type="source"
          position={Position.Right}
          id="error"
          className="compact-handle source condition-false"
          style={{ top: '70%' }}
        />
      </div>

      <div className="compact-condition-labels">
        <span className="compact-condition-label true">✓</span>
        <span className="compact-condition-label false">✗</span>
      </div>

      {showTooltip && (
        <div className="node-tooltip">
          <div className="tooltip-title">{data.label || 'Error Handler'}</div>
          <div className="tooltip-detail">Try → body / Error → fallback</div>
        </div>
      )}
    </div>
  )
})

ErrorHandlerNode.displayName = 'ErrorHandlerNode'

export default ErrorHandlerNode
