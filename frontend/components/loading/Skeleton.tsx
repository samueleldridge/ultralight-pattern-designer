'use client'

import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

/**
 * Skeleton - Loading placeholder component
 * Used for showing loading state of content that will be loaded
 * 
 * Inspired by: Linear, Vercel, Raycast
 * 
 * @example
 * <Skeleton className="h-4 w-32" />
 * <Skeleton className="h-20 w-full" variant="card" />
 */
interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'card' | 'circle' | 'text' | 'avatar'
  animate?: boolean
  shimmer?: boolean
}

export function Skeleton({
  className,
  variant = 'default',
  animate = true,
  shimmer = true,
  ...props
}: SkeletonProps) {
  const variants = {
    default: 'rounded-lg',
    card: 'rounded-2xl',
    circle: 'rounded-full',
    text: 'rounded',
    avatar: 'rounded-full',
  }

  return (
    <div
      className={cn(
        'bg-surface',
        variants[variant],
        animate && 'animate-pulse',
        shimmer && 'relative overflow-hidden',
        className
      )}
      {...props}
    >
      {shimmer && (
        <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
      )}
    </div>
  )
}

/**
 * SkeletonText - Multi-line text skeleton
 * 
 * @example
 * <SkeletonText lines={3} className="space-y-2" />
 */
interface SkeletonTextProps {
  lines?: number
  lineHeight?: string
  lastLineWidth?: string
  className?: string
}

export function SkeletonText({
  lines = 3,
  lineHeight = 'h-4',
  lastLineWidth = 'w-3/4',
  className,
}: SkeletonTextProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            lineHeight,
            i === lines - 1 ? lastLineWidth : 'w-full'
          )}
          variant="text"
        />
      ))}
    </div>
  )
}

/**
 * SkeletonCard - Card-shaped skeleton with header and content
 * 
 * @example
 * <SkeletonCard hasHeader hasFooter />
 */
interface SkeletonCardProps {
  hasHeader?: boolean
  hasFooter?: boolean
  contentLines?: number
  className?: string
}

export function SkeletonCard({
  hasHeader = true,
  hasFooter = false,
  contentLines = 3,
  className,
}: SkeletonCardProps) {
  return (
    <div className={cn('glass-card rounded-2xl overflow-hidden', className)}>
      {hasHeader && (
        <div className="p-4 border-b border-border/50 flex items-center gap-3">
          <Skeleton className="w-8 h-8 rounded-lg" variant="circle" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      )}
      
      <div className="p-4">
        <SkeletonText lines={contentLines} />
      </div>
      
      {hasFooter && (
        <div className="p-4 border-t border-border/50 flex justify-between">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-24" />
        </div>
      )}
    </div>
  )
}

/**
 * SkeletonTable - Table skeleton
 * 
 * @example
 * <SkeletonTable rows={5} columns={4} />
 */
