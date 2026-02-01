'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Sparkles,
  X,
  ChevronDown,
  ChevronUp,
  Code2,
  BarChart3,
  Paperclip,
  Mic,
  ThumbsUp,
  ThumbsDown,
  Copy,
  RotateCcw,
  Edit3,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'

/**
 * Types
 */
type StepStatus = 'pending' | 'running' | 'complete' | 'error'
type StepCategory = 'thinking' | 'action' | 'check' | 'error' | 'default'
type MessageRole = 'user' | 'assistant'

interface Step {
  id: string
  name: string
  status: StepStatus
  message: string
  icon: string
  category: StepCategory
  progress: number
}

interface Message {
  id: string
  role: MessageRole
  content: string
  steps?: Step[]
  currentStep?: string
  sql?: string
  result?: {
    row_count: number
    columns: string[]
    data?: unknown[]
  }
  chartType?: string
  timestamp: Date
  isStreaming?: boolean
  error?: string
  rating?: 'up' | 'down' | null
}

interface ChatInterfaceProps {
  onAddView?: (view: {
    title: string
    query: string
    data: unknown
    type?: string
  }) => void
  onClose?: () => void
}

/**
 * Suggested questions for empty state
 */
const suggestedQuestions = [
  'What was our revenue last month?',
  'Show me top customers by spend',
  'Compare Q3 vs Q4 growth',
  'Which products are trending?',
  'Analyze customer churn patterns',
]

/**
 * Typing indicator animation
 */
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full bg-foreground-muted"
          animate={{ y: [0, -4, 0] }}
          transition={{ 
            duration: 0.6, 
            repeat: Infinity, 
            delay: i * 0.15,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  )
}

/**
 * Message Actions Component
 */
interface MessageActionsProps {
  onCopy: () => void
  onRegenerate: () => void
  onEdit: () => void
  onRate: (rating: 'up' | 'down') => void
  rating?: 'up' | 'down' | null
  isAssistant?: boolean
}

