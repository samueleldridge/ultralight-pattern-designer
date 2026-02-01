'use client'

import { useEffect, useRef, useCallback, useState } from 'react'

/**
 * useFocusTrap - Trap focus within a container (for modals, dialogs)
 * 
 * @example
 * const { ref } = useFocusTrap({ active: isOpen })
 * 
 * <div ref={ref} role="dialog">
 *   <button>First</button>
 *   <button>Last</button>
 * </div>
 */
interface FocusTrapOptions {
  active: boolean
  initialFocus?: boolean
  returnFocus?: boolean
}

export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(
  options: FocusTrapOptions
) {
  const { active, initialFocus = true, returnFocus = true } = options
  const ref = useRef<T>(null)
  const previouslyFocusedElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!active) return

    const container = ref.current
    if (!container) return

    // Store previously focused element
    previouslyFocusedElement.current = document.activeElement as HTMLElement

    // Find all focusable elements
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )

    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    // Set initial focus
    if (initialFocus && firstElement) {
      firstElement.focus()
    }

    // Handle tab key
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement?.focus()
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement?.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      
      // Return focus to previous element
      if (returnFocus && previouslyFocusedElement.current) {
        previouslyFocusedElement.current.focus()
      }
    }
  }, [active, initialFocus, returnFocus])

  return { ref }
}

/**
 * useAriaLive - Announce messages to screen readers
 * 
 * @example
 * const { announce } = useAriaLive()
 * 
 * announce('Form submitted successfully', 'polite')
 */
type AriaLivePriority = 'polite' | 'assertive' | 'off'

export function useAriaLive() {
  const announce = useCallback((message: string, priority: AriaLivePriority = 'polite') => {
    // Find or create live region
    let liveRegion = document.getElementById('aria-live-region')
    
    if (!liveRegion) {
      liveRegion = document.createElement('div')
      liveRegion.id = 'aria-live-region'
      liveRegion.setAttribute('aria-live', 'polite')
      liveRegion.setAttribute('aria-atomic', 'true')
      liveRegion.className = 'sr-only'
      document.body.appendChild(liveRegion)
    }

    // Update priority
    liveRegion.setAttribute('aria-live', priority)
    
    // Set message
    liveRegion.textContent = message

    // Clear after announcement
    setTimeout(() => {
      liveRegion!.textContent = ''
    }, 1000)
  }, [])

  return { announce }
}

/**
 * useReducedMotion - Respect user's motion preferences
 * 
 * @example
 * const prefersReducedMotion = useReducedMotion()
 * 
 * <motion.div animate={prefersReducedMotion ? {} : { scale: 1.1 }} />
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)

    const handler = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  return prefersReducedMotion
}

/**
 * useHighContrast - Detect high contrast mode
 * 
 * @example
 * const isHighContrast = useHighContrast()
 * 
 * <div className={isHighContrast ? 'border-2' : 'border'} />
 */
export function useHighContrast(): boolean {
  const [isHighContrast, setIsHighContrast] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)')
    setIsHighContrast(mediaQuery.matches)

    const handler = (e: MediaQueryListEvent) => {
      setIsHighContrast(e.matches)
    }

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  return isHighContrast
}

/**
 * useColorScheme - Detect preferred color scheme
 * 
 * @example
 * const colorScheme = useColorScheme()
 * 
 * <div className={colorScheme === 'dark' ? 'bg-black' : 'bg-white'} />
 */
export type ColorScheme = 'light' | 'dark' | 'no-preference'

export function useColorScheme(): ColorScheme {
  const [colorScheme, setColorScheme] = useState<ColorScheme>('no-preference')

  useEffect(() => {
    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const lightQuery = window.matchMedia('(prefers-color-scheme: light)')

    const updateScheme = () => {
      if (darkQuery.matches) setColorScheme('dark')
      else if (lightQuery.matches) setColorScheme('light')
      else setColorScheme('no-preference')
    }

    updateScheme()

    darkQuery.addEventListener('change', updateScheme)
    lightQuery.addEventListener('change', updateScheme)

    return () => {
      darkQuery.removeEventListener('change', updateScheme)
      lightQuery.removeEventListener('change', updateScheme)
    }
  }, [])

  return colorScheme
}

