'use client'

import { useState, useCallback, memo } from 'react'
import { 
  LayoutDashboard, 
  Database, 
  Settings, 
  Users, 
  Plus,
  Menu,
  ChevronRight,
  Sparkles,
  History,
  TrendingUp,
  Zap,
  LogOut,
  HelpCircle,
  Keyboard,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useKeyboardShortcut, COMMON_SHORTCUTS } from '@/hooks/useKeyboardShortcuts'
import { useReducedMotion } from '@/hooks/useA11y'

interface Suggestion {
  id: string
  type: 'pattern' | 'insight' | 'popular'
  title: string
  subtitle?: string
  icon: React.ReactNode
}

interface NavItem {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  shortcut?: string
  badge?: number
}

interface SidebarProps {
  isCollapsed?: boolean
  onCollapse?: (collapsed: boolean) => void
  className?: string
}

const suggestions: Suggestion[] = [
  {
    id: '1',
    type: 'pattern',
    title: 'Weekly revenue check',
    subtitle: 'You usually ask this on Mondays',
    icon: <History className="w-4 h-4" />,
  },
  {
    id: '2',
    type: 'insight',
    title: 'Q3 revenue up 23%',
    subtitle: 'Unusual spike detected',
    icon: <TrendingUp className="w-4 h-4" />,
  },
  {
    id: '3',
    type: 'popular',
    title: 'Top products by region',
    subtitle: 'Popular in your workspace',
    icon: <Zap className="w-4 h-4" />,
  },
]

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'queries', label: 'Queries', icon: History, shortcut: 'Q' },
  { id: 'data', label: 'Data Sources', icon: Database },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'settings', label: 'Settings', icon: Settings, shortcut: ',' },
]

/**
 * Sidebar Component - Optimized with React.memo and accessibility
 * 
 * Features:
 * - Collapsible sidebar with animation
 * - Keyboard navigation support
 * - ARIA labels and roles
 * - Reduced motion support
 * - Memoized to prevent unnecessary re-renders
 */
