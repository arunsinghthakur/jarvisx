import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const NotificationNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getPlatformInfo = () => {
    const platform = data.config?.platform || 'slack'
    const platforms = {
      slack: { icon: '💬', name: 'Slack' },
      teams: { icon: '👥', name: 'Teams' },
      discord: { icon: '🎮', name: 'Discord' },
    }
    return platforms[platform] || platforms.slack
  }

  const platformInfo = getPlatformInfo()

  const getTooltipContent = () => {
    const lines = [data.label || 'Notification']
    lines.push(`Platform: ${platformInfo.name}`)
    if (data.config?.message) {
      const truncated = data.config.message.length > 40 
        ? data.config.message.substring(0, 40) + '...' 
        : data.config.message
      lines.push(`Message: ${truncated}`)
    }
    if (data.config?.include_data) {
      lines.push('📊 Includes data')
    }
    return lines
  }

  return (
    <div 
      className={`compact-node notification-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon notification">
        <span className="icon-emoji">🔔</span>
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

NotificationNode.displayName = 'NotificationNode'

export default NotificationNode
