import React, { memo } from 'react'
import './NodeStyles.css'

const GroupNode = memo(({ data, selected }) => {
  return (
    <div className={`group-node ${selected ? 'selected' : ''}`}>
      <div className="group-node-header">
        {data.label || 'Group'}
      </div>
    </div>
  )
})

GroupNode.displayName = 'GroupNode'

export default GroupNode
