'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/hooks/useA11y'

/**
 * MobileSidebar - Responsive sidebar that becomes a drawer on mobile
 * 
 * @example
 * <MobileSidebar>
 *   <SidebarContent />
 * </MobileSidebar>
 */
interface MobileSidebarProps {
  children: React.ReactNode
  className?: string
}

export function MobileSidebar({ children, className }: MobileSidebarProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const prefersReducedMotion = useReducedMotion()

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-40 p-2 rounded-lg bg-surface border border-border 
                 text-foreground shadow-lg"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Desktop sidebar */}
      <aside className={cn(
        'hidden lg:block h-screen glass-card border-r border-border/50',
        className
      )}>
        {children}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {isOpen && isMobile && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setIsOpen(false)}
            />

            {/* Drawer */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ 
                type: 'spring',
                damping: 25,
                stiffness: 300,
                duration: prefersReducedMotion ? 0 : undefined
              }}
              className={cn(
                'fixed top-0 left-0 h-full w-72 z-50',
                'glass-card border-r border-border/50',
                'lg:hidden',
                className
              )}
            >
              {/* Close button */}
              <div className="flex items-center justify-between p-4 border-b border-border/50">
                <span className="font-semibold">Menu</span>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-surface rounded-lg transition-colors"
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="h-[calc(100vh-65px)] overflow-y-auto">
                {children}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

/**
 * MobileBottomNav - Bottom navigation for mobile apps
 * 
 * @example
 * <MobileBottomNav
 *   items={[
 *     { icon: Home, label: 'Home', href: '/' },
 *     { icon: Search, label: 'Search', href: '/search' },
 *     { icon: Settings, label: 'Settings', href: '/settings' },
 *   ]}
 * />
 */
interface BottomNavItem {
  icon: React.ComponentType<{ className?: string }>
  label: string
  href?: string
  onClick?: () => void
  isActive?: boolean
}

interface MobileBottomNavProps {
  items: BottomNavItem[]
  className?: string
}

export function MobileBottomNav({ items, className }: MobileBottomNavProps) {
  const handleClick = (item: BottomNavItem) => {
    if (item.onClick) {
      item.onClick()
    }
  }

  return (
    <nav className={cn(
      'fixed bottom-0 left-0 right-0 z-40',
      'lg:hidden',
      className
    )}>
      <div className="glass-card border-t border-border/50 px-2 pb-safe">
        <div className="flex items-center justify-around">
          {items.map((item, index) => {
            const Icon = item.icon
            const isActive = item.isActive

            return (
              <button
                key={index}
                onClick={() => handleClick(item)}
                className={cn(
                  'flex flex-col items-center justify-center py-2 px-3 min-w-[64px]',
                  'text-foreground-muted hover:text-foreground transition-colors',
                  isActive && 'text-primary'
                )}
              >
                <div className={cn(
                  'p-1.5 rounded-xl transition-colors',
                  isActive && 'bg-primary/10'
                )}>
                  <Icon className={cn(
                    'w-5 h-5',
                    isActive && 'text-primary'
                  )} />
                </div>
                <span className="text-[10px] mt-0.5 font-medium">{item.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

/**
 * MobileChatPanel - Mobile-optimized chat panel
 * 
 * @example
 * <MobileChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)}>
 *   <ChatInterface />
 * </MobileChatPanel>
 */
interface MobileChatPanelProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
}

export function MobileChatPanel({
  isOpen,
  onClose,
  children,
  className,
}: MobileChatPanelProps) {
  const prefersReducedMotion = useReducedMotion()

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{
              type: 'spring',
              damping: 25,
              stiffness: 300,
              duration: prefersReducedMotion ? 0 : undefined
            }}
            className={cn(
              'fixed inset-x-0 bottom-0 z-50',
              'h-[85vh] rounded-t-3xl',
              'glass-card border-t border-border/50',
              'flex flex-col',
              className
            )}
          >
            {/* Handle bar */}
            <div className="flex justify-center pt-3 pb-1" onClick={onClose}>
              <div className="w-12 h-1.5 rounded-full bg-border" />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

/**
 * ResponsiveContainer - Container with responsive padding
 * 
 * @example
 * <ResponsiveContainer>
 *   <DashboardContent />
 * </ResponsiveContainer>
 */
interface ResponsiveContainerProps {
  children: React.ReactNode
  className?: string
}

export function ResponsiveContainer({ children, className }: ResponsiveContainerProps) {
  return (
    <div className={cn(
      'w-full mx-auto',
      'px-4 sm:px-6 lg:px-8',
      'max-w-7xl',
      className
    )}>
      {children}
    </div>
  )
}

/**
 * TouchFriendly - Wrapper that increases touch targets on mobile
 * 
 * @example
 * <TouchFriendly>
 *   <Button>Click me</Button>
 * </TouchFriendly>
 */
interface TouchFriendlyProps {
  children: React.ReactNode
  minHeight?: string
  className?: string
}

export function TouchFriendly({
  children,
  minHeight = '44px',
  className,
}: TouchFriendlyProps) {
  return (
    <div 
      className={cn('touch-manipulation', className)}
      style={{ minHeight }}
    >
      {children}
    </div>
  )
}

/**
 * PullToRefresh - Pull to refresh functionality for mobile
 * 
 * @example
 * <PullToRefresh onRefresh={async () => await refetch()}>
 *   <ScrollableContent />
 * </PullToRefresh>
 */
interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  children: React.ReactNode
  className?: string
}

export function PullToRefresh({ onRefresh, children, className }: PullToRefreshProps) {
  const [pulling, setPulling] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const startY = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleTouchStart = (e: React.TouchEvent) => {
    if (containerRef.current?.scrollTop === 0) {
      startY.current = e.touches[0].clientY
      setPulling(true)
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!pulling) return

    const y = e.touches[0].clientY
    const diff = y - startY.current

    if (diff > 0 && diff < 150) {
      setPullDistance(diff)
      e.preventDefault()
    }
  }

  const handleTouchEnd = async () => {
    if (!pulling) return

    if (pullDistance > 80) {
      setRefreshing(true)
      await onRefresh()
      setRefreshing(false)
    }

    setPulling(false)
    setPullDistance(0)
  }

  return (
    <div
      ref={containerRef}
      className={cn('overflow-y-auto', className)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{
        transform: pulling ? `translateY(${pullDistance * 0.5}px)` : undefined,
        transition: pulling ? undefined : 'transform 0.3s ease-out',
      }}
    >
      {/* Pull indicator */}
      <div
        className="flex items-center justify-center h-0 overflow-visible"
        style={{
          opacity: Math.min(pullDistance / 80, 1),
        }}
      >
        {refreshing ? (
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        ) : (
          <motion.div
            animate={{ rotate: pullDistance > 80 ? 180 : 0 }}
            className="text-primary"
          >
            ↓
          </motion.div>
        )}
      </div>

      {children}
    </div>
  )
}

// Safe area insets for mobile
export function useSafeArea() {
  const [safeArea, setSafeArea] = useState({
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  })

  useEffect(() => {
    // Get CSS safe area insets
    const styles = getComputedStyle(document.documentElement)
    setSafeArea({
      top: parseInt(styles.getPropertyValue('--sat') || '0'),
      bottom: parseInt(styles.getPropertyValue('--sab') || '0'),
      left: parseInt(styles.getPropertyValue('--sal') || '0'),
      right: parseInt(styles.getPropertyValue('--sar') || '0'),
    })
  }, [])

  return safeArea
}
