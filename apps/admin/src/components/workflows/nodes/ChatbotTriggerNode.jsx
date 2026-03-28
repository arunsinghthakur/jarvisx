import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const ChatbotTriggerNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getChatModeLabel = () => {
    const modes = {
      text: 'Text Only',
      voice: 'Voice Only',
      both: 'Text + Voice',
    }
    return modes[data.config?.chat_mode] || 'Text + Voice'
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'Chatbot']
    if (data.config?.bot_name) {
      lines.push(`Bot: ${data.config.bot_name}`)
    }
    lines.push(`Mode: ${getChatModeLabel()}`)
    if (data.config?.allow_file_upload) {
      lines.push('📎 File upload enabled')
    }
    return lines
  }

  return (
    <div 
      className={`compact-node trigger-node chatbot-trigger ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="compact-node-icon chatbot">
        <span className="icon-emoji">💬</span>
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

ChatbotTriggerNode.displayName = 'ChatbotTriggerNode'

export default ChatbotTriggerNode
