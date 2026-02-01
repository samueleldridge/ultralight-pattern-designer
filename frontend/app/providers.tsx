'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState, useEffect } from 'react'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ToastProvider } from '@/components/feedback/Toast'

/**
 * Optimized QueryClient configuration
 * - Stale time of 5 minutes for better caching
 * - Retry logic for failed queries
 * - Refetch on window focus disabled for better UX
 */
function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Data stays fresh for 5 minutes
        staleTime: 5 * 60 * 1000,
        // Keep data in cache for 10 minutes
        gcTime: 10 * 60 * 1000,
        // Retry failed queries 2 times
        retry: 2,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // Don't refetch on window focus (better UX)
        refetchOnWindowFocus: false,
        // Don't refetch on reconnect if data is fresh
        refetchOnReconnect: 'always',
        // Show stale data while fetching
        placeholderData: (previousData: any) => previousData,
      },
      mutations: {
        // Retry mutations once
        retry: 1,
        retryDelay: 1000,
      },
    },
  })
}

/**
 * Global Providers
 * 
 * Wraps the application with all necessary providers:
 * - QueryClientProvider for data fetching
 * - ThemeProvider for light/dark mode
 * - ToastProvider for notifications
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient())
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Add loaded class for theme transitions
    document.documentElement.classList.add('loaded')
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange={false}
      >
        <ToastProvider position="bottom-right" maxToasts={5}>
          {children}
          
          {/* React Query Devtools - only in development */}
          {process.env.NODE_ENV === 'development' && mounted && (
            <ReactQueryDevtools 
              initialIsOpen={false}
              buttonPosition="bottom-left"
            />
          )}
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default Providers
