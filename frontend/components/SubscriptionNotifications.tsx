'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-react'
import { 
  Bell, 
  X, 
  Sparkles, 
  ChevronRight,
  MessageSquare,
  TrendingDown,
  TrendingUp,
  Users,
  AlertTriangle
} from 'lucide-react'

interface SubscriptionNotification {
  id: string
  subscription_id: string
  subscription_name: string
  message: string
  condition_met: boolean
  rows_found: number
  executed_at: string
  action_prompt: string
}

interface SubscriptionNotificationsProps {
  onExplore: (notification: SubscriptionNotification) => void
  onDismiss: (id: string) => void
}

export function SubscriptionNotifications({ onExplore, onDismiss }: SubscriptionNotificationsProps) {
  const [notifications, setNotifications] = useState<SubscriptionNotification[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    fetchNotifications()
  }, [])

  const fetchNotifications = async () => {
    try {
      const response = await fetch('/api/subscriptions/notifications/pending?limit=10')
      if (response.ok) {
        const data = await response.json()
        setNotifications(data)
      }
    } catch (error) {
      console.error('Failed to fetch notifications:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDismiss = async (id: string) => {
    try {
      await fetch(`/api/subscriptions/notifications/${id}/view`, { method: 'POST' })
      setNotifications(prev => prev.filter(n => n.id !== id))
      onDismiss(id)
    } catch (error) {
      console.error('Failed to dismiss:', error)
    }
  }

  const handleExplore = async (notification: SubscriptionNotification) => {
    try {
      const response = await fetch(`/api/subscriptions/notifications/${notification.id}/explore`, {
        method: 'POST'
      })
      if (response.ok) {
        const data = await response.json()
        onExplore(notification)
        // Remove from list
        setNotifications(prev => prev.filter(n => n.id !== notification.id))
      }
    } catch (error) {
      console.error('Failed to explore:', error)
    }
  }

  const handleDismissAll = () => {
    notifications.forEach(n => handleDismiss(n.id))
  }

  if (isLoading) return null

  if (notifications.length === 0) return null

  const current = notifications[currentIndex]

  // Format the greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  // Get icon based on subscription type
  const getIcon = (name: string) => {
    const lower = name.toLowerCase()
    if (lower.includes('margin') || lower.includes('revenue') || lower.includes('profit')) {
      return <TrendingDown className="w-5 h-5 text-amber-400" />
    }
    if (lower.includes('customer') || lower.includes('client') || lower.includes('user')) {
      return <Users className="w-5 h-5 text-primary" />
    }
    if (lower.includes('alert') || lower.includes('warning')) {
      return <AlertTriangle className="w-5 h-5 text-red-400" />
    }
    return <Sparkles className="w-5 h-5 text-primary" />
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="glass-card rounded-xl overflow-hidden border border-primary/20"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-primary/5 border-b border-primary/10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
              <Bell className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h4 className="text-sm font-medium">Subscription Updates</h4>
              <p className="text-xs text-foreground-muted">
                {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {notifications.length > 1 && (
              <span className="text-xs text-foreground-muted">
                {currentIndex + 1} / {notifications.length}
              </span>
            )}
            <button
              onClick={handleDismissAll}
              className="p-1.5 hover:bg-surface rounded-lg transition-colors"
              title="Dismiss all"
            >
              <X className="w-4 h-4 text-foreground-muted" />
            </button>
          </div>
        </div>

        {/* Notification Content */}
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-surface flex items-center justify-center shrink-0">
              {getIcon(current.subscription_name)}
            </div>
            <div className="flex-1">
              {/* Personalized greeting + message */}
              <p className="text-sm text-foreground leading-relaxed">
                <span className="font-medium">{getGreeting()}</span>, {current.message}
              </p>

              {/* Result summary */}
              {current.condition_met && current.rows_found > 0 && (
                <div className="mt-3 p-3 bg-surface rounded-lg">
                  <div className="flex items-center gap-2 text-sm">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <span>Found <strong>{current.rows_found}</strong> matching records</span>
                  </div>
                </div>
              )}

              {/* Action prompt */}
              <p className="mt-3 text-sm text-foreground-muted">
                {current.action_prompt}
              </p>

              {/* Actions */}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => handleExplore(current)}
                  className="btn-primary flex items-center gap-2 text-sm"
                >
                  <MessageSquare className="w-4 h-4" />
                  Yes, dive in
                </button>
                <button
                  onClick={() => handleDismiss(current.id)}
                  className="btn-secondary text-sm"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation dots for multiple notifications */}
        {notifications.length > 1 && (
          <div className="flex justify-center gap-1.5 pb-4">
            {notifications.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  idx === currentIndex ? 'bg-primary' : 'bg-surface'
                }`}
              />
            ))}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// Simpler inline notification for chat interface
export function InlineSubscriptionNotification({ 
  notification, 
  onExplore,
  onDismiss 
}: { 
  notification: SubscriptionNotification
  onExplore: (n: SubscriptionNotification) => void
  onDismiss: (id: string) => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-3 p-4 rounded-xl bg-gradient-to-r from-primary/10 to-accent/5 border border-primary/20"
    >
      <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center shrink-0">
        <Sparkles className="w-5 h-5 text-primary" />
      </div>
      <div className="flex-1">
        <p className="text-sm text-foreground">{notification.message}</p>
        <p className="text-xs text-foreground-muted mt-1">
          {notification.action_prompt}
        </p>
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => onExplore(notification)}
            className="text-xs px-3 py-1.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            Explore
          </button>
          <button
            onClick={() => onDismiss(notification.id)}
            className="text-xs px-3 py-1.5 text-foreground-muted hover:text-foreground transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </motion.div>
  )
}
