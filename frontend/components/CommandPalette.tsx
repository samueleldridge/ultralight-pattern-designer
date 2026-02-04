'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Clock, 
  TrendingUp, 
  MessageSquare,
  Sparkles,
  ChevronRight
} from 'lucide-react'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onSelectQuery: (query: string) => void
}

interface SearchResult {
  id: string
  query: string
  type: 'history' | 'popular' | 'suggestion'
  created_at?: string
  count?: number
}

export function CommandPalette({ 
  isOpen, 
  onClose, 
  onSelectQuery 
}: CommandPaletteProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)

  // Fetch search results
  const searchQueries = useCallback(async (term: string) => {
    if (!term.trim()) {
      // Show default results - recent and popular
      await fetchDefaultResults()
      return
    }

    setIsLoading(true)
    try {
      // Search history
      const historyRes = await fetch(`/api/history/search?q=${encodeURIComponent(term)}&limit=5`)
      const historyData = historyRes.ok ? await historyRes.json() : { results: [] }
      
      // Get suggestions
      const suggestionsRes = await fetch(`/api/history/suggestions?query=${encodeURIComponent(term)}&limit=3`)
      const suggestionsData = suggestionsRes.ok ? await suggestionsRes.json() : { suggestions: [] }

      const combined: SearchResult[] = [
        ...historyData.results.map((r: any) => ({
          id: r.id,
          query: r.query,
          type: 'history' as const,
          created_at: r.created_at
        })),
        ...suggestionsData.suggestions.map((s: any, i: number) => ({
          id: `sugg-${i}`,
          query: s.query,
          type: 'suggestion' as const
        }))
      ]

      // Remove duplicates
      const unique = combined.filter((v, i, a) => 
        a.findIndex(t => t.query === v.query) === i
      )

      setResults(unique.slice(0, 8))
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Fetch default results
  const fetchDefaultResults = useCallback(async () => {
    try {
      const [historyRes, popularRes] = await Promise.all([
        fetch('/api/history?limit=5'),
        fetch('/api/history/popular?limit=3')
      ])

      const history = historyRes.ok ? await historyRes.json() : []
      const popular = popularRes.ok ? await popularRes.json() : []

      const combined: SearchResult[] = [
        ...history.slice(0, 5).map((h: any) => ({
          id: h.id,
          query: h.query,
          type: 'history' as const,
          created_at: h.created_at
        })),
        ...popular.slice(0, 3).map((p: any, i: number) => ({
          id: `pop-${i}`,
          query: p.query,
          type: 'popular' as const,
          count: p.count
        }))
      ]

      setResults(combined)
    } catch (error) {
      console.error('Failed to fetch defaults:', error)
    }
  }, [])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      searchQueries(searchTerm)
    }, 150)
    return () => clearTimeout(timer)
  }, [searchTerm, searchQueries])

  // Reset when opening
  useEffect(() => {
    if (isOpen) {
      setSearchTerm('')
      setSelectedIndex(0)
      fetchDefaultResults()
    }
  }, [isOpen, fetchDefaultResults])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(i => (i + 1) % results.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(i => (i - 1 + results.length) % results.length)
      } else if (e.key === 'Enter' && results[selectedIndex]) {
        e.preventDefault()
        onSelectQuery(results[selectedIndex].query)
        onClose()
      } else if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, results, selectedIndex, onSelectQuery, onClose])

  // Format time
  const formatTime = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  // Get icon for result type
  const getIcon = (type: string) => {
    switch (type) {
      case 'history': return <Clock className="w-4 h-4 text-foreground-muted" />
      case 'popular': return <TrendingUp className="w-4 h-4 text-emerald-400" />
      case 'suggestion': return <Sparkles className="w-4 h-4 text-primary" />
      default: return <MessageSquare className="w-4 h-4 text-foreground-muted" />
    }
  }

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
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Command Palette */}
          <div className="fixed inset-0 flex items-start justify-center pt-[20vh] z-50 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              className="w-full max-w-[640px] glass-card rounded-xl overflow-hidden shadow-2xl pointer-events-auto"
            >
              {/* Search Input */}
              <div className="flex items-center gap-3 p-4 border-b border-border">
                <Search className="w-5 h-5 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Search queries or ask something new..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-foreground-muted"
                  autoFocus
                />
                <kbd className="px-2 py-1 text-xs bg-surface rounded border border-border text-foreground-muted">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <div className="max-h-[400px] overflow-y-auto py-2">
                {isLoading ? (
                  <div className="p-8 text-center text-foreground-muted">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-sm">Searching...</p>
                  </div>
                ) : results.length === 0 ? (
                  <div className="p-8 text-center text-foreground-muted">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No results found</p>
                    <p className="text-xs mt-1">Try a different search term</p>
                  </div>
                ) : (
                  <div className="px-2">
                    {searchTerm ? (
                      <div className="px-3 py-1.5 text-xs text-foreground-muted uppercase">
                        Search Results
                      </div>
                    ) : (
                      <div className="px-3 py-1.5 text-xs text-foreground-muted uppercase">
                        Recent & Popular
                      </div>
                    )}
                    
                    {results.map((result, index) => (
                      <button
                        key={result.id}
                        onClick={() => {
                          onSelectQuery(result.query)
                          onClose()
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                          index === selectedIndex
                            ? 'bg-primary/10 text-foreground'
                            : 'text-foreground-muted hover:bg-surface'
                        }`}
                      >
                        {getIcon(result.type)}
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm truncate ${
                            index === selectedIndex ? 'text-foreground' : ''
                          }`}>
                            {result.query}
                          </p>
                          {result.type === 'history' && result.created_at && (
                            <p className="text-xs text-foreground-muted">
                              {formatTime(result.created_at)}
                            </p>
                          )}
                          {result.type === 'popular' && result.count && (
                            <p className="text-xs text-emerald-400">
                              Used {result.count} times
                            </p>
                          )}
                        </div>
                        {index === selectedIndex && (
                          <ChevronRight className="w-4 h-4 text-primary" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-surface/50 text-xs text-foreground-muted">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-surface rounded border border-border">↑↓</kbd>
                    <span>Navigate</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-surface rounded border border-border">↵</kbd>
                    <span>Select</span>
                  </span>
                </div>
                <span>{results.length} results</span>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
