'use client'

import { useState } from 'react'
import { 
  LayoutDashboard, 
  Database, 
  Settings, 
  Users, 
  Bell,
  Search,
  Plus,
  Menu,
  ChevronRight,
  Sparkles,
  History,
  TrendingUp,
  Zap
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Suggestion {
  id: string
  type: 'pattern' | 'insight' | 'popular'
  title: string
  subtitle?: string
  icon: React.ReactNode
}

const suggestions: Suggestion[] = [
  {
    id: '1',
    type: 'pattern',
    title: 'Weekly revenue check',
    subtitle: 'You usually ask this on Mondays',
    icon: <History className="w-4 h-4" />
  },
  {
    id: '2',
    type: 'insight',
    title: 'Q3 revenue up 23%',
    subtitle: 'Unusual spike detected',
    icon: <TrendingUp className="w-4 h-4" />
  },
  {
    id: '3',
    type: 'popular',
    title: 'Top products by region',
    subtitle: 'Popular in your workspace',
    icon: <Zap className="w-4 h-4" />
  }
]

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [activeItem, setActiveItem] = useState('dashboard')

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'queries', label: 'Queries', icon: History },
    { id: 'data', label: 'Data Sources', icon: Database },
    { id: 'team', label: 'Team', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  return (
    <motion.aside 
      initial={false}
      animate={{ width: isCollapsed ? 80 : 280 }}
      className="h-screen glass-card border-r border-border/50 flex flex-col"
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-border/50">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-background" />
        </div>
        {!isCollapsed && (
          <motion.span 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="ml-3 font-semibold text-lg"
          >
            DataAI
          </motion.span>
        )}
      </div>

      {/* New Query Button */}
      <div className="p-4">
        <button className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 rounded-xl">
          <Plus className="w-4 h-4" />
          {!isCollapsed && <span>New Query</span>}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeItem === item.id
          
          return (
            <button
              key={item.id}
              onClick={() => setActiveItem(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                isActive 
                  ? 'bg-primary/10 text-primary' 
                  : 'text-foreground-muted hover:text-foreground hover:bg-surface'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive && 'text-primary'}`} />
              {!isCollapsed && (
                <span className="font-medium text-sm">{item.label}</span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Suggestions Section */}
      {!isCollapsed && (
        <div className="p-4 border-t border-border/50">
          <h4 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-3">
            Suggestions
          </h4>
          <div className="space-y-2">
            {suggestions.map((suggestion) => (
              <motion.button
                key={suggestion.id}
                whileHover={{ x: 2 }}
                className="w-full text-left p-3 rounded-xl bg-surface/50 hover:bg-surface transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
                    {suggestion.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {suggestion.title}
                    </p>
                    {suggestion.subtitle && (
                      <p className="text-xs text-foreground-muted mt-0.5">
                        {suggestion.subtitle}
                      </p>
                    )}
                  </div>
                  <ChevronRight className="w-4 h-4 text-foreground-subtle opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="p-4 border-t border-border/50">
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted"
        >
          <Menu className={`w-5 h-5 transition-transform ${isCollapsed && 'rotate-180'}`} />
        </button>
      </div>
    </motion.aside>
  )
}
