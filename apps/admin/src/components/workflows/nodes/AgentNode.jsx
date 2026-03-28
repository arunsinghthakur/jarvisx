import React, { memo, useState } from 'react'
import { Handle, Position } from 'reactflow'
import './NodeStyles.css'

const AgentNode = memo(({ data, selected }) => {
  const [showTooltip, setShowTooltip] = useState(false)

  const getAgentLabel = () => {
    const agents = {
      orchestrator: 'Orchestrator',
      developer: 'Developer',
      researcher: 'Researcher',
      browser: 'Browser',
      knowledge: 'Knowledge',
    }
    return agents[data.config?.agent] || 'Agent'
  }

  const getTooltipContent = () => {
    const lines = [data.label || 'Agent Node']
    if (data.config?.agent) {
      lines.push(`Agent: ${getAgentLabel()}`)
    }
    if (data.config?.prompt) {
      const truncatedPrompt = data.config.prompt.length > 50 
        ? data.config.prompt.substring(0, 50) + '...' 
        : data.config.prompt
      lines.push(`Prompt: ${truncatedPrompt}`)
    }
    if (data.config?.include_file_content !== false) {
      lines.push('📎 Multimodal enabled')
    }
    return lines
  }

  return (
    <div 
      className={`compact-node agent-node ${selected ? 'selected' : ''}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="compact-handle target"
      />
      
      <div className="compact-node-icon agent">
        <span className="icon-emoji">🤖</span>
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

AgentNode.displayName = 'AgentNode'

export default AgentNode
