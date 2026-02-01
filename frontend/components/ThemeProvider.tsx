'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react'
import { motion } from 'framer-motion'

/**
 * Theme types
 */
type Theme = 'light' | 'dark' | 'system'
type ResolvedTheme = 'light' | 'dark'

/**
 * Theme context type
 */
interface ThemeContextType {
  theme: Theme
  resolvedTheme: ResolvedTheme
  systemTheme: ResolvedTheme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  themes: Theme[]
  isLoading: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

/**
 * Theme Provider Props
 */
interface ThemeProviderProps {
  children: ReactNode
  attribute?: 'class' | 'data-theme'
  defaultTheme?: Theme
  enableSystem?: boolean
  disableTransitionOnChange?: boolean
  storageKey?: string
  themes?: Theme[]
}

/**
 * Theme Provider Component
 * 
 * Features:
 * - Light/Dark/System theme support
 * - Smooth transitions between themes
 * - System preference detection
 * - Theme persistence in localStorage
 * - No flash on load (inline script)
 * - Reduced motion support
 * 
 * Inspired by: next-themes, Radix UI
 */
export function ThemeProvider({
  children,
  attribute = 'class',
  defaultTheme = 'system',
  enableSystem = true,
  disableTransitionOnChange = false,
  storageKey = 'theme',
  themes = ['light', 'dark', 'system'],
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>('system')
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('dark')
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>('dark')
  const [mounted, setMounted] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  /**
   * Apply theme to document
   */
  const applyTheme = useCallback((newTheme: Theme) => {
    const root = document.documentElement
    
    // Disable transitions temporarily
    if (!disableTransitionOnChange) {
      root.classList.add('theme-transitioning')
    }

    // Remove old theme attribute
    if (attribute === 'class') {
      root.classList.remove('light', 'dark')
    } else {
      root.removeAttribute(attribute)
    }

    // Resolve theme
    let resolved: ResolvedTheme
    if (newTheme === 'system' && enableSystem) {
      resolved = systemTheme
    } else {
      resolved = newTheme as ResolvedTheme
    }

    // Apply new theme
    if (attribute === 'class') {
      root.classList.add(resolved)
    } else {
      root.setAttribute(attribute, resolved)
    }

    // Update color scheme meta tag
    const meta = document.querySelector('meta[name="color-scheme"]')
    if (meta) {
      meta.setAttribute('content', resolved)
    }

    setResolvedTheme(resolved)

    // Re-enable transitions
    if (!disableTransitionOnChange) {
      requestAnimationFrame(() => {
        root.classList.remove('theme-transitioning')
      })
    }
  }, [attribute, disableTransitionOnChange, enableSystem, systemTheme])

  /**
   * Set theme and persist
   */
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem(storageKey, newTheme)
    applyTheme(newTheme)
  }, [applyTheme, storageKey])

  /**
   * Toggle between light and dark
   */
  const toggleTheme = useCallback(() => {
    const newTheme = resolvedTheme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
  }, [resolvedTheme, setTheme])

