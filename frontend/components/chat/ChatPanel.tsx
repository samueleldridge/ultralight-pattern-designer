'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X, Minimize2, MessageSquare } from 'lucide-react'
import { ChatInterface } from './ChatInterface'
import { toast } from 'sonner'

interface ChatPanelProps {
  onAddView?: (view: {
    title: string
    query: string
    data: unknown
    type?: string
  }) => void
}

/**
 * ChatPanel Component
 * 
 * Wrapper component for ChatInterface that provides:
 * - Minimize/expand toggle
 * - Floating action button when minimized
 * - Badge showing unread message count
 */
export function ChatPanel({ onAddView }: ChatPanelProps) {
  const [isMinimized, setIsMinimized] = useState(false)
  const [unreadCount] = useState(0)

  const handleMinimize = () => {
    setIsMinimized(true)
    toast.info('Chat minimized', {
      description: 'Click the AI button to reopen',
    })
  }

  const handleExpand = () => {
    setIsMinimized(false)
  }

  return (
    <div className="fixed right-0 bottom-0 z-50">
      <AnimatePresence mode="wait">
        {isMinimized ? (
          <motion.button
            key="minimized"
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleExpand}
            className="fixed right-6 bottom-6 btn-primary flex items-center gap-2 px-5 py-3 rounded-full shadow-2xl shadow-primary/30"
          >
            <div className="relative">
              <Sparkles className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-error text-error-foreground text-[10px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </div>
            <span className="font-medium">Ask AI</span>
          </motion.button>
        ) : (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <ChatInterface 
              onAddView={onAddView}
              onClose={handleMinimize}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default ChatPanel