interface SkeletonTableProps {
  rows?: number
  columns?: number
  hasHeader?: boolean
  className?: string
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  hasHeader = true,
  className,
}: SkeletonTableProps) {
  return (
    <div className={cn('w-full', className)}>
      {hasHeader && (
        <div className="flex gap-4 pb-3 border-b border-border">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
      )}
      <div className="space-y-3 pt-3">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                className={cn(
                  'h-10',
                  colIndex === 0 ? 'flex-[2]' : 'flex-1'
                )}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * SkeletonChart - Chart skeleton
 * 
 * @example
 * <SkeletonChart type="line" />
 */
interface SkeletonChartProps {
  type?: 'line' | 'bar' | 'pie'
  className?: string
}

export function SkeletonChart({ type = 'line', className }: SkeletonChartProps) {
  if (type === 'pie') {
    return (
      <div className={cn('flex items-center justify-center', className)}>
        <Skeleton className="w-40 h-40 rounded-full" />
      </div>
    )
  }

  return (
    <div className={cn('relative h-64', className)}>
      {/* Axis lines */}
      <div className="absolute left-0 top-0 bottom-8 w-px bg-border" />
      <div className="absolute left-0 right-0 bottom-8 h-px bg-border" />
      
      {/* Bars or area */}
      <div className="absolute left-4 right-0 top-4 bottom-12 flex items-end gap-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1 rounded-t-lg"
            style={{
              height: `${30 + Math.random() * 50}%`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * SkeletonList - List item skeletons
 * 
 * @example
 * <SkeletonList items={5} />
 */
interface SkeletonListProps {
  items?: number
  hasAvatar?: boolean
  hasAction?: boolean
  className?: string
}

export function SkeletonList({
  items = 5,
  hasAvatar = true,
  hasAction = true,
  className,
}: SkeletonListProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3">
          {hasAvatar && (
            <Skeleton className="w-10 h-10 rounded-full flex-shrink-0" />
          )}
          <div className="flex-1 min-w-0 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          {hasAction && (
            <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * SkeletonChat - Chat message skeletons
 * 
 * @example
 * <SkeletonChat messages={3} />
 */
interface SkeletonChatProps {
  messages?: number
  className?: string
}

export function SkeletonChat({ messages = 3, className }: SkeletonChatProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {Array.from({ length: messages }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'flex gap-3',
            i % 2 === 0 ? 'flex-row' : 'flex-row-reverse'
          )}
        >
          <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
          <div className={cn(
            'max-w-[70%] space-y-2',
            i % 2 === 0 ? 'items-start' : 'items-end'
          )}>
            <Skeleton className={cn(
              'h-20 w-64 rounded-2xl',
              i % 2 === 0 ? 'rounded-tl-sm' : 'rounded-tr-sm'
            )} />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * PageSkeleton - Full page skeleton layout
 * 
 * @example
 * <PageSkeleton />
 */
export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="h-16 border-b border-border px-6 flex items-center gap-4">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <Skeleton className="h-6 w-32" />
        <div className="flex-1" />
        <Skeleton className="h-10 w-64 rounded-lg" />
        <Skeleton className="w-10 h-10 rounded-full" />
      </div>
      
      <div className="flex h-[calc(100vh-64px)]">
        {/* Sidebar */}
        <div className="w-72 border-r border-border p-4 space-y-4">
          <Skeleton className="h-10 w-full rounded-xl" />
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-lg" />
            ))}
          </div>
        </div>
        
        {/* Main content */}
        <div className="flex-1 p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} contentLines={4} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * LoadingOverlay - Full screen loading overlay
 * 
 * @example
 * <LoadingOverlay isLoading={isLoading} />
 */
interface LoadingOverlayProps {
  isLoading: boolean
  message?: string
  className?: string
}

export function LoadingOverlay({
  isLoading,
  message = 'Loading...',
  className,
}: LoadingOverlayProps) {
  if (!isLoading) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm',
        className
      )}
    >
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-12 h-12">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-primary/30"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            style={{ borderTopColor: 'hsl(var(--primary))' }}
          />
        </div>
        <p className="text-sm text-foreground-muted">{message}</p>
      </div>
    </motion.div>
  )
}

/**
 * LoadingSpinner - Simple loading spinner
 * 
 * @example
 * <LoadingSpinner size="lg" />
 */
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12',
  }

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-2 border-primary/30',
        'border-t-primary',
        sizes[size],
        className
      )}
    />
  )
}

/**
 * LoadingDots - Animated loading dots
 * 
 * @example
 * <LoadingDots />
 */
interface LoadingDotsProps {
  className?: string
}

export function LoadingDots({ className }: LoadingDotsProps) {
  return (
    <div className={cn('flex gap-1', className)}>
      {Array.from({ length: 3 }).map((_, i) => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-foreground-muted"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  )
}

/**
 * PulseBadge - Pulsing badge for real-time updates
 * 
 * @example
 * <PulseBadge>Live</PulseBadge>
 */
interface PulseBadgeProps {
  children: React.ReactNode
  color?: 'primary' | 'success' | 'warning' | 'error'
  className?: string
}

export function PulseBadge({
  children,
  color = 'success',
  className,
}: PulseBadgeProps) {
  const colors = {
    primary: 'bg-primary text-primary-foreground',
    success: 'bg-success text-white',
    warning: 'bg-warning text-white',
    error: 'bg-error text-white',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        colors[color],
        className
      )}
    >
      <span className="relative flex h-2 w-2">
        <span className={cn(
          'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
          color === 'primary' ? 'bg-primary' :
          color === 'success' ? 'bg-success' :
          color === 'warning' ? 'bg-warning' : 'bg-error'
        )} />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
      </span>
      {children}
    </span>
  )
}
