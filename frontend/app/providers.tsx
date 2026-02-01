'use client'

import { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ThemeProvider } from '@/components/ThemeProvider'

/**
 * Configure React Query client with optimal defaults
 * for the AI Analytics Platform
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data stays fresh for 1 minute
      staleTime: 60 * 1000,
      // Don't refetch on window focus to avoid disruption
      refetchOnWindowFocus: false,
      // Retry failed queries 2 times with exponential backoff
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Keep previous data while fetching new data
      placeholderData: (previousData: unknown) => previousData,
    },
    mutations: {
      // Retry mutations once on failure
      retry: 1,
    },
  },
})

interface ProvidersProps {
  children: ReactNode
}

/**
 * Application Providers
 * 
 * Wraps the application with all necessary context providers:
 * - ErrorBoundary: Catches and handles React errors gracefully
 * - QueryClientProvider: Manages server state with React Query
 * - ThemeProvider: Handles dark/light mode theming
 * - Toaster: Displays toast notifications
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange={false}
        >
          {children}
          <Toaster
            position="bottom-right"
            richColors
            closeButton
            toastOptions={{
              style: {
                background: 'hsl(var(--surface))',
                border: '1px solid hsl(var(--border))',
                color: 'hsl(var(--foreground))',
              },
            }}
          />
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default Providers
