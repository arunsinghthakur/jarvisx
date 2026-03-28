import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const SubWorkflowNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Sub-Workflow']
    if (data.config?.workflow_id) {
      lines.push(`Workflow: ${data.config.workflow_name || data.config.workflow_id}`)
    } else {
      lines.push('No workflow selected')
    }
    return lines
  }

  return (
    <div
      className={`compact-node sub-workflow-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Left} className="compact-handle target" />

      <div className="compact-node-icon sub-workflow">
        <span className="icon-emoji">📋</span>
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

SubWorkflowNode.displayName = 'SubWorkflowNode'

export default SubWorkflowNode
