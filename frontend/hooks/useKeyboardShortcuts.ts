'use client'

import { useEffect, useCallback, useRef } from 'react'

/**
 * Keyboard shortcut modifiers
 */
type ModifierKey = 'ctrl' | 'alt' | 'shift' | 'meta' | 'mod'

/**
 * Single key or key combination
 */
interface KeyCombo {
  key: string
  modifiers?: ModifierKey[]
}

/**
 * Keyboard shortcut handler
 */
type ShortcutHandler = (event: KeyboardEvent) => void | boolean

/**
 * Shortcut configuration
 */
interface Shortcut {
  combo: KeyCombo | string
  handler: ShortcutHandler
  description?: string
  scope?: string
  preventDefault?: boolean
  stopPropagation?: boolean
  disabled?: boolean
}

/**
 * useKeyboardShortcut - Register keyboard shortcuts
 * 
 * @example
 * useKeyboardShortcut({
 *   combo: { key: 'k', modifiers: ['mod'] },
 *   handler: () => setSearchOpen(true),
 *   description: 'Open search'
 * })
 */
export function useKeyboardShortcut(shortcut: Shortcut) {
  const {
    combo,
    handler,
    preventDefault = true,
    stopPropagation = false,
    disabled = false,
  } = shortcut

  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    if (disabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (matchesCombo(event, combo)) {
        if (preventDefault) {
          event.preventDefault()
        }
        if (stopPropagation) {
          event.stopPropagation()
        }

        const result = handlerRef.current(event)
        
        // If handler returns false, prevent default behavior
        if (result === false) {
          event.preventDefault()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [combo, preventDefault, stopPropagation, disabled])
}

/**
 * useKeyboardShortcuts - Register multiple keyboard shortcuts
 * 
 * @example
 * useKeyboardShortcuts([
 *   { combo: 'mod+k', handler: openSearch, description: 'Open search' },
 *   { combo: 'mod+/', handler: showShortcuts, description: 'Show shortcuts' },
 *   { combo: 'esc', handler: closeModal, description: 'Close modal' },
 * ])
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  const shortcutsRef = useRef(shortcuts)
  shortcutsRef.current = shortcuts

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcutsRef.current) {
        if (shortcut.disabled) continue

        if (matchesCombo(event, shortcut.combo)) {
          if (shortcut.preventDefault !== false) {
            event.preventDefault()
          }
          if (shortcut.stopPropagation) {
            event.stopPropagation()
          }

          const result = shortcut.handler(event)
          
          if (result === false) {
            event.preventDefault()
          }

          // Only handle first matching shortcut
          break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])
}

/**
 * useFocusScope - Scope keyboard shortcuts to a specific element
 * 
 * @example
 * const { ref, isActive } = useFocusScope()
 * 
 * useKeyboardShortcut({
 *   combo: 'esc',
 *   handler: close,
 *   disabled: !isActive
 * })
 */
export function useFocusScope<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null)
  const [isActive, setIsActive] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const handleFocus = () => setIsActive(true)
    const handleBlur = (e: FocusEvent) => {
      // Only deactivate if focus is leaving the element entirely
      if (!element.contains(e.relatedTarget as Node)) {
        setIsActive(false)
      }
    }

    element.addEventListener('focusin', handleFocus)
    element.addEventListener('focusout', handleBlur)

    return () => {
      element.removeEventListener('focusin', handleFocus)
      element.removeEventListener('focusout', handleBlur)
    }
  }, [])

  return { ref, isActive }
}

/**
 * Check if a keyboard event matches a key combo
 */
function matchesCombo(event: KeyboardEvent, combo: KeyCombo | string): boolean {
  let key: string
  let modifiers: ModifierKey[] = []

  if (typeof combo === 'string') {
    const parts = combo.toLowerCase().split('+')
    key = parts[parts.length - 1]
    modifiers = parts.slice(0, -1) as ModifierKey[]
  } else {
    key = combo.key.toLowerCase()
    modifiers = combo.modifiers || []
  }

  // Check key
  const eventKey = event.key.toLowerCase()
  if (eventKey !== key && event.code.toLowerCase() !== `key${key}`) {
    return false
  }

  // Check modifiers
  const ctrlKey = modifiers.includes('ctrl') || modifiers.includes('mod')
  const metaKey = modifiers.includes('meta') || modifiers.includes('mod')
  const altKey = modifiers.includes('alt')
  const shiftKey = modifiers.includes('shift')

  if (ctrlKey !== event.ctrlKey) return false
  if (metaKey !== event.metaKey) return false
  if (altKey !== event.altKey) return false
  if (shiftKey !== event.shiftKey) return false

  return true
}

/**
 * Parse shortcut string to KeyCombo
 */
export function parseShortcut(shortcut: string): KeyCombo {
  const parts = shortcut.toLowerCase().split('+')
  return {
    key: parts[parts.length - 1],
    modifiers: parts.slice(0, -1) as ModifierKey[],
  }
}

/**
 * Format KeyCombo to readable string
 */
export function formatShortcut(combo: KeyCombo): string {
  const { key, modifiers = [] } = combo
  const parts = [...modifiers]
  
  // Format key
  const formattedKey = key.length === 1 ? key.toUpperCase() : key
  parts.push(formattedKey)
  
  return parts.join(' + ')
}

/**
 * Get platform-specific modifier key name
 */
export function getModKey(): string {
  return typeof navigator !== 'undefined' && navigator.platform.includes('Mac') 
    ? '⌘' 
    : 'Ctrl'
}

/**
 * Common keyboard shortcuts configuration
 */
export const COMMON_SHORTCUTS = {
  // Navigation
  search: { key: 'k', modifiers: ['mod'] as ModifierKey[], description: 'Open search' },
  commandPalette: { key: 'p', modifiers: ['mod', 'shift'] as ModifierKey[], description: 'Open command palette' },
  goHome: { key: 'h', modifiers: ['mod'] as ModifierKey[], description: 'Go home' },
  
  // Actions
  new: { key: 'n', modifiers: ['mod'] as ModifierKey[], description: 'New item' },
  save: { key: 's', modifiers: ['mod'] as ModifierKey[], description: 'Save' },
  close: { key: 'w', modifiers: ['mod'] as ModifierKey[], description: 'Close' },
  
  // UI
  toggleSidebar: { key: 'b', modifiers: ['mod'] as ModifierKey[], description: 'Toggle sidebar' },
  toggleTheme: { key: 't', modifiers: ['mod', 'shift'] as ModifierKey[], description: 'Toggle theme' },
  showShortcuts: { key: '/', modifiers: ['mod'] as ModifierKey[], description: 'Show shortcuts' },
  
  // Global
  escape: { key: 'escape', modifiers: [] as ModifierKey[], description: 'Close/Cancel' },
  enter: { key: 'enter', modifiers: [] as ModifierKey[], description: 'Confirm' },
} as const

// Need to import useState for useFocusScope
import { useState } from 'react'
