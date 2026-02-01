'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'

interface ThemeContextType {
  theme: string | undefined
  setTheme: (theme: string) => void
  resolvedTheme: string
  systemTheme: string
  themes: string[]
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
  attribute?: 'class' | 'data-theme'
  defaultTheme?: string
  enableSystem?: boolean
  disableTransitionOnChange?: boolean
  themes?: string[]
}

/**
 * Theme Provider Component
 * 
 * Manages theme state with support for:
 * - Light/Dark mode
 * - System preference detection
 * - No flash on load (using inline script)
 * - Smooth transitions between themes
 * 
 * Based on next-themes patterns but simplified for this project
 */
export function ThemeProvider({
  children,
  attribute = 'class',
  defaultTheme = 'system',
  enableSystem = true,
  disableTransitionOnChange = false,
  themes = ['light', 'dark', 'system'],
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<string | undefined>(undefined)
  const [resolvedTheme, setResolvedTheme] = useState<string>('dark')
  const [systemTheme, setSystemTheme] = useState<string>('dark')
  const [mounted, setMounted] = useState(false)

  // Initialize theme from localStorage on mount
  useEffect(() => {
    setMounted(true)
    
    const root = window.document.documentElement
    const savedTheme = localStorage.getItem('theme')
    const initialTheme = savedTheme || defaultTheme
    
    // Get system preference
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const systemPrefersDark = mediaQuery.matches
    const currentSystemTheme = systemPrefersDark ? 'dark' : 'light'
    setSystemTheme(currentSystemTheme)
    
    // Determine actual theme to apply
    let themeToApply = initialTheme
    if (initialTheme === 'system' && enableSystem) {
      themeToApply = currentSystemTheme
    }
    
    // Apply theme
    applyTheme(themeToApply, initialTheme)
    
    // Listen for system theme changes
    const handleChange = (e: MediaQueryListEvent) => {
      const newSystemTheme = e.matches ? 'dark' : 'light'
      setSystemTheme(newSystemTheme)
      
      if (theme === 'system' || (!theme && defaultTheme === 'system')) {
        applyTheme(newSystemTheme, 'system')
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [defaultTheme, enableSystem])

  const applyTheme = (newTheme: string, storageTheme: string) => {
    const root = window.document.documentElement
    
    // Disable transitions during theme change
    if (!disableTransitionOnChange) {
      root.classList.add('transitioning-theme')
    }
    
    // Remove old theme classes
    themes.forEach(t => {
      if (t !== 'system') {
        root.classList.remove(t)
      }
    })
    
    // Add new theme class
    if (newTheme !== 'system') {
      root.classList.add(newTheme)
    }
    
    // Store preference
    localStorage.setItem('theme', storageTheme)
    
    // Update state
    setThemeState(storageTheme)
    setResolvedTheme(newTheme === 'system' ? systemTheme : newTheme)
    
    // Re-enable transitions
    if (!disableTransitionOnChange) {
      setTimeout(() => {
        root.classList.remove('transitioning-theme')
      }, 0)
    }
  }

  const setTheme = (newTheme: string) => {
    if (!themes.includes(newTheme)) {
      console.warn(`Theme "${newTheme}" is not in allowed themes:`, themes)
      return
    }
    
    let themeToApply = newTheme
    if (newTheme === 'system' && enableSystem) {
      themeToApply = systemTheme
    }
    
    applyTheme(themeToApply, newTheme)
  }

  // Prevent flash by not rendering until mounted
  if (!mounted) {
    return (
      <>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                function getTheme() {
                  const saved = localStorage.getItem('theme')
                  if (saved) return saved
                  return '${defaultTheme}'
                }
                const theme = getTheme()
                const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
                const resolved = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme
                document.documentElement.classList.add(resolved)
              })()
            `,
          }}
        />
        <div style={{ visibility: 'hidden' }}>{children}</div>
      </>
    )
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        resolvedTheme,
        systemTheme,
        themes,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

/**
 * Hook to use theme context
 */
export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

/**
 * Theme toggle button component
 */
interface ThemeToggleProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function ThemeToggle({ className = '', size = 'md' }: ThemeToggleProps) {
  const { theme, setTheme, resolvedTheme } = useTheme()
  
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
  
  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
  }
  
  return (
    <button
      onClick={toggleTheme}
      className={`
        ${sizeClasses[size]}
        flex items-center justify-center
        rounded-xl
        text-foreground-muted
        hover:text-foreground
        hover:bg-surface
        transition-all duration-200
        ${className}
      `}
      aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {resolvedTheme === 'dark' ? (
        <svg className={iconSizes[size]} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        <svg className={iconSizes[size]} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  )
}

export default ThemeProvider
