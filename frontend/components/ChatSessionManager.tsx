'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  MessageSquare, 
  Plus, 
  Clock, 
  MoreHorizontal,
  Trash2,
  Archive,
  Edit3,
  ChevronRight,
  X
} from 'lucide-react'

interface ChatSession {
  id: string
  title: string
  summary?: string
  status: 'active' | 'archived'
  message_count: number
  created_at: string
  updated_at: string
  last_message_at?: string
}

interface ChatSessionManagerProps {
  currentSessionId: string | null
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  onSessionRename?: (sessionId: string, newTitle: string) => void
  onSessionArchive?: (sessionId: string) => void
  onSessionDelete?: (sessionId: string) => void
}

export function ChatSessionManager({
  currentSessionId,
  onSessionSelect,
  onNewSession,
  onSessionRename,
  onSessionArchive,
  onSessionDelete
}: ChatSessionManagerProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    fetchSessions()
  }, [showArchived])

  const fetchSessions = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/chat/sessions?include_archived=${showArchived}&limit=50`)
      if (response.ok) {
        const data = await response.json()
        setSessions(data)
      }
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRename = async (sessionId: string) => {
    if (!editTitle.trim()) return
    
    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}/title`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle })
      })
      
      if (response.ok) {
        setSessions(prev => prev.map(s => 
          s.id === sessionId ? { ...s, title: editTitle } : s
        ))
        onSessionRename?.(sessionId, editTitle)
      }
    } catch (error) {
      console.error('Failed to rename:', error)
    }
    
    setEditingId(null)
    setEditTitle('')
  }

  const handleArchive = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}/archive`, {
        method: 'POST'
      })
      
      if (response.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId))
        onSessionArchive?.(sessionId)
      }
    } catch (error) {
      console.error('Failed to archive:', error)
    }
  }

  const handleDelete = async (sessionId: string) => {
    if (!confirm('Are you sure? This cannot be undone.')) return
    
    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId))
        onSessionDelete?.(sessionId)
      }
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  // Group sessions by date
  const groupedSessions = sessions.reduce((groups, session) => {
    const date = new Date(session.created_at)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    
    let group = 'Earlier'
    if (date.toDateString() === today.toDateString()) {
      group = 'Today'
    } else if (date.toDateString() === yesterday.toDateString()) {
      group = 'Yesterday'
    } else if (date > new Date(today.getTime() - 7 * 86400000)) {
      group = 'This Week'
    }
    
    if (!groups[group]) groups[group] = []
    groups[group].push(session)
    return groups
  }, {} as Record<string, ChatSession[]>)

  return (
    <div className="w-64 h-full flex flex-col glass-card border-r border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h3 className="font-semibold text-sm">Chat History</h3>
        <button
          onClick={onNewSession}
          className="p-2 hover:bg-surface rounded-lg transition-colors"
          title="New Chat"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Toggle Archived */}
      <div className="px-4 py-2 border-b border-border">
        <button
          onClick={() => setShowArchived(!showArchived)}
          className="text-xs text-foreground-muted hover:text-foreground transition-colors"
        >
          {showArchived ? 'Hide archived' : 'Show archived'}
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-12 bg-surface animate-pulse rounded-lg" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-4 text-center">
            <MessageSquare className="w-8 h-8 mx-auto text-foreground-muted mb-2" />
            <p className="text-sm text-foreground-muted">No chats yet</p>
          </div>
        ) : (
          <div className="p-2 space-y-4">
            {Object.entries(groupedSessions).map(([group, groupSessions]) => (
              <div key={group}>
                <span className="text-xs text-foreground-muted px-2">{group}</span>
                <div className="mt-1 space-y-1">
                  {groupSessions.map(session => (
                    <div
                      key={session.id}
                      className={`group relative rounded-lg transition-colors ${
                        currentSessionId === session.id
                          ? 'bg-primary/10 border border-primary/20'
                          : 'hover:bg-surface'
                      }`}
                    >
                      {editingId === session.id ? (
                        <div className="p-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            onBlur={() => handleRename(session.id)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleRename(session.id)
                              if (e.key === 'Escape') {
                                setEditingId(null)
                                setEditTitle('')
                              }
                            }}
                            className="input-field w-full text-sm py-1"
                            autoFocus
                          />
                        </div>
                      ) : (
                        <button
                          onClick={() => onSessionSelect(session.id)}
                          className="w-full text-left p-2"
                        >
                          <div className="flex items-start gap-2">
                            <MessageSquare className="w-4 h-4 text-foreground-muted mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm truncate">{session.title}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-xs text-foreground-muted">
                                  {session.message_count} messages
                                </span>
                                <span className="text-xs text-foreground-muted">
                                  {formatTime(session.last_message_at)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </button>
                      )}

                      {/* Actions */}
                      {editingId !== session.id && (
                        <div className="absolute right-1 top-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <div className="relative">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setEditingId(session.id)
                                setEditTitle(session.title)
                              }}
                              className="p-1 hover:bg-surface-elevated rounded"
                            >
                              <MoreHorizontal className="w-3 h-3" />
                            </button>
                            
                            {/* Dropdown would go here */}
                            <div className="absolute right-0 top-full mt-1 w-32 bg-surface border border-border rounded-lg shadow-lg hidden group-hover:block z-10">
                              <button
                                onClick={() => {
                                  setEditingId(session.id)
                                  setEditTitle(session.title)
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-elevated"
                              >
                                <Edit3 className="w-3 h-3" />
                                Rename
                              </button>
                              <button
                                onClick={() => handleArchive(session.id)}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-elevated"
                              >
                                <Archive className="w-3 h-3" />
                                Archive
                              </button>
                              <button
                                onClick={() => handleDelete(session.id)}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-surface-elevated"
                              >
                                <Trash2 className="w-3 h-3" />
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