export const Sidebar = memo(function Sidebar({
  isCollapsed: controlledCollapsed,
  onCollapse,
  className,
}: SidebarProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  const [activeItem, setActiveItem] = useState('dashboard')
  const [showShortcuts, setShowShortcuts] = useState(false)
  const prefersReducedMotion = useReducedMotion()

  const isCollapsed = controlledCollapsed ?? internalCollapsed

  const handleToggleCollapse = useCallback(() => {
    const newState = !isCollapsed
    setInternalCollapsed(newState)
    onCollapse?.(newState)
  }, [isCollapsed, onCollapse])

  // Keyboard shortcut to toggle sidebar
  useKeyboardShortcut({
    combo: COMMON_SHORTCUTS.toggleSidebar,
    handler: () => {
      handleToggleCollapse()
      return false
    },
  })

  // Keyboard shortcut for settings
  useKeyboardShortcut({
    combo: { key: ',', modifiers: ['mod'] },
    handler: () => {
      setActiveItem('settings')
      return false
    },
  })

  const transitionConfig = prefersReducedMotion 
    ? { duration: 0 } 
    : { type: 'spring', stiffness: 400, damping: 30 }

  return (
    <motion.aside
      initial={false}
      animate={{ width: isCollapsed ? 80 : 280 }}
      transition={transitionConfig}
      className={cn(
        'h-screen glass-card border-r border-border/50',
        'flex flex-col',
        className
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-border/50">
        <div 
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent 
                   flex items-center justify-center flex-shrink-0"
          aria-hidden="true"
        >
          <Sparkles className="w-5 h-5 text-background" />
        </div>
        <AnimatePresence mode="wait">
          {!isCollapsed && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="ml-3 font-semibold text-lg whitespace-nowrap"
            >
              DataAI
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* New Query Button */}
      <div className="p-4">
        <button 
          className={cn(
            'btn-primary w-full flex items-center justify-center gap-2 py-2.5 rounded-xl',
            'transition-all duration-200',
            isCollapsed && 'px-2'
          )}
          aria-label={isCollapsed ? 'New Query' : undefined}
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="whitespace-nowrap overflow-hidden"
              >
                New Query
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1" aria-label="Primary">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeItem === item.id

          return (
            <button
              key={item.id}
              onClick={() => setActiveItem(item.id)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl',
                'transition-all duration-200',
                'focus:outline-none focus:ring-2 focus:ring-primary/50',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-foreground-muted hover:text-foreground hover:bg-surface'
              )}
              aria-current={isActive ? 'page' : undefined}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon 
                className={cn(
                  'w-5 h-5 flex-shrink-0',
                  isActive && 'text-primary'
                )} 
                aria-hidden="true"
              />
              <AnimatePresence>
                {!isCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="flex-1 flex items-center justify-between min-w-0"
                  >
                    <span className="font-medium text-sm truncate">{item.label}</span>
                    {item.shortcut && (
                      <kbd className="hidden lg:block px-1.5 py-0.5 text-[10px] 
                                   text-foreground-subtle bg-surface rounded">
                        ⌘{item.shortcut}
                      </kbd>
                    )}
                    {item.badge && (
                      <span className="px-1.5 py-0.5 text-[10px] font-medium 
                                     bg-primary/20 text-primary rounded-full">
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

      {/* Suggestions Section */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 border-t border-border/50 overflow-hidden"
          >
            <h4 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-3">
              Suggestions
            </h4>
            <div className="space-y-2">
              {suggestions.map((suggestion) => (
                <motion.button
                  key={suggestion.id}
                  whileHover={{ x: 2 }}
                  className="w-full text-left p-3 rounded-xl bg-surface/50 
                           hover:bg-surface transition-colors group
                           focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <div className="flex items-start gap-3">
                    <div 
                      className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center 
                               text-primary group-hover:bg-primary/20 transition-colors"
                      aria-hidden="true"
                    >
                      {suggestion.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {suggestion.title}
                      </p>
                      {suggestion.subtitle && (
                        <p className="text-xs text-foreground-muted mt-0.5 truncate">
                          {suggestion.subtitle}
                        </p>
                      )}
                    </div>
                    <ChevronRight 
                      className="w-4 h-4 text-foreground-subtle opacity-0 
                               group-hover:opacity-100 transition-opacity flex-shrink-0" 
                      aria-hidden="true"
                    />
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border/50 space-y-1">
        {/* Help button */}
        {!isCollapsed && (
          <button
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl
                     text-foreground-muted hover:text-foreground hover:bg-surface
                     transition-colors text-sm
                     focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <Keyboard className="w-4 h-4" aria-hidden="true" />
            <span>Keyboard shortcuts</span>
            <kbd className="ml-auto px-1.5 py-0.5 text-[10px] 
                         text-foreground-subtle bg-surface rounded">
              ⌘/
            </kbd>
          </button>
        )}

        {/* Collapse Toggle */}
        <button
          onClick={handleToggleCollapse}
          className={cn(
            'w-full flex items-center p-2 rounded-lg',
            'hover:bg-surface transition-colors text-foreground-muted',
            'focus:outline-none focus:ring-2 focus:ring-primary/50',
            isCollapsed ? 'justify-center' : 'justify-between'
          )}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!isCollapsed}
          title={isCollapsed ? 'Expand (⌘B)' : 'Collapse (⌘B)'}
        >
          {!isCollapsed && <span className="text-sm">Collapse</span>}
          <Menu 
            className={cn(
              'w-5 h-5 transition-transform',
              isCollapsed && 'rotate-180'
            )} 
            aria-hidden="true"
          />
        </button>
      </div>

      {/* Shortcuts Modal */}
      <AnimatePresence>
        {showShortcuts && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowShortcuts(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card rounded-2xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
                <button
                  onClick={() => setShowShortcuts(false)}
                  className="p-2 hover:bg-surface rounded-lg transition-colors"
                >
                  <span className="sr-only">Close</span>
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
              
              <div className="space-y-4">
                {Object.entries(COMMON_SHORTCUTS).map(([key, combo]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-foreground-muted">
                      {combo.description}
                    </span>
                    <kbd className="px-2 py-1 text-sm bg-surface rounded border border-border">
                      {combo.modifiers?.includes('mod') ? '⌘' : ''}
                      {combo.key.toUpperCase()}
                    </kbd>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  )
})

export default Sidebar
