import React, { useState } from 'react'
import { ChevronRightIcon, ChevronDownIcon } from '../common/Icons'

const TraceTree = ({ trace, observations, onSelectObservation, selectedObservationId }) => {
  const [expandedNodes, setExpandedNodes] = useState(new Set(['trace']))
  const [viewMode, setViewMode] = useState('tree')

  const toggleNode = (nodeId) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId)
      } else {
        newSet.add(nodeId)
      }
      return newSet
    })
  }

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatCost = (cost) => {
    if (cost === null || cost === undefined) return null
    return `$${cost.toFixed(6)}`
  }

  const getObservationTypeClass = (type) => {
    const typeMap = {
      'GENERATION': 'generation',
      'SPAN': 'span',
      'EVENT': 'event',
    }
    return typeMap[type?.toUpperCase()] || 'span'
  }

  const calculateTotalStats = () => {
    let totalTokens = 0
    let totalCost = 0
    let promptTokens = 0
    let completionTokens = 0

    observations?.forEach(obs => {
      if (obs.total_tokens) totalTokens += obs.total_tokens
      if (obs.prompt_tokens) promptTokens += obs.prompt_tokens
      if (obs.completion_tokens) completionTokens += obs.completion_tokens
      if (obs.cost) totalCost += obs.cost
    })

    return { totalTokens, totalCost, promptTokens, completionTokens }
  }

  const stats = calculateTotalStats()

  const renderTreeNode = (node, isTrace = false) => {
    const nodeId = isTrace ? 'trace' : node.id
    const isExpanded = expandedNodes.has(nodeId)
    const isSelected = !isTrace && selectedObservationId === node.id
    const hasChildren = isTrace && observations && observations.length > 0
    const typeClass = isTrace ? 'trace' : getObservationTypeClass(node.type)

    return (
      <div key={nodeId} className="tree-node-container">
        <div 
          className={`tree-node ${typeClass} ${isSelected ? 'selected' : ''}`}
          onClick={() => {
            if (isTrace) {
              toggleNode(nodeId)
            } else {
              onSelectObservation?.(node)
            }
          }}
        >
          <div className="node-expand">
            {hasChildren ? (
              isExpanded ? <ChevronDownIcon size={14} /> : <ChevronRightIcon size={14} />
            ) : (
              <span className="node-dot" />
            )}
          </div>
          <div className="node-content">
            <div className="node-header">
              <span className={`node-type-badge ${typeClass}`}>
                {isTrace ? 'TRACE' : node.type || 'SPAN'}
              </span>
              <span className="node-name">
                {isTrace ? trace.name : node.name}
              </span>
            </div>
            <div className="node-meta">
              <span className="node-duration">
                {formatDuration(isTrace ? trace.duration_ms : node.duration_ms)}
              </span>
              {!isTrace && node.model && (
                <span className="node-model">{node.model}</span>
              )}
              {!isTrace && node.total_tokens && (
                <span className="node-tokens">
                  {node.prompt_tokens?.toLocaleString() || 0} → {node.completion_tokens?.toLocaleString() || 0} ({node.total_tokens?.toLocaleString()})
                </span>
              )}
              {!isTrace && node.cost && (
                <span className="node-cost">{formatCost(node.cost)}</span>
              )}
            </div>
          </div>
        </div>
        {hasChildren && isExpanded && (
          <div className="tree-children">
            {observations.map(obs => renderTreeNode(obs, false))}
          </div>
        )}
      </div>
    )
  }

  const renderTimelineNode = (node, index) => {
    const isSelected = selectedObservationId === node.id
    const typeClass = getObservationTypeClass(node.type)
    
    return (
      <div 
        key={node.id} 
        className={`timeline-node ${typeClass} ${isSelected ? 'selected' : ''}`}
        onClick={() => onSelectObservation?.(node)}
      >
        <div className="timeline-marker">
          <div className="timeline-line" />
          <div className={`timeline-dot ${typeClass}`} />
        </div>
        <div className="timeline-content">
          <div className="timeline-header">
            <span className={`node-type-badge ${typeClass}`}>
              {node.type || 'SPAN'}
            </span>
            <span className="timeline-name">{node.name}</span>
            <span className="timeline-duration">{formatDuration(node.duration_ms)}</span>
          </div>
          {node.model && (
            <div className="timeline-model">
              <span className="model-badge">{node.model}</span>
              {node.total_tokens && (
                <span className="token-info">
                  {node.prompt_tokens?.toLocaleString() || 0} → {node.completion_tokens?.toLocaleString() || 0}
                </span>
              )}
              {node.cost && <span className="cost-info">{formatCost(node.cost)}</span>}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="trace-tree">
      <div className="tree-header">
        <div className="tree-stats">
          <div className="stat-item">
            <span className="stat-label">Duration</span>
            <span className="stat-value">{formatDuration(trace?.duration_ms)}</span>
          </div>
          {stats.totalTokens > 0 && (
            <div className="stat-item">
              <span className="stat-label">Tokens</span>
              <span className="stat-value">
                {stats.promptTokens.toLocaleString()} → {stats.completionTokens.toLocaleString()} 
                <span className="stat-total">({stats.totalTokens.toLocaleString()})</span>
              </span>
            </div>
          )}
          {stats.totalCost > 0 && (
            <div className="stat-item">
              <span className="stat-label">Cost</span>
              <span className="stat-value cost">{formatCost(stats.totalCost)}</span>
            </div>
          )}
        </div>
        <div className="tree-view-toggle">
          <button 
            className={`view-btn ${viewMode === 'tree' ? 'active' : ''}`}
            onClick={() => setViewMode('tree')}
            title="Tree View"
          >
            Tree
          </button>
          <button 
            className={`view-btn ${viewMode === 'timeline' ? 'active' : ''}`}
            onClick={() => setViewMode('timeline')}
            title="Timeline View"
          >
            Timeline
          </button>
        </div>
      </div>
      
      <div className="tree-content">
        {viewMode === 'tree' ? (
          <div className="tree-view">
            {trace && renderTreeNode(trace, true)}
          </div>
        ) : (
          <div className="timeline-view">
            <div className="timeline-root">
              <div className={`timeline-trace-header ${trace?.status || 'success'}`}>
                <span className="node-type-badge trace">TRACE</span>
                <span className="trace-name">{trace?.name}</span>
                <span className="trace-duration">{formatDuration(trace?.duration_ms)}</span>
              </div>
            </div>
            <div className="timeline-observations">
              {observations?.map((obs, index) => renderTimelineNode(obs, index))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default TraceTree
