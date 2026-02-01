'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, X, Command, ArrowUp, ArrowDown, Enter, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useDebounce } from '@/hooks/usePerformance'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcuts'

/**
 * SearchInput - Debounced search input with loading state
 * 
 * @example
 * <SearchInput
 *   value={search}
 *   onChange={setSearch}
 *   onSearch={handleSearch}
 *   placeholder="Search..."
 *   debounceMs={300}
 * />
 */
interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  onSearch?: (value: string) => void
  placeholder?: string
  debounceMs?: number
  isLoading?: boolean
  autoFocus?: boolean
  className?: string
  inputClassName?: string
}

export function SearchInput({
  value,
  onChange,
  onSearch,
  placeholder = 'Search...',
  debounceMs = 300,
  isLoading = false,
  autoFocus = false,
  className,
  inputClassName,
}: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedValue = useDebounce(localValue, debounceMs)

  // Sync with external value
  useEffect(() => {
    setLocalValue(value)
  }, [value])

  // Trigger search on debounced value change
  useEffect(() => {
    onChange(debouncedValue)
    onSearch?.(debouncedValue)
  }, [debouncedValue])

  const handleClear = useCallback(() => {
    setLocalValue('')
    onChange('')
    onSearch?.('')
    inputRef.current?.focus()
  }, [onChange, onSearch])

  return (
    <div className={cn('relative', className)}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
      
      <input
        ref={inputRef}
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        className={cn(
          'input-field w-full pl-10 pr-10',
          inputClassName
        )}
        aria-label="Search"
      />

      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
        {isLoading ? (
          <Loader2 className="w-4 h-4 text-foreground-muted animate-spin" />
        ) : localValue ? (
          <button
            onClick={handleClear}
            className="p-1 hover:bg-surface rounded transition-colors"
            aria-label="Clear search"
          >
            <X className="w-4 h-4 text-foreground-muted" />
          </button>
        ) : (
          <kbd className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 
                         text-xs text-foreground-subtle bg-surface rounded">
            <Command className="w-3 h-3" />
            <span>K</span>
          </kbd>
        )}
      </div>
    </div>
  )
}

/**
 * SearchCommand - Command palette style search (like Raycast, Linear)
 * 
 * @example
 * const [open, setOpen] = useState(false)
 * 
 * <SearchCommand
 *   open={open}
 *   onOpenChange={setOpen}
 *   items={searchResults}
 *   onSelect={handleSelect}
 * />
 */
interface SearchItem {
  id: string
  title: string
  subtitle?: string
  icon?: React.ReactNode
  shortcut?: string
  section?: string
  disabled?: boolean
}

interface SearchCommandProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  items: SearchItem[]
  onSelect: (item: SearchItem) => void
  placeholder?: string
  isLoading?: boolean
  emptyMessage?: string
  className?: string
}

export function SearchCommand({
  open,
  onOpenChange,
  items,
  onSelect,
  placeholder = 'Search commands...',
  isLoading = false,
  emptyMessage = 'No results found',
  className,
}: SearchCommandProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Filter items based on query
  const filteredItems = items.filter((item) => {
    const searchStr = `${item.title} ${item.subtitle || ''}`.toLowerCase()
    return searchStr.includes(query.toLowerCase())
  })

  // Group items by section
  const groupedItems = filteredItems.reduce((acc, item) => {
    const section = item.section || 'Results'
    if (!acc[section]) acc[section] = []
    acc[section].push(item)
    return acc
  }, {} as Record<string, SearchItem[]>)

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) => 
          prev < filteredItems.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev))
        break
      case 'Enter':
        e.preventDefault()
        const selected = filteredItems[selectedIndex]
        if (selected && !selected.disabled) {
          onSelect(selected)
          onOpenChange(false)
          setQuery('')
        }
        break
      case 'Escape':
        e.preventDefault()
        onOpenChange(false)
        setQuery('')
        break
    }
  }, [filteredItems, selectedIndex, onSelect, onOpenChange])

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`)
    selectedElement?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      {/* Command palette */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: -20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className={cn(
          'relative w-full max-w-2xl mx-4',
          'glass-card rounded-2xl overflow-hidden shadow-2xl',
          className
        )}
        onKeyDown={handleKeyDown}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-border">
          <Search className="w-5 h-5 text-foreground-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-foreground placeholder:text-foreground-subtle 
                     outline-none text-lg"
            aria-label="Search commands"
            aria-expanded={open}
            aria-controls="command-list"
            aria-activedescendant={filteredItems[selectedIndex]?.id}
          />
          {isLoading ? (
            <Loader2 className="w-5 h-5 text-foreground-muted animate-spin" />
          ) : (
            <kbd className="px-2 py-1 text-xs text-foreground-subtle bg-surface rounded">
              ESC
            </kbd>
          )}
        </div>

        {/* Results */}
        <div
          ref={listRef}
          id="command-list"
          role="listbox"
          className="max-h-[50vh] overflow-y-auto p-2"
        >
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-foreground-muted">
              {emptyMessage}
            </div>
          ) : (
            Object.entries(groupedItems).map(([section, sectionItems], sectionIndex) => (
              <div key={section} className={sectionIndex > 0 ? 'mt-4' : ''}>
                <h3 className="px-3 py-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                  {section}
                </h3>
                <div className="space-y-1">
                  {sectionItems.map((item) => {
                    const globalIndex = filteredItems.indexOf(item)
                    const isSelected = globalIndex === selectedIndex

                    return (
                      <button
                        key={item.id}
                        data-index={globalIndex}
                        role="option"
                        aria-selected={isSelected}
                        disabled={item.disabled}
                        onClick={() => {
                          onSelect(item)
                          onOpenChange(false)
                          setQuery('')
                        }}
                        className={cn(
                          'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left',
                          'transition-colors duration-150',
                          isSelected
                            ? 'bg-primary/10 text-foreground'
                            : 'text-foreground-muted hover:bg-surface',
                          item.disabled && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {item.icon && (
                          <span className="flex-shrink-0">{item.icon}</span>
                        )}
                        
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{item.title}</p>
                          {item.subtitle && (
                            <p className="text-xs text-foreground-subtle truncate">
                              {item.subtitle}
                            </p>
                          )}
                        </div>

                        {item.shortcut && (
                          <kbd className="flex-shrink-0 px-2 py-0.5 text-xs 
                                       text-foreground-subtle bg-surface rounded">
                            {item.shortcut}
                          </kbd>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-border 
                      bg-surface/50 text-xs text-foreground-subtle">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <ArrowUp className="w-3 h-3" />
              <ArrowDown className="w-3 h-3" />
              <span>Navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <Enter className="w-3 h-3" />
              <span>Select</span>
            </span>
          </div>
          <span>{filteredItems.length} results</span>
        </div>
      </motion.div>
    </div>
  )
}

/**
 * useCommandPalette - Hook to easily add command palette functionality
 * 
 * @example
 * const { open, setOpen, items, setItems } = useCommandPalette()
 * 
 * useEffect(() => {
 *   setItems([
 *     { id: '1', title: 'Dashboard', section: 'Navigation', icon: <Home /> },
 *     { id: '2', title: 'Settings', section: 'Navigation', icon: <Settings /> },
 *   ])
 * }, [])
 */
export function useCommandPalette() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<SearchItem[]>([])

  // Open with keyboard shortcut (Cmd+K)
  useKeyboardShortcut({
    combo: { key: 'k', modifiers: ['mod'] },
    handler: () => {
      setOpen(true)
      return false
    },
  })

  return { open, setOpen, items, setItems }
}
