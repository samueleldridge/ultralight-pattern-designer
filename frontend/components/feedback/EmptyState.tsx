'use client'

import { motion } from 'framer-motion'
import { 
  Search, 
  Inbox, 
  FileX, 
  Database, 
  FolderOpen,
  AlertTriangle,
  Plus,
  RefreshCw,
  ArrowRight
} from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * EmptyState - Consistent empty state component
 * 
 * Inspired by: Linear, Vercel, GitHub
 * 
 * @example
 * <EmptyState
 *   icon={Inbox}
 *   title="No messages"
 *   description="Your inbox is empty. Start a conversation!"
 *   action={{ label: 'New message', onClick: () => {} }}
 * />
 */
interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    icon?: React.ComponentType<{ className?: string }>
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  variant?: 'default' | 'compact' | 'inline'
  className?: string
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  secondaryAction,
  variant = 'default',
  className,
}: EmptyStateProps) {
  const variants = {
    default: 'p-12',
    compact: 'p-8',
    inline: 'p-4',
  }

  const iconSizes = {
    default: 'w-16 h-16',
    compact: 'w-12 h-12',
    inline: 'w-8 h-8',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex flex-col items-center justify-center text-center',
        variants[variant],
        className
      )}
    >
      <div className={cn(
        'rounded-2xl bg-surface flex items-center justify-center mb-4',
        iconSizes[variant]
      )}>
        <Icon className={cn(
          'text-foreground-subtle',
          variant === 'default' ? 'w-8 h-8' : variant === 'compact' ? 'w-6 h-6' : 'w-4 h-4'
        )} />
      </div>

      <h3 className={cn(
        'font-semibold text-foreground',
        variant === 'default' ? 'text-lg' : variant === 'compact' ? 'text-base' : 'text-sm'
      )}>
        {title}
      </h3>

      {description && (
        <p className={cn(
          'text-foreground-muted max-w-sm mt-2',
          variant === 'inline' ? 'text-xs' : 'text-sm'
        )}>
          {description}
        </p>
      )}

      {(action || secondaryAction) && (
        <div className={cn(
          'flex items-center gap-3 mt-6',
          variant === 'inline' && 'mt-3'
        )}>
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                'btn-primary flex items-center gap-2',
                variant === 'inline' && 'px-3 py-1.5 text-xs'
              )}
            >
              {action.icon && <action.icon className="w-4 h-4" />}
              {!action.icon && <Plus className="w-4 h-4" />}
              {action.label}
            </button>
          )}
          
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className={cn(
                'btn-secondary',
                variant === 'inline' && 'px-3 py-1.5 text-xs'
              )}
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </motion.div>
  )
}

/**
 * EmptySearch - Empty state for search results
 * 
 * @example
 * <EmptySearch query="machine learning" onClear={() => setQuery('')} />
 */
interface EmptySearchProps {
  query: string
  onClear: () => void
  suggestions?: string[]
  onSuggestionClick?: (suggestion: string) => void
  className?: string
}

