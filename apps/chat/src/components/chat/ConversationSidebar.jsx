import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  listConversations,
  createConversation,
  updateConversation,
  deleteConversation,
  getTimeGroupLabel,
  formatConversationDate,
} from '../../services'
import './ConversationSidebar.css'

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function SidebarToggleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  )
}

function ConversationItem({ 
  conversation, 
  isActive, 
  onClick, 
  onRename, 
  onDelete 
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(conversation.title)
  const [showActions, setShowActions] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleSave = useCallback(() => {
    if (editTitle.trim() && editTitle !== conversation.title) {
      onRename(conversation.id, editTitle.trim())
    }
    setIsEditing(false)
  }, [editTitle, conversation.id, conversation.title, onRename])

  const handleCancel = useCallback(() => {
    setEditTitle(conversation.title)
    setIsEditing(false)
  }, [conversation.title])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }, [handleSave, handleCancel])

  const handleDelete = useCallback((e) => {
    e.stopPropagation()
    if (window.confirm('Delete this conversation?')) {
      onDelete(conversation.id)
    }
  }, [conversation.id, onDelete])

  return (
    <div
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={() => !isEditing && onClick(conversation)}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="conversation-icon">
        <ChatIcon />
      </div>
      
      {isEditing ? (
        <div className="conversation-edit">
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSave}
            className="conversation-edit-input"
          />
          <button className="edit-action-btn save" onClick={handleSave}>
            <CheckIcon />
          </button>
          <button className="edit-action-btn cancel" onClick={handleCancel}>
            <CloseIcon />
          </button>
        </div>
      ) : (
        <>
          <div className="conversation-info">
            <span className="conversation-title">{conversation.title}</span>
          </div>
          
          {showActions && (
            <div className="conversation-actions">
              <button
                className="action-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  setIsEditing(true)
                }}
                title="Rename"
              >
                <EditIcon />
              </button>
              <button
                className="action-btn delete"
                onClick={handleDelete}
                title="Delete"
              >
                <TrashIcon />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function ConversationSidebar({
  workflowId,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isOpen,
  onToggle,
}) {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)

  const loadConversations = useCallback(async (reset = false) => {
    if (!workflowId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const newOffset = reset ? 0 : offset
      const response = await listConversations(workflowId, {
        limit: 30,
        offset: newOffset,
      })
      
      if (reset) {
        setGroups(response.groups || [])
        setOffset(30)
      } else {
        setGroups(prev => {
          const merged = [...prev]
          for (const newGroup of response.groups || []) {
            const existingIndex = merged.findIndex(g => g.group === newGroup.group)
            if (existingIndex >= 0) {
              const existingIds = new Set(merged[existingIndex].conversations.map(c => c.id))
              const newConvs = newGroup.conversations.filter(c => !existingIds.has(c.id))
              merged[existingIndex].conversations.push(...newConvs)
            } else {
              merged.push(newGroup)
            }
          }
          return merged
        })
        setOffset(newOffset + 30)
      }
      
      setHasMore(response.has_more)
    } catch (err) {
      console.error('Failed to load conversations:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [workflowId, offset])

  useEffect(() => {
    loadConversations(true)
  }, [workflowId])

  const handleNewChat = useCallback(async () => {
    onNewConversation()
  }, [onNewConversation])

  const handleRename = useCallback(async (conversationId, newTitle) => {
    try {
      await updateConversation(workflowId, conversationId, { title: newTitle })
      setGroups(prev => prev.map(group => ({
        ...group,
        conversations: group.conversations.map(conv =>
          conv.id === conversationId ? { ...conv, title: newTitle } : conv
        )
      })))
    } catch (err) {
      console.error('Failed to rename conversation:', err)
    }
  }, [workflowId])

  const handleDelete = useCallback(async (conversationId) => {
    try {
      await deleteConversation(workflowId, conversationId)
      setGroups(prev => prev.map(group => ({
        ...group,
        conversations: group.conversations.filter(conv => conv.id !== conversationId)
      })).filter(group => group.conversations.length > 0))
      
      if (conversationId === currentConversationId) {
        onNewConversation()
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err)
    }
  }, [workflowId, currentConversationId, onNewConversation])

  const refreshConversations = useCallback(() => {
    loadConversations(true)
  }, [loadConversations])

  useEffect(() => {
    window.refreshConversationSidebar = refreshConversations
    return () => {
      delete window.refreshConversationSidebar
    }
  }, [refreshConversations])

  if (!isOpen) {
    return (
      <button className="sidebar-toggle-btn collapsed" onClick={onToggle} title="Open sidebar">
        <SidebarToggleIcon />
      </button>
    )
  }

  return (
    <div className="conversation-sidebar">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <PlusIcon />
          <span>New chat</span>
        </button>
        <button className="sidebar-toggle-btn" onClick={onToggle} title="Close sidebar">
          <SidebarToggleIcon />
        </button>
      </div>

      <div className="sidebar-content">
        {error && (
          <div className="sidebar-error">
            {error}
            <button onClick={() => loadConversations(true)}>Retry</button>
          </div>
        )}

        {groups.map((group) => (
          <div key={group.group} className="conversation-group">
            <div className="group-header">
              {getTimeGroupLabel(group.group)}
            </div>
            <div className="group-conversations">
              {group.conversations.map((conversation) => (
                <ConversationItem
                  key={conversation.id}
                  conversation={conversation}
                  isActive={conversation.id === currentConversationId}
                  onClick={onSelectConversation}
                  onRename={handleRename}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </div>
        ))}

        {groups.length === 0 && !loading && !error && (
          <div className="sidebar-empty">
            <ChatIcon />
            <p>No conversations yet</p>
            <p className="sidebar-empty-hint">Start a new chat to begin</p>
          </div>
        )}

        {hasMore && (
          <button
            className="load-more-btn"
            onClick={() => loadConversations(false)}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Load more'}
          </button>
        )}

        {loading && groups.length === 0 && (
          <div className="sidebar-loading">
            <div className="loading-spinner small" />
          </div>
        )}
      </div>
    </div>
  )
}
