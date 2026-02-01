'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  AlertTriangle,
  Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Toast notification system
 * 
 * Inspired by: Sonner, React Hot Toast
 * Features:
 * - Multiple toast types (success, error, warning, info, loading)
 * - Auto-dismiss with progress indicator
 * - Pause on hover
 * - Rich content support
 * - Action buttons
 * 
 * @example
 * const toast = useToast()
 * 
 * toast.success('Item created!')
 * toast.error('Something went wrong')
 * toast.promise(saveData(), {
 *   loading: 'Saving...',
 *   success: 'Saved!',
 *   error: 'Failed to save'
 * })
 */

type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading'

interface ToastAction {
  label: string
  onClick: () => void
  variant?: 'primary' | 'secondary'
}

interface Toast {
  id: string
  type: ToastType
  title?: string
  message: string
  duration?: number
  action?: ToastAction
  onDismiss?: () => void
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  updateToast: (id: string, updates: Partial<Toast>) => void
  success: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) => string
  error: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) => string
  warning: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) => string
  info: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) => string
  loading: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) => string
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: any) => string)
    },
    options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>
  ) => Promise<T>
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

interface ToastProviderProps {
  children: ReactNode
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'bottom-center'
  maxToasts?: number
}

export function ToastProvider({
  children,
  position = 'bottom-right',
  maxToasts = 5,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>): string => {
    const id = Math.random().toString(36).substr(2, 9)
    
    setToasts((prev) => {
      const newToasts = [...prev, { ...toast, id }]
      // Keep only the last maxToasts
      return newToasts.slice(-maxToasts)
    })

    return id
  }, [maxToasts])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const updateToast = useCallback((id: string, updates: Partial<Toast>) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
    )
  }, [])

  const success = useCallback((message: string, options?: any) => {
    return addToast({ type: 'success', message, duration: 4000, ...options })
  }, [addToast])

  const error = useCallback((message: string, options?: any) => {
    return addToast({ type: 'error', message, duration: 6000, ...options })
  }, [addToast])

  const warning = useCallback((message: string, options?: any) => {
    return addToast({ type: 'warning', message, duration: 5000, ...options })
  }, [addToast])

  const info = useCallback((message: string, options?: any) => {
    return addToast({ type: 'info', message, duration: 4000, ...options })
  }, [addToast])

  const loading = useCallback((message: string, options?: any) => {
    return addToast({ type: 'loading', message, duration: Infinity, ...options })
  }, [addToast])

  const promise = useCallback(async <T,>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: any) => string)
    },
    options?: any
  ): Promise<T> => {
    const id = addToast({
      type: 'loading',
      message: messages.loading,
      duration: Infinity,
      ...options,
    })

    try {
      const data = await promise
      const successMessage = typeof messages.success === 'function'
        ? messages.success(data)
        : messages.success
      
      updateToast(id, {
        type: 'success',
        message: successMessage,
        duration: 4000,
      })
      
      return data
    } catch (err) {
      const errorMessage = typeof messages.error === 'function'
        ? messages.error(err)
        : messages.error
      
      updateToast(id, {
        type: 'error',
        message: errorMessage,
        duration: 6000,
      })
      
      throw err
    }
  }, [addToast, updateToast])

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    updateToast,
    success,
    error,
    warning,
    info,
    loading,
    promise,
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} position={position} onDismiss={removeToast} />
    </ToastContext.Provider>
  )
}

interface ToastContainerProps {
  toasts: Toast[]
  position: ToastProviderProps['position']
  onDismiss: (id: string) => void
}

function ToastContainer({ toasts, position, onDismiss }: ToastContainerProps) {
  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  }

  return (
    <div
      className={cn(
        'fixed z-50 flex flex-col gap-2 pointer-events-none',
        positionClasses[position]
      )}
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={() => onDismiss(toast.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}

interface ToastItemProps {
  toast: Toast
  onDismiss: () => void
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-success" />,
    error: <AlertCircle className="w-5 h-5 text-error" />,
    warning: <AlertTriangle className="w-5 h-5 text-warning" />,
    info: <Info className="w-5 h-5 text-primary" />,
    loading: <Loader2 className="w-5 h-5 text-primary animate-spin" />,
  }

  const borderColors = {
    success: 'border-success/30',
    error: 'border-error/30',
    warning: 'border-warning/30',
    info: 'border-primary/30',
    loading: 'border-primary/30',
  }

  const [isPaused, setIsPaused] = useState(false)
  const [progress, setProgress] = useState(100)
  const duration = toast.duration ?? 4000

  // Auto-dismiss with progress
  useState(() => {
    if (duration === Infinity || toast.type === 'loading') return

    const startTime = Date.now()
    const interval = setInterval(() => {
      if (isPaused) return
      
      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100)
      setProgress(remaining)

      if (remaining <= 0) {
        clearInterval(interval)
        onDismiss()
      }
    }, 16)

    return () => clearInterval(interval)
  })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      className={cn(
        'pointer-events-auto min-w-[320px] max-w-md',
        'glass-card rounded-xl overflow-hidden',
        'border-l-4',
        borderColors[toast.type]
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <div className="flex-shrink-0 mt-0.5">{icons[toast.type]}</div>
        
        <div className="flex-1 min-w-0">
          {toast.title && (
            <h4 className="font-medium text-sm text-foreground mb-1">
              {toast.title}
            </h4>
          )}
          <p className="text-sm text-foreground-muted leading-relaxed">
            {toast.message}
          </p>
          
          {toast.action && (
            <button
              onClick={() => {
                toast.action?.onClick()
                onDismiss()
              }}
              className={cn(
                'mt-2 text-xs font-medium',
                toast.action.variant === 'primary'
                  ? 'text-primary hover:text-primary/80'
                  : 'text-foreground-muted hover:text-foreground'
              )}
            >
              {toast.action.label}
            </button>
          )}
        </div>

        <button
          onClick={onDismiss}
          className="flex-shrink-0 p-1 text-foreground-muted hover:text-foreground transition-colors"
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress bar */}
      {duration !== Infinity && toast.type !== 'loading' && (
        <div className="h-0.5 bg-surface">
          <motion.div
            className={cn(
              'h-full',
              toast.type === 'success' && 'bg-success',
              toast.type === 'error' && 'bg-error',
              toast.type === 'warning' && 'bg-warning',
              toast.type === 'info' && 'bg-primary'
            )}
            style={{ width: `${progress}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      )}
    </motion.div>
  )
}

// Standalone toast function for use outside React components
let toastInstance: ToastContextValue | null = null

export function setToastInstance(instance: ToastContextValue) {
  toastInstance = instance
}

export const toast = {
  success: (message: string, options?: any) => 
    toastInstance?.success(message, options) ?? '',
  error: (message: string, options?: any) => 
    toastInstance?.error(message, options) ?? '',
  warning: (message: string, options?: any) => 
    toastInstance?.warning(message, options) ?? '',
  info: (message: string, options?: any) => 
    toastInstance?.info(message, options) ?? '',
  loading: (message: string, options?: any) => 
    toastInstance?.loading(message, options) ?? '',
  promise: <T,>(promise: Promise<T>, messages: any, options?: any) =>
    toastInstance?.promise(promise, messages, options) ?? promise,
}