/**
 * useClickOutside - Handle clicks outside an element (with escape key support)
 * 
 * @example
 * const { ref } = useClickOutside({
 *   onClickOutside: closeModal,
 *   onEscape: closeModal
 * })
 */
interface ClickOutsideOptions {
  onClickOutside: () => void
  onEscape?: () => void
  enabled?: boolean
}

export function useClickOutside<T extends HTMLElement = HTMLDivElement>(
  options: ClickOutsideOptions
) {
  const { onClickOutside, onEscape, enabled = true } = options
  const ref = useRef<T>(null)

  useEffect(() => {
    if (!enabled) return

    const handleClick = (event: MouseEvent) => {
      const element = ref.current
      if (element && !element.contains(event.target as Node)) {
        onClickOutside()
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && onEscape) {
        onEscape()
      }
    }

    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClickOutside, onEscape, enabled])

  return { ref }
}

/**
 * useAnnounceLoading - Announce loading states to screen readers
 * 
 * @example
 * useAnnounceLoading(isLoading, 'Loading search results')
 */
export function useAnnounceLoading(isLoading: boolean, message: string) {
  const { announce } = useAriaLive()
  const wasLoading = useRef(false)

  useEffect(() => {
    if (isLoading && !wasLoading.current) {
      announce(`${message}...`, 'polite')
    } else if (!isLoading && wasLoading.current) {
      announce(`${message} complete`, 'polite')
    }
    wasLoading.current = isLoading
  }, [isLoading, message, announce])
}

/**
 * usePageTitle - Update page title with announcement
 * 
 * @example
 * usePageTitle('Dashboard - AI Analytics')
 */
export function usePageTitle(title: string) {
  const { announce } = useAriaLive()

  useEffect(() => {
    const originalTitle = document.title
    document.title = title
    announce(`Navigated to ${title}`, 'polite')

    return () => {
      document.title = originalTitle
    }
  }, [title, announce])
}

/**
 * Accessible key codes for common operations
 */
export const KEY_CODES = {
  ENTER: 'Enter',
  ESCAPE: 'Escape',
  SPACE: ' ',
  TAB: 'Tab',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  HOME: 'Home',
  END: 'End',
  PAGE_UP: 'PageUp',
  PAGE_DOWN: 'PageDown',
} as const

/**
 * Generate unique IDs for ARIA attributes
 */
export function useUniqueId(prefix: string = 'id'): string {
  const [id] = useState(() => `${prefix}-${Math.random().toString(36).substr(2, 9)}`)
  return id
}

/**
 * Generate ARIA relationship IDs
 * 
 * @example
 * const { id, labelId, describedById } = useAriaIds('dialog')
 * 
 * <div id={id} aria-labelledby={labelId} aria-describedby={describedById}>
 *   <h2 id={labelId}>Title</h2>
 *   <p id={describedById}>Description</p>
 * </div>
 */
export function useAriaIds(componentName: string) {
  const baseId = useUniqueId(componentName)
  
  return {
    id: baseId,
    labelId: `${baseId}-label`,
    describedById: `${baseId}-description`,
    errorId: `${baseId}-error`,
    helperId: `${baseId}-helper`,
  }
}

/**
 * Skip link component for keyboard navigation
 * Allows users to skip to main content
 */
export function SkipLink({ targetId = 'main-content' }: { targetId?: string }) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    const target = document.getElementById(targetId)
    if (target) {
      target.focus()
      target.scrollIntoView()
    }
  }

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 
                 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground 
                 focus:rounded-lg focus:font-medium"
    >
      Skip to main content
    </a>
  )
}

/**
 * Visually hidden component for screen reader only content
 */
export function VisuallyHidden({ children }: { children: React.ReactNode }) {
  return (
    <span className="absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0">
      {children}
    </span>
  )
}
