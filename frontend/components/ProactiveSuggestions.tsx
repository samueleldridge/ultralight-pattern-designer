'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Lightbulb, 
  TrendingUp, 
  AlertTriangle,
  Sparkles,
  X,
  ChevronRight,
  Bell,
  Brain
} from 'lucide-react'

interface ProactiveSuggestion {
  id: string
  title: string
  description: string
  suggested_query: string
  reason: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  created_at: string
}

interface ProactiveSuggestionsPanelProps {
  onSelectQuery: (query: string) => void
}

export function ProactiveSuggestionsPanel({ onSelectQuery }: ProactiveSuggestionsPanelProps) {
  const [suggestions, setSuggestions] = useState<ProactiveSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isExpanded, setIsExpanded] = useState(true)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchSuggestions()
  }, [])

  const fetchSuggestions = async () => {
    try {
      const response = await fetch('/api/users/me/suggestions?limit=5')
      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDismiss = async (id: string) => {
    try {
      await fetch(`/api/users/me/suggestions/${id}/dismiss`, { method: 'POST' })
      setDismissed(prev => new Set(prev).add(id))
    } catch (error) {
      console.error('Failed to dismiss:', error)
    }
  }

  const handleClick = async (suggestion: ProactiveSuggestion) => {
    try {
      await fetch(`/api/users/me/suggestions/${suggestion.id}/click`, { method: 'POST' })
      onSelectQuery(suggestion.suggested_query)
    } catch (error) {
      console.error('Failed to track click:', error)
      onSelectQuery(suggestion.suggested_query)
    }
  }

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'urgent':
      case 'high':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />
      case 'medium':
        return <Lightbulb className="w-4 h-4 text-primary" />
      default:
        return <Sparkles className="w-4 h-4 text-foreground-muted" />
    }
  }

  const getPriorityBorder = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'border-amber-500/50 bg-amber-500/10'
      case 'high':
        return 'border-amber-400/30 bg-amber-400/5'
      case 'medium':
        return 'border-primary/30 bg-primary/5'
      default:
        return 'border-border bg-surface'
    }
  }

  const visibleSuggestions = suggestions.filter(s => !dismissed.has(s.id))

  if (isLoading) {
    return (
      <div className="glass-card rounded-xl p-4">
        <div className="flex items-center gap-2 text-foreground-muted">
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading suggestions...</span>
        </div>
      </div>
    )
  }

  if (visibleSuggestions.length === 0) {
    return (
      <div className="glass-card rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-surface-elevated flex items-center justify-center">
            <Brain className="w-5 h-5 text-foreground-muted" />
          </div>
          <div>
            <h4 className="text-sm font-medium">Proactive Intelligence</h4>
            <p className="text-xs text-foreground-muted">
              No new suggestions. Check back later!
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h4 className="text-sm font-medium flex items-center gap-2">
              Insights for You
              <span className="px-2 py-0.5 text-[10px] bg-primary/20 text-primary rounded-full">
                {visibleSuggestions.length} new
              </span>
            </h4>
            <p className="text-xs text-foreground-muted">
              Based on your interests and new data
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-primary" />
          {isExpanded ? (
            <ChevronRight className="w-4 h-4 text-foreground-muted rotate-90 transition-transform" />
          ) : (
            <ChevronRight className="w-4 h-4 text-foreground-muted transition-transform" />
          )}
        </div>
      </button>

      {/* Suggestions List */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-2">
              {visibleSuggestions.map((suggestion, index) => (
                <motion.div
                  key={suggestion.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  className={`group relative p-3 rounded-lg border ${getPriorityBorder(suggestion.priority)} hover:shadow-lg transition-all cursor-pointer`}
                  onClick={() => handleClick(suggestion)}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getPriorityIcon(suggestion.priority)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h5 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                        {suggestion.title}
                      </h5>
                      <p className="text-xs text-foreground-muted mt-1 line-clamp-2">
                        {suggestion.description}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-[10px] px-2 py-0.5 bg-surface rounded-full text-foreground-muted">
                          {suggestion.suggested_query.slice(0, 30)}...
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDismiss(suggestion.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-surface-elevated rounded transition-all"
                    >
                      <X className="w-3 h-3 text-foreground-muted" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-4 pb-4">
              <a
                href="/settings/intelligence"
                className="flex items-center justify-center gap-2 text-xs text-foreground-muted hover:text-foreground transition-colors py-2"
              >
                <TrendingUp className="w-3 h-3" />
                <span>View all insights & analytics</span>
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