function MessageActions({ 
  onCopy, 
  onRegenerate, 
  onEdit, 
  onRate,
  rating,
  isAssistant = false
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    onCopy()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
      <button
        onClick={handleCopy}
        className="p-1.5 hover:bg-surface rounded-md text-foreground-subtle hover:text-foreground transition-colors"
        title="Copy to clipboard"
      >
        {copied ? <CheckCircle2 className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
      </button>
      
      {isAssistant && (
        <>
          <button
            onClick={onRegenerate}
            className="p-1.5 hover:bg-surface rounded-md text-foreground-subtle hover:text-foreground transition-colors"
            title="Regenerate response"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="w-px h-4 bg-border mx-1" />
          <button
            onClick={() => onRate('up')}
            className={`p-1.5 hover:bg-surface rounded-md transition-colors ${
              rating === 'up' ? 'text-success' : 'text-foreground-subtle hover:text-foreground'
            }`}
            title="Helpful"
          >
            <ThumbsUp className="w-4 h-4" />
          </button>
          <button
            onClick={() => onRate('down')}
            className={`p-1.5 hover:bg-surface rounded-md transition-colors ${
              rating === 'down' ? 'text-error' : 'text-foreground-subtle hover:text-foreground'
            }`}
            title="Not helpful"
          >
            <ThumbsDown className="w-4 h-4" />
          </button>
        </>
      )}
      
      {!isAssistant && (
        <button
          onClick={onEdit}
          className="p-1.5 hover:bg-surface rounded-md text-foreground-subtle hover:text-foreground transition-colors"
          title="Edit message"
        >
          <Edit3 className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

/**
 * Loading Skeleton Component
 */
function MessageSkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="w-8 h-8 rounded-full bg-surface" />
      <div className="flex-1 space-y-3">
        <div className="h-4 bg-surface rounded w-3/4" />
        <div className="h-4 bg-surface rounded w-1/2" />
        <div className="h-20 bg-surface rounded-lg" />
      </div>
    </div>
  )
}

/**
 * Chat Interface Component
 * 
 * AI-powered chat interface with:
 * - Streaming responses
 * - Message editing and regeneration
 * - Rating system
 * - SQL preview
 * - Drag-and-drop file upload
 * - Voice input placeholder
 */
export function ChatInterface({ onAddView, onClose }: ChatInterfaceProps) {
  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const [showSql, setShowSql] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, scrollToBottom])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  // Copy to clipboard
  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }, [])

  // Get step status icon
  const getStepStatusIcon = useCallback((status: StepStatus) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 className="w-4 h-4 text-success" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error" />
      case 'running':
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />
      default:
        return <div className="w-4 h-4 rounded-full border-2 border-foreground-subtle" />
    }
  }, [])

  // Get category color
  const getCategoryColor = useCallback((category: StepCategory) => {
    switch (category) {
      case 'thinking':
        return 'bg-warning/10 text-warning border-warning/20'
      case 'action':
        return 'bg-primary/10 text-primary border-primary/20'
      case 'check':
        return 'bg-success/10 text-success border-success/20'
      case 'error':
        return 'bg-error/10 text-error border-error/20'
      default:
        return 'bg-surface text-foreground-muted border-border'
    }
  }, [])

  // Handle form submission
  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage.content,
          tenant_id: 'demo',
          user_id: 'demo-user'
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.message || `Server error: ${response.status}`)
      }

      const { workflow_id } = await response.json()

      // Connect to SSE stream
      const eventSource = new EventSource(`/api/stream/${workflow_id}`)
      let assistantMessage: Message | null = null

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.error) {
            setError(data.error)
            eventSource.close()
            setIsLoading(false)
            return
          }
          
          if (data.step === 'end') {
            eventSource.close()
            setIsLoading(false)
            return
          }

          if (!assistantMessage) {
            assistantMessage = {
              id: `assistant-${Date.now()}`,
              role: 'assistant',
              content: '',
              steps: [],
              timestamp: new Date(),
              isStreaming: true
            }
          }

          // Update or add step
          const existingStepIndex = assistantMessage.steps?.findIndex(
            s => s.name === data.step
          ) ?? -1

          const newStep: Step = {
            id: `${data.step}-${Date.now()}`,
            name: data.step,
            status: data.status === 'complete' ? 'complete' : 
                    data.status === 'error' ? 'error' : 'running',
            message: data.message,
            icon: data.icon || '•',
            category: (data.category as StepCategory) || 'default',
            progress: data.progress || 0
          }

          if (existingStepIndex >= 0 && assistantMessage.steps) {
            assistantMessage.steps[existingStepIndex] = newStep
          } else if (assistantMessage.steps) {
            assistantMessage.steps.push(newStep)
          }

          assistantMessage.currentStep = data.step

          if (data.sql) assistantMessage.sql = data.sql
          if (data.result_preview) {
            assistantMessage.result = {
              row_count: data.result_preview.row_count || 0,
              columns: data.result_preview.columns || [],
            }
          }
          if (data.viz_config) assistantMessage.chartType = data.viz_config.type
          if (data.insights) {
            assistantMessage.content = data.insights
            assistantMessage.isStreaming = false
          }

          setMessages(prev => {
            const filtered = prev.filter(m => m.id !== assistantMessage!.id)
            return [...filtered, { ...assistantMessage! }]
          })
        } catch (parseError) {
          console.error('Error parsing SSE data:', parseError)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setIsLoading(false)
        const errorMsg = 'Connection lost. Please try again.'
        setError(errorMsg)
        toast.error(errorMsg)
      }

    } catch (err: unknown) {
      console.error('Error:', err)
      setIsLoading(false)
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMessage)
      toast.error(errorMessage)
    }
  }, [input, isLoading])

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  // Handle drag and drop
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      toast.success(`${files.length} file(s) ready for upload`, {
        description: 'File upload feature coming soon!',
      })
    }
  }, [])

  // Handle message rating
  const handleRate = useCallback((messageId: string, rating: 'up' | 'down') => {
    setMessages(prev => prev.map(m => 
      m.id === messageId ? { ...m, rating } : m
    ))
    toast.success(rating === 'up' ? 'Thanks for the feedback!' : "We'll improve our responses")
  }, [])

  // Handle message edit
  const handleEdit = useCallback((content: string) => {
    setInput(content)
    inputRef.current?.focus()
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`fixed right-4 bottom-4 z-50 transition-all duration-500 ${
        isExpanded ? 'w-[480px]' : 'w-auto'
      }`}
    >
      {/* Toggle Button (when collapsed) */}
      <AnimatePresence>
        {!isExpanded && (
          <motion.button
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsExpanded(true)}
            className="btn-primary flex items-center gap-2 px-5 py-3 rounded-full shadow-xl"
          >
            <Sparkles className="w-5 h-5" />
            <span className="font-medium">Ask AI</span>
            {messages.length > 0 && (
              <span className="ml-1 text-xs bg-background/30 px-2 py-0.5 rounded-full">
                {messages.length}
              </span>
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Expanded Chat Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
            className="glass-card rounded-2xl overflow-hidden flex flex-col max-h-[80vh] shadow-2xl border border-border/50"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* Drag Overlay */}
            <AnimatePresence>
              {isDragging && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-primary/10 backdrop-blur-sm z-50 flex items-center justify-center border-2 border-dashed border-primary rounded-2xl m-2"
                >
                  <div className="text-center">
                    <Paperclip className="w-12 h-12 text-primary mx-auto mb-2" />
                    <p className="text-primary font-medium">Drop files to upload</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/50 bg-surface/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg shadow-primary/20">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">AI Analyst</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                    <p className="text-xs text-foreground-muted">Online</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button 
                  onClick={() => setIsExpanded(false)}
                  className="p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                  title="Minimize"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
                {onClose && (
                  <button 
                    onClick={onClose}
                    className="p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                    title="Close"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-[400px] max-h-[500px]">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 via-secondary/10 to-accent/10 flex items-center justify-center"
                  >
                    <Zap className="w-10 h-10 text-primary" />
                  </motion.div>
                  <div>
                    <p className="text-foreground font-semibold text-lg">What would you like to know?</p>
                    <p className="text-sm text-foreground-muted mt-2 max-w-xs mx-auto">
                      Ask me about your data and I&apos;ll analyze it step by step with AI-powered insights
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center max-w-sm">
                    {suggestedQuestions.map((suggestion, i) => (
                      <motion.button
                        key={suggestion}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        onClick={() => setInput(suggestion)}
                        className="px-3 py-1.5 text-xs bg-surface hover:bg-surface-elevated border border-border hover:border-border-strong rounded-full transition-all duration-200 text-foreground-muted hover:text-foreground"
                      >
                        {suggestion}
                      </motion.button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((message, index) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={`group flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[90%] space-y-2 ${
                        message.role === 'user' ? 'items-end' : 'items-start'
                      }`}>
                        {/* User Message */}
                        {message.role === 'user' && (
                          <>
                            <div className="px-4 py-3 rounded-2xl bg-primary text-primary-foreground rounded-br-md shadow-lg shadow-primary/20">
                              <p className="text-sm leading-relaxed">{message.content}</p>
                            </div>
                            <MessageActions
                              onCopy={() => copyToClipboard(message.content)}
                              onRegenerate={() => {
                                setInput(message.content)
                                handleSubmit()
                              }}
                              onEdit={() => handleEdit(message.content)}
                              onRate={() => {}}
                            />
                          </>
                        )}

                        {/* AI Response with Steps */}
                        {message.role === 'assistant' && (
                          <>
                            {/* Progress Steps */}
                            {message.steps && message.steps.length > 0 && (
                              <div className="glass-card rounded-xl p-4 space-y-2 min-w-[350px] border border-border/50">
                                {/* Progress Bar */}
                                <div className="flex items-center gap-3 mb-3">
                                  <div className="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                                    <motion.div
                                      className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                                      initial={{ width: 0 }}
                                      animate={{
                                        width: `${message.steps[message.steps.length - 1]?.progress || 0}%`
                                      }}
                                      transition={{ duration: 0.5, ease: "easeOut" }}
                                    />
                                  </div>
                                  <span className="text-xs text-foreground-muted font-medium">
                                    {message.steps[message.steps.length - 1]?.progress || 0}%
                                  </span>
                                </div>

                                {/* Steps */}
                                <div className="space-y-1.5">
                                  {message.steps.map((step, i) => (
                                    <motion.div
                                      key={step.id}
                                      initial={{ opacity: 0, x: -10 }}
                                      animate={{ opacity: 1, x: 0 }}
                                      transition={{ delay: i * 0.03 }}
                                      className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                                        step.status === 'running'
                                          ? 'bg-surface'
                                          : step.status === 'complete'
                                          ? 'opacity-70'
                                          : ''
                                      }`}
                                    >
                                      <div className="w-5 h-5 flex items-center justify-center">
                                        {getStepStatusIcon(step.status)}
                                      </div>
                                      <span className="text-lg">{step.icon}</span>
                                      <span className={`text-sm flex-1 ${
                                        step.status === 'running'
                                          ? 'text-foreground font-medium'
                                          : 'text-foreground-muted'
                                      }`}>
                                        {step.message}
                                      </span>
                                      {step.status === 'running' && (
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getCategoryColor(step.category)}`}>
                                          {step.category}
                                        </span>
                                      )}
                                    </motion.div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Streaming Indicator */}
                            {message.isStreaming && !message.content && (
                              <div className="glass-card rounded-2xl rounded-bl-md">
                                <TypingIndicator />
                              </div>
                            )}

                            {/* Results Content */}
                            {message.content && (
                              <motion.div
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="glass-card rounded-2xl rounded-bl-md px-4 py-3 border border-border/50"
                              >
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                              </motion.div>
                            )}

                            {/* SQL Toggle */}
                            {message.sql && (
                              <div className="w-full">
                                <button
                                  onClick={() => setShowSql(showSql === message.id ? null : message.id)}
                                  className="flex items-center gap-2 text-xs text-foreground-muted hover:text-foreground transition-colors px-1"
                                >
                                  <Code2 className="w-3.5 h-3.5" />
                                  <span>{showSql === message.id ? 'Hide' : 'Show'} SQL</span>
                                  {showSql === message.id ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                </button>
                                <AnimatePresence>
                                  {showSql === message.id && (
                                    <motion.div
                                      initial={{ height: 0, opacity: 0 }}
                                      animate={{ height: 'auto', opacity: 1 }}
                                      exit={{ height: 0, opacity: 0 }}
                                      className="overflow-hidden"
                                    >
                                      <div className="code-block mt-2 text-xs overflow-x-auto relative group">
                                        <button
                                          onClick={() => copyToClipboard(message.sql!)}
                                          className="absolute right-2 top-2 p-1.5 bg-surface rounded opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                          <Copy className="w-3 h-3" />
                                        </button>
                                        <pre className="text-foreground-muted">{message.sql}</pre>
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            )}

                            {/* Results Preview */}
                            {message.result && (
                              <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="glass-card rounded-xl p-3 border border-border/50"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <BarChart3 className="w-4 h-4 text-primary" />
                                    <span className="text-xs text-foreground-muted">
                                      {message.result.row_count} results found
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => onAddView?.({
                                      title: message.content?.slice(0, 30) || 'Query Results',
                                      query: message.content,
                                      data: message.result,
                                      type: message.chartType
                                    })}
                                    className="text-xs text-primary hover:text-secondary transition-colors font-medium"
                                  >
                                    Add to Dashboard
                                  </button>
                                </div>
                              </motion.div>
                            )}

                            {/* Message Actions for AI */}
                            {message.content && !message.isStreaming && (
                              <MessageActions
                                onCopy={() => copyToClipboard(message.content)}
                                onRegenerate={() => toast.info('Regenerating response...')}
                                onEdit={() => toast.info('Edit mode coming soon')}
                                onRate={(rating) => handleRate(message.id, rating)}
                                rating={message.rating}
                                isAssistant
                              />
                            )}
                          </>
                        )}
                      </div>
                    </motion.div>
                  ))}
                  
                  {/* Loading Skeleton */}
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex justify-start"
                    >
                      <div className="max-w-[90%]">
                        <MessageSkeleton />
                      </div>
                    </motion.div>
                  )}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-5 py-2 bg-error/10 border-y border-error/20"
                >
                  <div className="flex items-center gap-2 text-error text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span className="flex-1">{error}</span>
                    <button
                      onClick={() => setError(null)}
                      className="text-xs hover:underline"
                    >
                      Dismiss
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Input Area */}
            <div className="p-4 border-t border-border/50 bg-surface/30">
              <form onSubmit={handleSubmit} className="relative">
                <div className="flex items-end gap-2 bg-surface border border-border rounded-xl p-2 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2 text-foreground-muted hover:text-foreground hover:bg-surface-hover rounded-lg transition-colors flex-shrink-0"
                    title="Attach file"
                  >
                    <Paperclip className="w-5 h-5" />
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    multiple
                    onChange={(e) => {
                      if (e.target.files?.length) {
                        toast.success(`${e.target.files.length} file(s) selected`)
                      }
                    }}
                  />
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about your data..."
                    className="flex-1 bg-transparent border-0 p-2 text-sm text-foreground placeholder:text-foreground-subtle focus:outline-none resize-none min-h-[40px] max-h-[120px]"
                    disabled={isLoading}
                    rows={1}
                  />
                  <button
                    type="button"
                    className="p-2 text-foreground-muted hover:text-foreground hover:bg-surface-hover rounded-lg transition-colors flex-shrink-0"
                    title="Voice input"
                    onClick={() => toast.info('Voice input coming soon!')}
                  >
                    <Mic className="w-5 h-5" />
                  </button>
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="p-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-lg shadow-primary/20"
                  >
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </form>
              <p className="text-[10px] text-foreground-subtle mt-2 text-center">
                AI-generated insights. Always verify important decisions. 
                <button className="hover:underline ml-1">Learn more</button>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default ChatInterface
