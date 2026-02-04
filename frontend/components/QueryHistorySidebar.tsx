'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  History, 
  Clock, 
  Search, 
  TrendingUp, 
  X,
  ChevronRight,
  Command
} from 'lucide-react'

interface QueryHistoryItem {
  id: string
  query: string
  created_at: string
  result_summary?: string
}

interface QueryHistorySidebarProps {
  isOpen: boolean
  onClose: () => void
  onSelectQuery: (query: string) => void
}

export function QueryHistorySidebar({ 
  isOpen, 
  onClose, 
  onSelectQuery 
}: QueryHistorySidebarProps) {
  const [queries, setQueries] = useState<QueryHistoryItem[]>([])
  const [popular, setPopular] = useState<{query: string, count: number}[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  // Fetch recent queries
  const fetchQueries = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/history?limit=20')
      if (response.ok) {
        const data = await response.json()
        setQueries(data)
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Fetch popular queries
  const fetchPopular = useCallback(async () => {
    try {
      const response = await fetch('/api/history/popular?limit=5')
      if (response.ok) {
        const data = await response.json()
        setPopular(data)
      }
    } catch (error) {
      console.error('Failed to fetch popular:', error)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchQueries()
      fetchPopular()
    }
  }, [isOpen, fetchQueries, fetchPopular])

  // Format relative time
  const formatTime = (dateStr: string) => {
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

  // Filter queries by search
  const filteredQueries = searchTerm
    ? queries.filter(q => 
        q.query.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : queries

  // Group by date
  const groupedQueries = filteredQueries.reduce((groups, query) => {
    const date = new Date(query.created_at)
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
    groups[group].push(query)
    return groups
  }, {} as Record<string, QueryHistoryItem[]>)

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />
          
          {/* Sidebar */}
          <motion.div
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 h-full w-[360px] bg-surface border-r border-border z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-primary" />
                <h2 className="font-semibold">Query History</h2>
              </div>
              <button 
                onClick={onClose}
                className="p-2 hover:bg-surface-elevated rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-foreground-muted" />
              </button>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-border">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Search history..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-field w-full pl-9 py-2 text-sm"
                />
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {/* Popular Queries */}
              {!searchTerm && popular.length > 0 && (
                <div className="p-4 border-b border-border">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-medium text-foreground-muted uppercase">
                      Popular
                    </span>
                  </div>
                  <div className="space-y-2">
                    {popular.slice(0, 3).map((item, i) => (
                      <button
                        key={i}
                        onClick={() => onSelectQuery(item.query)}
                        className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-surface-elevated transition-colors group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate pr-2">{item.query}</span>
                          <span className="text-xs text-foreground-muted shrink-0">
                            {item.count}×
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Queries */}
              <div className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-primary" />
                  <span className="text-xs font-medium text-foreground-muted uppercase">
                    Recent
                  </span>
                </div>

                {isLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-10 bg-surface animate-pulse rounded-lg" />
                    ))}
                  </div>
                ) : Object.keys(groupedQueries).length === 0 ? (
                  <div className="text-center py-8 text-foreground-muted">
                    <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No queries yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(groupedQueries).map(([group, items]) => (
                      <div key={group}>
                        <span className="text-xs text-foreground-muted px-3">
                          {group}
                        </span>
                        <div className="mt-1 space-y-1">
                          {items.map((query) => (
                            <button
                              key={query.id}
                              onClick={() => onSelectQuery(query.query)}
                              className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-surface-elevated transition-colors group"
                            >
                              <p className="text-sm text-foreground line-clamp-2">
                                {query.query}
                              </p>
                              <div className="flex items-center justify-between mt-1">
                                <span className="text-xs text-foreground-muted">
                                  {formatTime(query.created_at)}
                                </span>
                                <ChevronRight className="w-3 h-3 text-foreground-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border bg-surface/50">
              <div className="flex items-center justify-center gap-2 text-xs text-foreground-muted">
                <kbd className="px-1.5 py-0.5 bg-surface-elevated rounded border border-border">
                  ⌘
                </kbd>
                <kbd className="px-1.5 py-0.5 bg-surface-elevated rounded border border-border">
                  K
                </kbd>
                <span>for command palette</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
