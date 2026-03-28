import React, { useState } from 'react'
import './Agents.css'
import AddAgentModal from './AddAgentModal'
import EditAgentModal from './EditAgentModal'
import ViewAgentModal from './ViewAgentModal'
import { isCoreAgent } from '../../constants'
import { usePermissions } from '../../hooks'
import { ViewIcon, EditIcon, TrashIcon } from '../common'

const AgentsList = ({
  agents,
  loading,
  onCreateAgent,
  onUpdateAgent,
  onDeleteAgent,
  newAgent,
  setNewAgent,
  showCreateModal,
  setShowCreateModal,
  createLoading,
  availableMcps = [],
  availableAgents = [],
  organizationId,
}) => {
  const { agents: agentPerms } = usePermissions()
  const [editingAgent, setEditingAgent] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [viewingAgent, setViewingAgent] = useState(null)
  const [showViewModal, setShowViewModal] = useState(false)

  const handleView = (agent) => {
    setViewingAgent(agent)
    setShowViewModal(true)
  }

  const handleEdit = (agent) => {
    setEditingAgent(agent)
    setShowEditModal(true)
  }

  const handleDelete = async (agent) => {
    if (!window.confirm(`Are you sure you want to delete agent "${agent.name}"? This action cannot be undone.`)) {
      return
    }
    await onDeleteAgent(agent.id)
  }

  return (
    <div className="section-content">
      <div className="section-header">
        <h2>Agents</h2>
        {agentPerms.canCreate && (
          <button
            className="btn-primary"
            onClick={() => setShowCreateModal(true)}
            disabled={loading}
          >
            + Add Agent
          </button>
        )}
      </div>

      <div className="info-banner">
        <p>💡 Agents are available to all workspaces in your organization. System agents are available globally.</p>
      </div>

      <AddAgentModal
        visible={showCreateModal}
        newAgent={newAgent}
        setNewAgent={setNewAgent}
        onCreate={onCreateAgent}
        onClose={() => setShowCreateModal(false)}
        loading={createLoading}
        availableMcps={availableMcps}
        organizationId={organizationId}
      />

      {viewingAgent && (
        <ViewAgentModal
          visible={showViewModal}
          agent={viewingAgent}
          onClose={() => {
            setShowViewModal(false)
            setViewingAgent(null)
          }}
          availableMcps={availableMcps}
          availableAgents={availableAgents.length > 0 ? availableAgents : agents}
        />
      )}

      {editingAgent && (
        <EditAgentModal
          visible={showEditModal}
          agent={editingAgent}
          onUpdate={async (updates) => {
            await onUpdateAgent(editingAgent.id, updates)
            setShowEditModal(false)
            setEditingAgent(null)
          }}
          onClose={() => {
            setShowEditModal(false)
            setEditingAgent(null)
          }}
          loading={createLoading}
          availableMcps={availableMcps}
          availableAgents={availableAgents.length > 0 ? availableAgents : agents}
          organizationId={organizationId}
        />
      )}

      {loading ? (
        <div className="loading-state">Loading agents...</div>
      ) : (
        <div className="list-container">
          {agents.length === 0 ? (
            <div className="empty-state">
              <p>No agents found. Add your first agent to get started.</p>
            </div>
          ) : (
            <div className="items-list">
              {agents.map(agent => {
                const isCore = isCoreAgent(agent)

                return (
                  <div key={agent.id} className="list-item">
                    <div className="list-item-content">
                      <div className="list-item-header">
                        <h3>{agent.name}</h3>
                        <div className="list-item-badges">
                          {agent.is_system_agent && (
                            <span className="badge badge-system">System Agent</span>
                          )}
                          {agent.is_custom_agent && !agent.is_dynamic_agent && (
                            <span className="badge badge-custom">External</span>
                          )}
                          {agent.is_dynamic_agent && (
                            <span className="badge badge-dynamic">Dynamic</span>
                          )}
                          {isCore && (
                            <span className="badge badge-core">Core</span>
                          )}
                        </div>
                      </div>
                      <div className="list-item-meta">
                        <span className="meta-item">ID: {agent.id}</span>
                        {agent.is_dynamic_agent ? (
                          agent.llm_config ? (
                            <span className="meta-item">LLM: {agent.llm_config.name} ({agent.llm_config.provider}/{agent.llm_config.model_name})</span>
                          ) : (
                            <span className="meta-item" style={{ color: '#dc3545' }}>LLM: Not configured</span>
                          )
                        ) : agent.default_url && (
                          <span className="meta-item">URL: {agent.default_url}</span>
                        )}
                      </div>
                      {agent.description && (
                        <p className="list-item-description">{agent.description}</p>
                      )}
                    </div>
                    <div className="list-item-actions">
                      <button
                        className="btn-icon"
                        onClick={() => handleView(agent)}
                        title="View details"
                      >
                        <ViewIcon size={16} />
                      </button>
                      {agentPerms.canEdit && agent.can_edit !== false && (
                        <button
                          className="btn-icon"
                          onClick={() => handleEdit(agent)}
                          title="Edit"
                        >
                          <EditIcon size={16} />
                        </button>
                      )}
                      {agentPerms.canDelete && agent.can_delete && (
                        <button
                          className="btn-icon btn-danger"
                          onClick={() => handleDelete(agent)}
                          title="Delete"
                        >
                          <TrashIcon size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default AgentsList
