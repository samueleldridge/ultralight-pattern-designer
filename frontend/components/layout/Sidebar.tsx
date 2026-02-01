'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  MessageSquare,
  History,
  Database,
  Settings,
  Users,
  Plus,
  Search,
  Clock,
  Sparkles,
  BarChart3,
  Trash2,
  Edit3,
  Pin,
  X,
  MoreHorizontal,
} from 'lucide-react'
import { format, isToday, isYesterday, subDays } from 'date-fns'
import { toast } from 'sonner'

/**
 * Types
 */
interface Conversation {
  id: string
  title: string
  timestamp: Date
  pinned?: boolean
  messageCount: number
}

interface NavItem {
  id: string
  label: string
  icon: React.ElementType
  badge?: number
}

interface SidebarProps {
  onConversationSelect?: (id: string) => void
  onNewChat?: () => void
}

/**
 * Mock Data
 */
const mockConversations: Conversation[] = [
  { id: '1', title: 'Q4 Revenue Analysis', timestamp: new Date(), pinned: true, messageCount: 12 },
  { id: '2', title: 'Customer churn prediction', timestamp: new Date(Date.now() - 1000 * 60 * 30), pinned: false, messageCount: 8 },
  { id: '3', title: 'Top products this month', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), pinned: false, messageCount: 5 },
  { id: '4', title: 'Marketing campaign ROI', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), pinned: false, messageCount: 15 },
  { id: '5', title: 'Sales team performance', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48), pinned: false, messageCount: 20 },
  { id: '6', title: 'Inventory forecast', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 72), pinned: false, messageCount: 6 },
]

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'queries', label: 'Saved Queries', icon: History, badge: 3 },
  { id: 'data', label: 'Data Sources', icon: Database },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'settings', label: 'Settings', icon: Settings },
]

/**
 * Conversation Group Type
 */
type ConversationGroup = {
  title: string
  conversations: Conversation[]
}

/**
 * Group conversations by date
 */
function groupConversations(conversations: Conversation[]): ConversationGroup[] {
  const groups: { [key: string]: Conversation[] } = {
    'Pinned': [],
    'Today': [],
    'Yesterday': [],
    'Last 7 Days': [],
    'Older': [],
  }

  conversations.forEach(conv => {
    // Pinned conversations go first
    if (conv.pinned) {
      groups['Pinned'].push(conv)
      return
    }

    const convDate = new Date(conv.timestamp)
    
    if (isToday(convDate)) {
      groups['Today'].push(conv)
    } else if (isYesterday(convDate)) {
      groups['Yesterday'].push(conv)
    } else if (convDate > subDays(new Date(), 7)) {
      groups['Last 7 Days'].push(conv)
    } else {
      groups['Older'].push(conv)
    }
  })

  // Return only non-empty groups in order
  const order = ['Pinned', 'Today', 'Yesterday', 'Last 7 Days', 'Older']
  return order
    .map(title => ({ title, conversations: groups[title] }))
    .filter(g => g.conversations.length > 0)
}

/**
 * Sidebar Component
 * 
 * Edge-style hover expand with 0.5s delay (Linear.app inspired)
 * Features conversation history with date grouping and search
 */
