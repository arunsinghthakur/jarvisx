import React, { memo, useState } from 'react'
import './NodeStyles.css'

const CommentNode = memo(({ data, selected }) => {
  return (
    <div className={`comment-node ${selected ? 'selected' : ''}`}>
      <div className="comment-node-content">
        {data.config?.text || data.label || 'Double-click to edit...'}
      </div>
    </div>
  )
})

CommentNode.displayName = 'CommentNode'

export default CommentNode
