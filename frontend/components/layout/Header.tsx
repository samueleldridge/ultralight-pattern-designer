'use client'

import { useState, useCallback, memo } from 'react'
import { Search, Bell, ChevronDown, Command, Menu } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useDebounceCallback } from '@/hooks/usePerformance'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcuts'
import { ThemeToggle } from '@/components/ThemeProvider'

interface HeaderProps {
  onMenuClick?: () => void
  onSearchClick?: () => void
  className?: string
}

/**
 * Header Component - Optimized with React.memo and debounced search
 * 
 * Features:
 * - Debounced search input to reduce API calls
 * - Keyboard shortcut (Cmd+K) to focus search
 * - Memoized to prevent unnecessary re-renders
 * - ARIA labels for accessibility
 * - Responsive design with mobile menu button
 */
export const Header = memo(function Header({
  onMenuClick,
  onSearchClick,
  className,
}: HeaderProps) {
  const [notifications] = useState(3)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchFocused, setIsSearchFocused] = useState(false)

  // Debounced search handler
  const debouncedSearch = useDebounceCallback(
    useCallback((query: string) => {
      // Trigger search API call here
      console.log('Searching:', query)
    }, []),
    300
  )

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchQuery(value)
    debouncedSearch(value)
  }

  // Keyboard shortcut to focus search
  useKeyboardShortcut({
    combo: { key: 'k', modifiers: ['mod'] },
    handler: () => {
      const searchInput = document.getElementById('global-search')
      searchInput?.focus()
      return false
    },
  })

  return (
    <header
      className={cn(
        'h-16 glass-card border-b border-border/50',
        'flex items-center justify-between px-4 lg:px-6',
        'sticky top-0 z-30',
        className
      )}
    >
      {/* Left section: Menu button & Search */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        {/* Mobile menu button */}
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-surface transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5 text-foreground-muted" />
          </button>
        )}

        {/* Search */}
        <div className="relative flex-1">
          <Search 
            className={cn(
              'absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors',
              isSearchFocused ? 'text-primary' : 'text-foreground-muted'
            )} 
            aria-hidden="true"
          />
          <input
            id="global-search"
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            onClick={onSearchClick}
            placeholder="Search dashboards, queries, or ask AI..."
            className={cn(
              'input-field w-full pl-10 pr-12',
              'transition-all duration-200',
              isSearchFocused && 'ring-2 ring-primary/50'
            )}
            aria-label="Search dashboards and queries"
            aria-expanded="false"
            aria-haspopup="listbox"
          />
          {/* Keyboard shortcut hint */}
          <kbd 
            className="absolute right-3 top-1/2 -translate-y-1/2 
                     hidden sm:flex items-center gap-0.5 
                     px-1.5 py-0.5 text-xs text-foreground-subtle 
                     bg-surface rounded border border-border"
            aria-hidden="true"
          >
            <Command className="w-3 h-3" />
            <span>K</span>
          </kbd>
        </div>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2 sm:gap-4 ml-4">
        {/* Theme toggle */}
        <ThemeToggle size="md" variant="ghost" />

        {/* Notifications */}
        <button 
          className="relative p-2 rounded-xl hover:bg-surface transition-colors
                   focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label={`Notifications (${notifications} unread)`}
        >
          <Bell className="w-5 h-5 text-foreground-muted" aria-hidden="true" />
          <AnimatePresence>
            {notifications > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute top-1 right-1 w-4 h-4 
                         bg-error text-error-foreground 
                         text-[10px] font-medium rounded-full 
                         flex items-center justify-center"
                aria-hidden="true"
              >
                {notifications > 9 ? '9+' : notifications}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* User menu */}
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex items-center gap-2 pl-1 pr-2 py-1 
                   rounded-xl hover:bg-surface transition-colors
                   focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label="User menu"
          aria-haspopup="menu"
        >
          <div 
            className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent 
                     flex items-center justify-center text-primary-foreground 
                     font-medium text-sm"
            aria-hidden="true"
          >
            SE
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-sm font-medium leading-tight">Sam Eldridge</p>
            <p className="text-xs text-foreground-muted">Admin</p>
          </div>
          <ChevronDown className="w-4 h-4 text-foreground-muted hidden sm:block" aria-hidden="true" />
        </motion.button>
      </div>
    </header>
  )
})

export default Header
