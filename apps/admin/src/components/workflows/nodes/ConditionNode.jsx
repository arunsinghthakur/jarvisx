import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ConditionNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getTooltipContent = () => {
    const lines = [data.label || 'Condition']
    if (data.config?.condition) {
      const truncated = data.config.condition.length > 40 
        ? data.config.condition.substring(0, 40) + '...' 
        : data.config.condition
      lines.push(`If: ${truncated}`)
    }
    lines.push('→ True / False branches')
    return lines
  }

  return (
    <div 
      className={`compact-node condition-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon condition">
        <span className="icon-emoji">🔀</span>
      </div>
      
      <div className="compact-condition-handles">
        <Handle
          type="source"
          position={Position.Right}
          id="true"
          className="compact-handle source condition-true"
          style={{ top: '30%' }}
        />
        <Handle
          type="source"
          position={Position.Right}
          id="false"
          className="compact-handle source condition-false"
          style={{ top: '70%' }}
        />
      </div>
      
      <div className="compact-condition-labels">
        <span className="compact-condition-label true">T</span>
        <span className="compact-condition-label false">F</span>
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

ConditionNode.displayName = 'ConditionNode'

export default ConditionNode