  /**
   * Initialize on mount
   */
  useEffect(() => {
    setMounted(true)

    // Get saved theme
    const savedTheme = localStorage.getItem(storageKey) as Theme | null
    const initialTheme = savedTheme || defaultTheme

    // Get system preference
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const currentSystemTheme: ResolvedTheme = mediaQuery.matches ? 'dark' : 'light'
    setSystemTheme(currentSystemTheme)

    // Apply initial theme
    setThemeState(initialTheme)
    applyTheme(initialTheme)
    setIsLoading(false)

    // Listen for system theme changes
    const handleChange = (e: MediaQueryListEvent) => {
      const newSystemTheme: ResolvedTheme = e.matches ? 'dark' : 'light'
      setSystemTheme(newSystemTheme)

      if (theme === 'system' || (!theme && defaultTheme === 'system')) {
        applyTheme('system')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [defaultTheme, storageKey, theme, applyTheme])

  // Prevent flash by hiding content until mounted
  if (!mounted) {
    return (
      <>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                function getThemePreference() {
                  if (typeof localStorage !== 'undefined' && localStorage.getItem('${storageKey}')) {
                    return localStorage.getItem('${storageKey}');
                  }
                  return '${defaultTheme}';
                }
                
                function getSystemTheme() {
                  if (typeof window !== 'undefined' && window.matchMedia) {
                    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                  }
                  return 'dark';
                }
                
                const theme = getThemePreference();
                const resolved = theme === 'system' ? getSystemTheme() : theme;
                
                if ('${attribute}' === 'class') {
                  document.documentElement.classList.add(resolved);
                } else {
                  document.documentElement.setAttribute('${attribute}', resolved);
                }
              })();
            `,
          }}
        />
        <div style={{ visibility: 'hidden' }}>{children}</div>
      </>
    )
  }

  const value: ThemeContextType = {
    theme,
    resolvedTheme,
    systemTheme,
    setTheme,
    toggleTheme,
    themes,
    isLoading,
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

/**
 * Hook to use theme
 */
export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

/**
 * Theme Toggle Button
 */
interface ThemeToggleProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'ghost' | 'outline'
}

export function ThemeToggle({ 
  className = '', 
  size = 'md',
  variant = 'default' 
}: ThemeToggleProps) {
  const { resolvedTheme, toggleTheme, isLoading } = useTheme()

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  }

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  }

  if (isLoading) {
    return (
      <div className={cn(
        sizeClasses[size],
        'rounded-xl bg-surface animate-pulse',
        className
      )} />
    )
  }

  const isDark = resolvedTheme === 'dark'

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={toggleTheme}
      className={cn(
        sizeClasses[size],
        'relative flex items-center justify-center rounded-xl',
        'transition-colors duration-200',
        variant === 'default' && 'bg-surface hover:bg-surface-elevated',
        variant === 'ghost' && 'hover:bg-surface',
        variant === 'outline' && 'border border-border hover:bg-surface',
        className
      )}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          <motion.div
            key="moon"
            initial={{ y: -20, opacity: 0, rotate: -90 }}
            animate={{ y: 0, opacity: 1, rotate: 0 }}
            exit={{ y: 20, opacity: 0, rotate: 90 }}
            transition={{ duration: 0.2 }}
          >
            <svg 
              className={cn(iconSizes[size], 'text-foreground')} 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" 
              />
            </svg>
          </motion.div>
        ) : (
          <motion.div
            key="sun"
            initial={{ y: -20, opacity: 0, rotate: -90 }}
            animate={{ y: 0, opacity: 1, rotate: 0 }}
            exit={{ y: 20, opacity: 0, rotate: 90 }}
            transition={{ duration: 0.2 }}
          >
            <svg 
              className={cn(iconSizes[size], 'text-foreground')} 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" 
              />
            </svg>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.button>
  )
}

/**
 * Theme Selector Dropdown
 */
interface ThemeSelectorProps {
  className?: string
}

export function ThemeSelector({ className }: ThemeSelectorProps) {
  const { theme, setTheme, themes, resolvedTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)

  const themeIcons = {
    light: '☀️',
    dark: '🌙',
    system: '💻',
  }

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface 
                 hover:bg-surface-elevated transition-colors"
      >
        <span>{themeIcons[resolvedTheme]}</span>
        <span className="text-sm capitalize">{theme}</span>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-40 py-1 rounded-xl 
                      glass-card border border-border shadow-xl z-50">
          {themes.map((t) => (
            <button
              key={t}
              onClick={() => {
                setTheme(t)
                setIsOpen(false)
              }}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-sm',
                'hover:bg-surface transition-colors',
                theme === t && 'bg-primary/10 text-primary'
              )}
            >
              <span>{themeIcons[t]}</span>
              <span className="capitalize">{t}</span>
              {theme === t && (
                <svg className="w-4 h-4 ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
