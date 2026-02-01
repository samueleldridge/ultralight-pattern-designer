'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Bell,
  HelpCircle,
  Settings,
  LogOut,
  User,
  Moon,
  Sun,
  Sparkles,
  ChevronDown,
  Command,
  CreditCard,
  Keyboard,
} from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as Avatar from '@radix-ui/react-avatar'
import { toast } from 'sonner'
import { useTheme } from '@/components/ThemeProvider'

/**
 * Header Component
 * 
 * Main application header featuring:
 * - Global search with keyboard shortcut
 * - Theme toggle
 * - Notifications dropdown
 * - User profile menu
 * 
 * Design inspired by Linear.app and Vercel
 */
export function Header() {
  const { resolvedTheme, setTheme } = useTheme()
  const [notifications] = useState([
    { 
      id: 1, 
      title: 'New insight available', 
      message: 'Revenue anomaly detected in Q4 data', 
      time: '2m ago', 
      unread: true,
      type: 'insight' as const
    },
    { 
      id: 2, 
      title: 'Query completed', 
      message: 'Weekly report is ready for review', 
      time: '1h ago', 
      unread: true,
      type: 'success' as const
    },
    { 
      id: 3, 
      title: 'System update', 
      message: 'New AI features available', 
      time: '3h ago', 
      unread: false,
      type: 'info' as const
    },
  ])
  
  const unreadCount = notifications.filter(n => n.unread).length

  const handleThemeToggle = () => {
    const newTheme = resolvedTheme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    toast.success(`Switched to ${newTheme} mode`)
  }

  const handleSearchFocus = () => {
    toast.info('Global search coming soon! Try Cmd+K', {
      icon: <Keyboard className="w-4 h-4" />,
    })
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'insight':
        return <div className="w-2 h-2 rounded-full bg-primary" />
      case 'success':
        return <div className="w-2 h-2 rounded-full bg-success" />
      default:
        return <div className="w-2 h-2 rounded-full bg-foreground-subtle" />
    }
  }

  return (
    <header className="h-16 glass-card border-b border-border/50 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-40">
      {/* Search Bar */}
      <div className="flex-1 max-w-2xl">
        <div 
          className="relative group cursor-pointer"
          onClick={handleSearchFocus}
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-subtle group-focus-within:text-primary transition-colors" />
          <input
            type="text"
            placeholder="Search dashboards, queries, or ask AI..."
            className="input-field w-full pl-10 pr-12 py-2.5 text-sm cursor-pointer"
            readOnly
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium text-foreground-subtle bg-background-secondary rounded border border-border">
            <Command className="w-3 h-3" />
            <span>K</span>
          </kbd>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-1 md:gap-2">
        {/* Help Button */}
        <button 
          onClick={() => toast.info('Help center coming soon!', {
            action: {
              label: 'View Docs',
              onClick: () => window.open('/docs', '_blank'),
            },
          })}
          className="p-2 text-foreground-muted hover:text-foreground hover:bg-surface rounded-lg transition-all duration-200"
          title="Help & Support"
        >
          <HelpCircle className="w-5 h-5" />
        </button>

        {/* Theme Toggle */}
        <button
          onClick={handleThemeToggle}
          className="p-2 text-foreground-muted hover:text-foreground hover:bg-surface rounded-lg transition-all duration-200"
          title="Toggle theme"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={resolvedTheme}
              initial={{ y: -10, opacity: 0, rotate: -90 }}
              animate={{ y: 0, opacity: 1, rotate: 0 }}
              exit={{ y: 10, opacity: 0, rotate: 90 }}
              transition={{ duration: 0.2 }}
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </motion.div>
          </AnimatePresence>
        </button>

        {/* Notifications */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button className="relative p-2 text-foreground-muted hover:text-foreground hover:bg-surface rounded-lg transition-all duration-200">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <motion.span 
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute top-1.5 right-1.5 w-4 h-4 bg-error text-error-foreground text-[10px] font-semibold rounded-full flex items-center justify-center"
                >
                  {unreadCount}
                </motion.span>
              )}
            </button>
          </DropdownMenu.Trigger>
          
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="w-80 bg-surface border border-border rounded-xl shadow-xl p-2 z-50 animate-scale-in"
              sideOffset={8}
              align="end"
            >
              <div className="flex items-center justify-between px-3 py-2 border-b border-border mb-2">
                <span className="font-semibold text-sm">Notifications</span>
                {unreadCount > 0 && (
                  <button 
                    onClick={() => toast.success('All notifications marked as read')}
                    className="text-xs text-primary hover:text-primary-foreground transition-colors"
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {notifications.map((notification) => (
                  <DropdownMenu.Item
                    key={notification.id}
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-surface-hover cursor-pointer outline-none transition-colors"
                  >
                    {getNotificationIcon(notification.type)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{notification.title}</p>
                      <p className="text-xs text-foreground-muted mt-0.5">{notification.message}</p>
                      <p className="text-[10px] text-foreground-subtle mt-1">{notification.time}</p>
                    </div>
                    {notification.unread && (
                      <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-1" />
                    )}
                  </DropdownMenu.Item>
                ))}
              </div>
              <DropdownMenu.Separator className="h-px bg-border my-2" />
              <DropdownMenu.Item 
                onClick={() => toast.info('Full notification history coming soon')}
                className="text-center py-2 text-xs text-primary cursor-pointer outline-none hover:text-primary-foreground transition-colors"
              >
                View all notifications
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>

        {/* User Menu */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl hover:bg-surface transition-colors ml-1"
            >
              <Avatar.Root className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center ring-2 ring-transparent hover:ring-primary/30 transition-all">
                <Avatar.Fallback className="text-primary-foreground font-medium text-sm">SE</Avatar.Fallback>
              </Avatar.Root>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-foreground">Sam Eldridge</p>
                <p className="text-xs text-foreground-muted">Admin</p>
              </div>
              <ChevronDown className="w-4 h-4 text-foreground-muted hidden md:block" />
            </motion.button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="w-56 bg-surface border border-border rounded-xl shadow-xl p-1.5 z-50 animate-scale-in"
              sideOffset={8}
              align="end"
            >
              <div className="px-3 py-2 border-b border-border mb-1">
                <p className="font-semibold text-sm">Sam Eldridge</p>
                <p className="text-xs text-foreground-muted">sam@nexus.ai</p>
              </div>
              
              <DropdownMenu.Item 
                onClick={() => toast.info('Profile settings coming soon')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-hover cursor-pointer outline-none transition-colors text-sm"
              >
                <User className="w-4 h-4 text-foreground-muted" />
                <span>Profile</span>
              </DropdownMenu.Item>
              
              <DropdownMenu.Item 
                onClick={() => toast.info('Settings page coming soon')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-hover cursor-pointer outline-none transition-colors text-sm"
              >
                <Settings className="w-4 h-4 text-foreground-muted" />
                <span>Settings</span>
              </DropdownMenu.Item>
              
              <DropdownMenu.Item 
                onClick={() => toast.info('Billing page coming soon')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-hover cursor-pointer outline-none transition-colors text-sm"
              >
                <CreditCard className="w-4 h-4 text-foreground-muted" />
                <span>Billing</span>
              </DropdownMenu.Item>
              
              <DropdownMenu.Separator className="h-px bg-border my-1" />
              
              <DropdownMenu.Item 
                onClick={() => {
                  toast.success('Upgrade initiated', {
                    description: 'Redirecting to billing...',
                  })
                }}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 cursor-pointer outline-none transition-colors text-sm text-primary"
              >
                <Sparkles className="w-4 h-4" />
                <span>Upgrade Plan</span>
              </DropdownMenu.Item>
              
              <DropdownMenu.Separator className="h-px bg-border my-1" />
              
              <DropdownMenu.Item 
                onClick={() => toast.success('Logged out successfully')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-error/10 cursor-pointer outline-none transition-colors text-sm text-error"
              >
                <LogOut className="w-4 h-4" />
                <span>Log out</span>
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}

export default Header
