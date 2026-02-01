'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw, Home, Bug, Copy } from 'lucide-react'
import { toast } from 'sonner'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  errorId: string
}

/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of the
 * component tree that crashed.
 * 
 * Inspired by Linear.app and Vercel error handling patterns
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: this.generateErrorId(),
    }
  }

  private generateErrorId(): string {
    return `err-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null,
      errorId: `err-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    this.setState({
      error,
      errorInfo,
    })

    // In production, you would send this to an error tracking service
    if (process.env.NODE_ENV === 'production') {
      // Example: Sentry.captureException(error, { extra: { errorInfo, errorId: this.state.errorId } })
      this.reportError(error, errorInfo)
    }
  }

  private reportError(error: Error, errorInfo: ErrorInfo) {
    // Placeholder for error reporting service
    fetch('/api/error-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        errorId: this.state.errorId,
        error: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        url: typeof window !== 'undefined' ? window.location.href : '',
        timestamp: new Date().toISOString(),
      }),
    }).catch(console.error)
  }

  private handleReset = () => {
    this.props.onReset?.()
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: this.generateErrorId(),
    })
  }

  private handleReload = () => {
    window.location.reload()
  }

  private handleGoHome = () => {
    window.location.href = '/'
  }

  private copyErrorDetails = () => {
    const details = `
Error ID: ${this.state.errorId}
Error: ${this.state.error?.message}
Stack: ${this.state.error?.stack}
Component Stack: ${this.state.errorInfo?.componentStack}
    `.trim()
    
    navigator.clipboard.writeText(details)
    toast.success('Error details copied to clipboard')
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
            className="max-w-lg w-full"
          >
            {/* Error Card */}
            <div className="glass-card rounded-2xl overflow-hidden">
              {/* Header */}
              <div className="relative px-6 py-8 text-center border-b border-border">
                <div className="absolute inset-0 bg-gradient-to-b from-error/5 to-transparent" />
                
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                  className="relative w-20 h-20 mx-auto mb-4 rounded-2xl bg-error/10 flex items-center justify-center"
                >
                  <AlertTriangle className="w-10 h-10 text-error" />
                </motion.div>
                
                <h1 className="relative text-2xl font-bold text-foreground mb-2">
                  Something went wrong
                </h1>
                <p className="relative text-foreground-muted">
                  We&apos;ve encountered an unexpected error
                </p>
              </div>

              {/* Error Details */}
              <div className="px-6 py-4 bg-surface/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                    Error ID
                  </span>
                  <button
                    onClick={this.copyErrorDetails}
                    className="flex items-center gap-1 text-xs text-primary hover:text-primary-foreground transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    Copy details
                  </button>
                </div>
                <code className="block px-3 py-2 bg-background rounded-lg text-xs font-mono text-foreground-muted">
                  {this.state.errorId}
                </code>
                
                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <div className="mt-4">
                    <span className="text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                      Error Message
                    </span>
                    <div className="mt-2 px-3 py-2 bg-error/5 border border-error/20 rounded-lg">
                      <p className="text-sm text-error font-mono">
                        {this.state.error.message}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="p-6 space-y-3">
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={this.handleReset}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-primary text-primary-foreground rounded-xl font-medium shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </motion.button>

                <div className="flex gap-3">
                  <motion.button
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={this.handleReload}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-surface border border-border text-foreground rounded-xl font-medium hover:bg-surface-hover hover:border-border-strong transition-all"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reload Page
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={this.handleGoHome}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-surface border border-border text-foreground rounded-xl font-medium hover:bg-surface-hover hover:border-border-strong transition-all"
                  >
                    <Home className="w-4 h-4" />
                    Go Home
                  </motion.button>
                </div>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-background-secondary border-t border-border text-center">
                <p className="text-xs text-foreground-subtle">
                  If this problem persists, please contact{' '}
                  <a
                    href="mailto:support@nexus.ai"
                    className="text-primary hover:underline"
                  >
                    support@nexus.ai
                  </a>
                </p>
              </div>
            </div>

            {/* Debug Info (Development Only) */}
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mt-4 glass-card rounded-xl overflow-hidden"
              >
                <div className="px-4 py-3 bg-warning/10 border-b border-warning/20 flex items-center gap-2">
                  <Bug className="w-4 h-4 text-warning" />
                  <span className="text-sm font-medium text-warning">Development Mode</span>
                </div>
                <div className="p-4 overflow-auto max-h-64">
                  <pre className="text-xs font-mono text-foreground-muted whitespace-pre-wrap">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </div>
              </motion.div>
            )}
          </motion.div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Hook version for functional components
 * Wraps children in ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  return function WithErrorBoundary(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    )
  }
}

export default ErrorBoundary