export function Sidebar({ onConversationSelect, onNewChat }: SidebarProps) {
  // State
  const [isExpanded, setIsExpanded] = useState(false)
  const [isHovering, setIsHovering] = useState(false)
  const [activeItem, setActiveItem] = useState('dashboard')
  const [activeConversation, setActiveConversation] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const [hoveredConversation, setHoveredConversation] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>(mockConversations)

  // Hover delay timer
  useEffect(() => {
    let timeout: NodeJS.Timeout

    if (isHovering) {
      // Expand after 300ms delay
      timeout = setTimeout(() => setIsExpanded(true), 300)
    } else {
      // Collapse after 500ms delay
      timeout = setTimeout(() => setIsExpanded(false), 500)
    }

    return () => clearTimeout(timeout)
  }, [isHovering])

  // Handle conversation selection
  const handleConversationClick = useCallback((id: string) => {
    setActiveConversation(id)
    onConversationSelect?.(id)
  }, [onConversationSelect])

  // Handle new chat
  const handleNewChat = useCallback(() => {
    setActiveConversation(null)
    onNewChat?.()
    toast.success('New conversation started')
  }, [onNewChat])

  // Handle pin/unpin
  const handlePin = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setConversations(prev => prev.map(c => 
      c.id === id ? { ...c, pinned: !c.pinned } : c
    ))
    const conv = conversations.find(c => c.id === id)
    toast.success(conv?.pinned ? 'Conversation unpinned' : 'Conversation pinned')
  }, [conversations])

  // Handle delete
  const handleDelete = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setConversations(prev => prev.filter(c => c.id !== id))
    if (activeConversation === id) {
      setActiveConversation(null)
    }
    toast.success('Conversation deleted')
  }, [activeConversation])

  // Handle rename
  const handleRename = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    toast.info('Rename feature coming soon')
  }, [])

  // Filter conversations
  const filteredConversations = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const groupedConversations = groupConversations(filteredConversations)

  return (
    <motion.aside
      initial={false}
      animate={{ width: isExpanded ? 280 : 72 }}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      className="h-screen bg-background-secondary border-r border-border flex flex-col relative z-50"
      style={{ transition: 'width 0.3s cubic-bezier(0.23, 1, 0.32, 1)' }}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-border flex-shrink-0">
        <motion.div 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-secondary to-accent flex items-center justify-center shadow-lg shadow-primary/20 flex-shrink-0"
        >
          <Sparkles className="w-5 h-5 text-white" />
        </motion.div>
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="ml-3 overflow-hidden"
            >
              <h1 className="font-bold text-lg gradient-text whitespace-nowrap">Nexus AI</h1>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* New Chat Button */}
      <div className="p-3 flex-shrink-0">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-primary text-primary-foreground rounded-xl font-medium shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all"
        >
          <Plus className="w-5 h-5 flex-shrink-0" />
          <AnimatePresence>
            {isExpanded && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="whitespace-nowrap overflow-hidden"
              >
                New Chat
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Navigation */}
      <nav className="px-2 space-y-0.5 flex-shrink-0">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeItem === item.id
          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveItem(item.id)
                toast.info(`${item.label} coming soon`)
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                isActive
                  ? 'bg-primary-subtle text-primary'
                  : 'text-foreground-muted hover:text-foreground hover:bg-surface'
              }`}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${isActive && 'text-primary'}`} />
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="flex items-center justify-between flex-1 min-w-0"
                  >
                    <span className="font-medium text-sm whitespace-nowrap">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
          )
        })}
      </nav>

      {/* Divider */}
      <div className="mx-4 my-3 h-px bg-border flex-shrink-0" />

      {/* Conversation History */}
      <AnimatePresence mode="wait">
        {isExpanded ? (
          <motion.div
            key="expanded"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex-1 flex flex-col min-h-0 overflow-hidden"
          >
            {/* Search */}
            <div className="px-3 mb-3 flex-shrink-0">
              <div className={`relative transition-all duration-200 ${isSearchFocused ? 'ring-2 ring-primary/30 rounded-xl' : ''}`}>
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-subtle" />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => setIsSearchFocused(true)}
                  onBlur={() => setIsSearchFocused(false)}
                  className="w-full bg-surface border border-border rounded-xl pl-9 pr-8 py-2 text-sm text-foreground placeholder:text-foreground-subtle focus:outline-none focus:border-primary/50 transition-colors"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-surface-hover rounded transition-colors"
                  >
                    <X className="w-3 h-3 text-foreground-subtle" />
                  </button>
                )}
              </div>
            </div>

            {/* Conversations List */}
            <div className="flex-1 overflow-y-auto px-2 space-y-4 min-h-0 scrollbar-hide">
              {groupedConversations.length === 0 ? (
                <div className="text-center py-8 text-foreground-subtle text-sm">
                  No conversations found
                </div>
              ) : (
                groupedConversations.map((group) => (
                  <div key={group.title} className="space-y-1">
                    <h3 className="px-3 text-[10px] font-semibold text-foreground-subtle uppercase tracking-wider">
                      {group.title}
                    </h3>
                    {group.conversations.map((conversation) => (
                      <motion.button
                        key={conversation.id}
                        onClick={() => handleConversationClick(conversation.id)}
                        onMouseEnter={() => setHoveredConversation(conversation.id)}
                        onMouseLeave={() => setHoveredConversation(null)}
                        className={`w-full text-left p-3 rounded-xl transition-all duration-200 group relative ${
                          activeConversation === conversation.id
                            ? 'bg-surface border border-border-strong'
                            : 'hover:bg-surface'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                            activeConversation === conversation.id
                              ? 'bg-primary/20 text-primary'
                              : 'bg-surface-elevated text-foreground-muted'
                          }`}>
                            <MessageSquare className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0 pr-8">
                            <div className="flex items-center gap-2">
                              <p className={`text-sm font-medium truncate transition-colors ${
                                activeConversation === conversation.id 
                                  ? 'text-foreground' 
                                  : 'text-foreground-muted group-hover:text-foreground'
                              }`}>
                                {conversation.title}
                              </p>
                              {conversation.pinned && (
                                <Pin className="w-3 h-3 text-primary flex-shrink-0 fill-primary" />
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <Clock className="w-3 h-3 text-foreground-subtle" />
                              <span className="text-[10px] text-foreground-subtle">
                                {format(conversation.timestamp, 'h:mm a')}
                              </span>
                              <span className="text-[10px] text-foreground-subtle">
                                • {conversation.messageCount} msgs
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Quick Actions on Hover */}
                        <AnimatePresence>
                          {hoveredConversation === conversation.id && (
                            <motion.div
                              initial={{ opacity: 0, y: 5 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: 5 }}
                              className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 bg-surface-elevated rounded-lg p-1 shadow-lg border border-border"
                            >
                              <button
                                onClick={(e) => handlePin(e, conversation.id)}
                                className="p-1.5 hover:bg-surface-hover rounded-md text-foreground-muted hover:text-foreground transition-colors"
                                title={conversation.pinned ? "Unpin" : "Pin"}
                              >
                                <Pin className={`w-3 h-3 ${conversation.pinned ? 'fill-primary text-primary' : ''}`} />
                              </button>
                              <button
                                onClick={(e) => handleRename(e, conversation.id)}
                                className="p-1.5 hover:bg-surface-hover rounded-md text-foreground-muted hover:text-foreground transition-colors"
                                title="Rename"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => handleDelete(e, conversation.id)}
                                className="p-1.5 hover:bg-error/10 rounded-md text-foreground-muted hover:text-error transition-colors"
                                title="Delete"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.button>
                    ))}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="collapsed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex-1 flex flex-col items-center gap-2 px-2 overflow-hidden"
          >
            {/* Recent conversations as icons */}
            {conversations
              .filter(c => c.pinned || conversations.indexOf(c) < 3)
              .map((conversation) => (
                <motion.button
                  key={conversation.id}
                  onClick={() => handleConversationClick(conversation.id)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                    activeConversation === conversation.id
                      ? 'bg-primary/20 text-primary'
                      : 'bg-surface text-foreground-muted hover:text-foreground'
                  }`}
                  title={conversation.title}
                >
                  <MessageSquare className="w-4 h-4" />
                </motion.button>
              ))}
            
            {conversations.length > 3 && (
              <>
                <div className="w-8 h-px bg-border my-1" />
                <button 
                  onClick={() => setIsHovering(true)}
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-foreground-subtle hover:text-foreground hover:bg-surface transition-colors"
                  title="More conversations"
                >
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed indicator hint */}
      {!isExpanded && (
        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-border rounded-l-full opacity-0 hover:opacity-100 transition-opacity" />
      )}
    </motion.aside>
  )
}

export default Sidebar
