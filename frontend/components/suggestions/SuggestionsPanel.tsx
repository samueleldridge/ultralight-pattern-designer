'use client'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { 
  Lightbulb, 
  History, 
  TrendingUp, 
  Users, 
  Sparkles,
  ChevronRight,
  Loader2,
  Zap
} from 'lucide-react'
import { toast } from 'sonner'

interface Suggestion {
  id: string
  type: 'pattern' | 'insight' | 'popular' | 'trending'
  title: string
  subtitle?: string
  description?: string
  query?: string
  confidence?: number
  icon?: string
}

const mockSuggestions: Suggestion[] = [
  {
    id: '1',
    type: 'pattern',
    title: 'Weekly revenue check',
    subtitle: 'You usually ask this on Mondays',
    query: 'What was our revenue this week?',
    confidence: 0.92,
  },
  {
    id: '2',
    type: 'insight',
    title: 'Q4 revenue up 23%',
    subtitle: 'Unusual spike detected in sales',
    description: 'Revenue has increased significantly compared to last quarter',
    confidence: 0.88,
  },
  {
    id: '3',
    type: 'popular',
    title: 'Top products by region',
    subtitle: 'Popular in your workspace',
    query: 'Show top products by sales region',
    confidence: 0.75,
  },
  {
    id: '4',
    type: 'trending',
    title: 'Customer churn risk',
    subtitle: '3 high-value accounts flagged',
    description: 'Potential churn detected based on activity patterns',
    confidence: 0.85,
  },
]

export function SuggestionsPanel() {
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['suggestions'],
    queryFn: async () => {
      // For demo, return mock data
      // In production: const res = await fetch('/api/suggestions')
      // return res.json()
      return mockSuggestions
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const getIcon = (type: string) => {
    switch (type) {
      case 'pattern': return <History className="w-4 h-4" />
      case 'insight': return <TrendingUp className="w-4 h-4" />
      case 'popular': return <Users className="w-4 h-4" />
      case 'trending': return <Zap className="w-4 h-4" />
      default: return <Lightbulb className="w-4 h-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'pattern': return 'bg-primary-subtle text-primary border-primary/20'
      case 'insight': return 'bg-success-subtle text-success border-success/20'
      case 'popular': return 'bg-secondary-subtle text-secondary border-secondary/20'
      case 'trending': return 'bg-warning-subtle text-warning border-warning/20'
      default: return 'bg-surface text-foreground-muted border-border'
    }
  }

  const handleSuggestionClick = (suggestion: Suggestion) => {
    if (suggestion.query) {
      toast.success(`Loading: ${suggestion.title}`)
      // Dispatch event or call parent handler
      window.dispatchEvent(new CustomEvent('suggestion-selected', { 
        detail: { query: suggestion.query } 
      }))
    } else {
      toast.info('Opening insight details...')
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-semibold">AI Suggestions</h2>
        </div>
        <span className="text-xs text-foreground-muted">
          {suggestions?.length || 0} insights
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-foreground-muted" />
          </div>
        ) : (
          <div className="space-y-2">
            {suggestions?.map((suggestion, index) => (
              <motion.button
                key={suggestion.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full text-left p-3 rounded-xl border border-border hover:border-primary/50 hover:bg-surface transition-all duration-200 group"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${getTypeColor(suggestion.type)}`}>
                    {getIcon(suggestion.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-foreground truncate">
                        {suggestion.title}
                      </p>
                      {suggestion.confidence && suggestion.confidence > 0.9 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-success-subtle text-success font-medium">
                          High confidence
                        </span>
                      )}
                    </div>
                    {suggestion.subtitle && (
                      <p className="text-xs text-foreground-muted mt-0.5">
                        {suggestion.subtitle}
                      </p>
                    )}
                    {suggestion.query && (
                      <p className="text-xs text-primary mt-1.5 truncate">
                        &ldquo;{suggestion.query}&rdquo;
                      </p>
                    )}
                  </div>
                  <ChevronRight className="w-4 h-4 text-foreground-subtle opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </div>
              </motion.button>
            ))}
          </div>
        )}

        {/* Recent Questions */}
        <div className="mt-6 pt-4 border-t border-border">
          <h3 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-3">
            Recent Questions
          </h3>
          <div className="space-y-1">
            {[
              'Revenue by region last month',
              'Top 10 products by sales',
              'Customer acquisition cost',
            ].map((question, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                onClick={() => toast.success(`Loading: ${question}`)}
                className="w-full text-left px-3 py-2 text-sm text-foreground-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors"
              >
                {question}
              </motion.button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border bg-surface/50">
        <button 
          onClick={() => toast.info('Feedback recorded')}
          className="w-full text-center text-xs text-foreground-muted hover:text-foreground transition-colors"
        >
          Are these suggestions helpful?
        </button>
      </div>
    </div>
  )
}
