import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const FileSaveNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getFormatIcon = () => {
    const format = data.config?.format || 'txt'
    const icons = {
      pdf: '📄',
      txt: '📝',
      json: '{ }',
      md: '📋',
    }
    return icons[format] || '💾'
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'Save File']
    if (data.config?.format) {
      lines.push(`Format: ${data.config.format.toUpperCase()}`)
    }
    if (data.config?.filename) {
      lines.push(`File: ${data.config.filename}`)
    }
    if (data.config?.subdirectory) {
      lines.push(`Dir: ${data.config.subdirectory}`)
    }
    return lines
  }

  return (
    <div 
      className={`compact-node file-save-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon file-save">
        <span className="icon-emoji">💾</span>
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

FileSaveNode.displayName = 'FileSaveNode'

export default FileSaveNode
