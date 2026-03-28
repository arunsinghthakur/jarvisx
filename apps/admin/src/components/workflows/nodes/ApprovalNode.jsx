import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ApprovalNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Approval']
    if (data.config?.approvers?.length) {
      lines.push(`Approvers: ${data.config.approvers.join(', ')}`)
    }
    if (data.config?.message) {
      lines.push(`Message: ${data.config.message.substring(0, 40)}`)
    }
    return lines
  }

  return (
    <div
      className={`compact-node approval-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon approval">
        <span className="icon-emoji">✋</span>
      </div>

      <Handle type="source" position={Position.Right} className="compact-handle source" />

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

ApprovalNode.displayName = 'ApprovalNode'

export default ApprovalNode
