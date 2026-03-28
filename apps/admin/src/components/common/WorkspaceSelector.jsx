import React from 'react'
import './WorkspaceSelector.css'

const WorkspaceSelector = ({ 
  workspaces = [], 
  selectedId, 
  onChange, 
  label = 'Workspace',
  placeholder = 'Select Workspace',
  required = false,
  disabled = false,
  className = ''
}) => {
  return (
    <div className={`workspace-selector ${className}`}>
      <label className="workspace-selector-label">
        {label}
        {required && <span className="required">*</span>}
      </label>
      <select 
        className="workspace-selector-select"
        value={selectedId || ''} 
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {workspaces.map(ws => (
          <option key={ws.id} value={ws.id}>{ws.name}</option>
        ))}
      </select>
    </div>
  )
}

export default WorkspaceSelector
