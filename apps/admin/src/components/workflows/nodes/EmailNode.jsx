import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const EmailNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getRecipientPreview = () => {
    const to = data.config?.to || ''
    if (!to) return ''
    const emails = to.split(',')
    if (emails.length > 1) {
      return `${emails[0].trim()} +${emails.length - 1}`
    }
    return emails[0].trim()
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'Send Email']
    if (data.config?.to) {
      lines.push(`To: ${getRecipientPreview()}`)
    }
    if (data.config?.subject) {
      const truncated = data.config.subject.length > 40 
        ? data.config.subject.substring(0, 40) + '...' 
        : data.config.subject
      lines.push(`Subject: ${truncated}`)
    }
    if (data.config?.include_attachment) {
      lines.push('📎 With attachment')
    }
    return lines
  }

  return (
    <div 
      className={`compact-node email-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon email">
        <span className="icon-emoji">📧</span>
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

EmailNode.displayName = 'EmailNode'

export default EmailNode