export function EmptySearch({
  query,
  onClear,
  suggestions = [],
  onSuggestionClick,
  className,
}: EmptySearchProps) {
  return (
    <EmptyState
      icon={Search}
      title={`No results for "${query}"`}
      description="Try adjusting your search terms or browse the suggestions below."
      variant="default"
      className={className}
      secondaryAction={{
        label: 'Clear search',
        onClick: onClear,
      }}
    >
      {suggestions.length > 0 && (
        <div className="mt-6">
          <p className="text-xs text-foreground-muted uppercase tracking-wider mb-3">
            Popular searches
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick?.(suggestion)}
                className="px-3 py-1.5 text-sm bg-surface hover:bg-surface-elevated 
                         border border-border rounded-lg transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </EmptyState>
  )
}

/**
 * EmptyDashboard - Empty state for dashboard
 * 
 * @example
 * <EmptyDashboard onCreate={() => {}} />
 */
interface EmptyDashboardProps {
  onCreate: () => void
  onExploreTemplates?: () => void
  className?: string
}

export function EmptyDashboard({
  onCreate,
  onExploreTemplates,
  className,
}: EmptyDashboardProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-12', className)}>
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="relative"
      >
        {/* Animated background */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 blur-3xl rounded-full" />
        
        <div className="relative w-24 h-24 rounded-3xl bg-surface border border-border 
                      flex items-center justify-center">
          <Database className="w-10 h-10 text-primary" />
        </div>
      </motion.div>

      <h2 className="text-xl font-semibold mt-8 mb-2">Welcome to your dashboard</h2>
      <p className="text-foreground-muted text-center max-w-md mb-8">
        Start by creating your first view or ask the AI Analyst to generate insights for you.
      </p>

      <div className="flex flex-col sm:flex-row gap-3">
        <button onClick={onCreate} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Create your first view
        </button>
        
        {onExploreTemplates && (
          <button 
            onClick={onExploreTemplates}
            className="btn-secondary flex items-center gap-2 group"
          >
            Explore templates
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * EmptyChat - Empty state for chat interface
 * 
 * @example
 * <EmptyChat suggestions={['Revenue this month', 'Top customers']} onSuggestionClick={handleQuery} />
 */
interface EmptyChatProps {
  suggestions?: string[]
  onSuggestionClick?: (suggestion: string) => void
  title?: string
  description?: string
  className?: string
}

export function EmptyChat({
  suggestions = [],
  onSuggestionClick,
  title = 'What would you like to know?',
  description = 'Ask me anything about your data and I\'ll analyze it step by step',
  className,
}: EmptyChatProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center p-6', className)}>
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 
                  flex items-center justify-center mb-6"
      >
        <Database className="w-10 h-10 text-primary" />
      </motion.div>
      
      <div>
        <p className="text-foreground font-medium text-lg">{title}</p>
        <p className="text-sm text-foreground-muted mt-2 max-w-xs">
          {description}
        </p>
      </div>
      
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 justify-center max-w-sm mt-6">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => onSuggestionClick?.(suggestion)}
              className="px-3 py-1.5 text-xs bg-surface hover:bg-surface-elevated 
                       border border-border rounded-full transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * ErrorState - Error state with retry action
 * 
 * @example
 * <ErrorState 
 *   error={error}
 *   onRetry={() => refetch()}
 *   onGoHome={() => router.push('/')}
 * />
 */
interface ErrorStateProps {
  error?: Error | null
  title?: string
  description?: string
  onRetry?: () => void
  onGoHome?: () => void
  className?: string
}

export function ErrorState({
  error,
  title = 'Something went wrong',
  description = 'We encountered an error while loading your data. Please try again.',
  onRetry,
  onGoHome,
  className,
}: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex flex-col items-center justify-center text-center p-12',
        className
      )}
    >
      <div className="w-16 h-16 rounded-2xl bg-error/10 flex items-center justify-center mb-4">
        <AlertTriangle className="w-8 h-8 text-error" />
      </div>

      <h3 className="font-semibold text-lg text-foreground">{title}</h3>
      <p className="text-sm text-foreground-muted max-w-sm mt-2">
        {error?.message || description}
      </p>

      <div className="flex items-center gap-3 mt-6">
        {onRetry && (
          <button onClick={onRetry} className="btn-primary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>
        )}
        
        {onGoHome && (
          <button onClick={onGoHome} className="btn-secondary">
            Go home
          </button>
        )}
      </div>
    </motion.div>
  )
}

/**
 * NoDataState - Empty state for data tables/lists
 * 
 * @example
 * <NoDataState type="files" onUpload={() => {}} />
 */
interface NoDataStateProps {
  type?: 'files' | 'records' | 'items' | 'results'
  onAction?: () => void
  actionLabel?: string
  className?: string
}

export function NoDataState({
  type = 'items',
  onAction,
  actionLabel,
  className,
}: NoDataStateProps) {
  const config = {
    files: {
      icon: FolderOpen,
      title: 'No files yet',
      description: 'Upload your first file to get started',
      defaultAction: 'Upload file',
    },
    records: {
      icon: FileX,
      title: 'No records found',
      description: 'There are no records to display at this time',
      defaultAction: 'Add record',
    },
    items: {
      icon: Inbox,
      title: 'No items yet',
      description: 'Get started by creating your first item',
      defaultAction: 'Create item',
    },
    results: {
      icon: Search,
      title: 'No results',
      description: 'Try adjusting your filters to see more results',
      defaultAction: undefined,
    },
  }

  const { icon, title, description, defaultAction } = config[type]

  return (
    <EmptyState
      icon={icon}
      title={title}
      description={description}
      action={onAction ? {
        label: actionLabel || defaultAction || 'Get started',
        onClick: onAction,
      } : undefined}
      className={className}
    />
  )
}

/**
 * LoadingEmptyState - Shows skeleton while loading, then empty state
 * 
 * @example
 * <LoadingEmptyState
 *   isLoading={isLoading}
 *   hasData={data.length > 0}
 *   skeleton={<SkeletonList items={5} />}
 *   empty={<NoDataState type="items" />}
 * >
 *   {children}
 * </LoadingEmptyState>
 */
interface LoadingEmptyStateProps {
  isLoading: boolean
  hasData: boolean
  skeleton: React.ReactNode
  empty: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function LoadingEmptyState({
  isLoading,
  hasData,
  skeleton,
  empty,
  children,
  className,
}: LoadingEmptyStateProps) {
  if (isLoading) {
    return <div className={className}>{skeleton}</div>
  }

  if (!hasData) {
    return <div className={className}>{empty}</div>
  }

  return <>{children}</>
}
