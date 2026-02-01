'use client'

import { useState } from 'react'
import { Search, Bell, User, ChevronDown } from 'lucide-react'
import { motion } from 'framer-motion'

export function Header() {
  const [notifications] = useState(3)

  return (
    <header className="h-16 glass-card border-b border-border/50 flex items-center justify-between px-6">
      {/* Search */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
          <input
            type="text"
            placeholder="Search dashboards, queries, or ask AI..."
            className="input-field w-full pl-10 pr-4"
          />
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 hover:bg-surface rounded-lg transition-colors">
          <Bell className="w-5 h-5 text-foreground-muted" />
          {notifications > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-error text-error-foreground text-[10px] font-medium rounded-full flex items-center justify-center">
              {notifications}
            </span>
          )}
        </button>

        {/* User */}
        <motion.button 
          whileHover={{ scale: 1.02 }}
          className="flex items-center gap-3 pl-2 pr-3 py-1.5 rounded-xl hover:bg-surface transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-primary-foreground font-medium text-sm">
            SE
          </div>
          <div className="hidden md:block text-left">
            <p className="text-sm font-medium">Sam Eldridge</p>
            <p className="text-xs text-foreground-muted">Admin</p>
          </div>
          <ChevronDown className="w-4 h-4 text-foreground-muted" />
        </motion.button>
      </div>
    </header>
  )
}
