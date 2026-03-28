import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const FileReadNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getFileExtension = () => {
    const filePath = data.config?.file_path || ''
    if (!filePath) return ''
    const parts = filePath.split('.')
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
  }

  const getFileCategory = () => {
    const ext = getFileExtension()
    const categories = {
      txt: 'text', json: 'text', md: 'text', csv: 'text', yaml: 'text', yml: 'text', xml: 'text', log: 'text',
      pdf: 'document', doc: 'document', docx: 'document', xls: 'document', xlsx: 'document', ppt: 'document', pptx: 'document',
      jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', webp: 'image', bmp: 'image', tiff: 'image',
      mp3: 'audio', wav: 'audio', ogg: 'audio', flac: 'audio', aac: 'audio', m4a: 'audio',
      mp4: 'video', webm: 'video', avi: 'video', mov: 'video', mkv: 'video',
    }
    return categories[ext] || 'text'
  }

  const getFilename = () => {
    const filePath = data.config?.file_path || ''
    if (!filePath) return ''
    const parts = filePath.split('/')
    return parts[parts.length - 1] || filePath
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'Read File']
    if (data.config?.file_path) {
      lines.push(`File: ${getFilename()}`)
      const ext = getFileExtension()
      if (ext) {
        lines.push(`Type: ${ext.toUpperCase()} (${getFileCategory()})`)
      }
    }
    return lines
  }

  return (
    <div 
      className={`compact-node file-read-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon file-read">
        <span className="icon-emoji">📂</span>
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

FileReadNode.displayName = 'FileReadNode'

export default FileReadNode
