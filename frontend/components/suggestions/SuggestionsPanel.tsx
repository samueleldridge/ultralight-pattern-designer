'use client'

import { useQuery } from '@tanstack/react-query'
import { Lightbulb, History, TrendingUp, Users } from 'lucide-react'

interface Suggestion {
  type: string
  text: string
  action: string
  query?: string
}

export function SuggestionsPanel() {
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['suggestions'],
    queryFn: async () => {
      const res = await fetch('/api/suggestions')
      return res.json()
    }
  })

  const getIcon = (type: string) => {
    switch (type) {
      case 'pattern': return <History className="w-4 h-4" />
      case 'proactive': return <TrendingUp className="w-4 h-4" />
      case 'popular': return <Users className="w-4 h-4" />
      default: return <Lightbulb className="w-4 h-4" />
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Suggestions
      </h2>

      {isLoading ? (
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-gray-100 rounded" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions?.map((suggestion: Suggestion, index: number) => (
            <button
              key={index}
              className="w-full text-left p-3 rounded-lg border hover:border-blue-500 hover:bg-blue-50 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-gray-400">
                  {getIcon(suggestion.type)}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {suggestion.text}
                  </p>
                  {suggestion.query && (
                    <p className="text-xs text-blue-600 mt-1">
                      "{suggestion.query}"
                    </p>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="mt-6 pt-6 border-t">
        <h3 className="text-xs font-medium text-gray-500 mb-2">
          Recent Questions
        </h3>
        <div className="space-y-2">
          <p className="text-sm text-gray-600 hover:text-blue-600 cursor-pointer">
            Revenue by region last month
          </p>
          <p className="text-sm text-gray-600 hover:text-blue-600 cursor-pointer">
            Top 10 products by sales
          </p>
        </div>
      </div>
    </div>
  )
}
