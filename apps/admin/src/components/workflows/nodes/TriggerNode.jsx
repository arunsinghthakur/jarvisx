import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const TriggerNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getSubTypeIcon = () => {
    switch (data.subType) {
      case 'manual':
        return '▶️'
      case 'schedule':
        return '⏰'
      case 'webhook':
        return '🔗'
      case 'chatbot':
        return '💬'
      default:
        return '⚡'
    }
  }

  const getSubTypeLabel = () => {
    switch (data.subType) {
      case 'manual':
        return 'Manual'
      case 'schedule':
        return 'Schedule'
      case 'webhook':
        return 'Webhook'
      case 'chatbot':
        return 'Chatbot'
      default:
        return 'Trigger'
    }
  }

  const getTooltipContent = () => {
    const lines = [data.label || getSubTypeLabel()]
    if (data.subType === 'schedule' && data.config?.cron) {
      lines.push(`Cron: ${data.config.cron}`)
    }
    if (data.subType === 'chatbot' && data.config?.bot_name) {
      lines.push(`Bot: ${data.config.bot_name}`)
    }
    return lines
  }

  return (
    <div 
      className={`compact-node trigger-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="compact-node-icon trigger">
        <span className="icon-emoji">{getSubTypeIcon()}</span>
      </div>
      
      {showTooltip && (
        <div className="node-tooltip">
          {getTooltipContent().map((line, i) => (
            <div key={i} className={i === 0 ? 'tooltip-title' : 'tooltip-detail'}>{line}</div>
          ))}
        </div>
      )}
      
      <Handle
        type="source"
        position={Position.Right}
        className="compact-handle source"
      />
    </div>
  )
})

TriggerNode.displayName = 'TriggerNode'

export default TriggerNode
