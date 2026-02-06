'use client'

import { useState, useRef, useEffect } from 'react'
import { 
  Send, 
  Sparkles, 
  Database, 
  Code2, 
  BarChart3, 
  Loader2,
  X,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  CheckCircle2,
  Circle,
  AlertCircle,
  History,
  Command
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChartRenderer, ChartTypeSelector } from '@/components/ChartRenderer'
import { QueryHistorySidebar } from '@/components/QueryHistorySidebar'
import { CommandPalette } from '@/components/CommandPalette'

interface Step {
  id: string
  name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  message: string
  icon: string
  category: string
  progress: number
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  steps?: Step[]
  currentStep?: string
  sql?: string
  result?: any
  resultData?: any[]  // Full result data for chart rendering
  chartType?: string
  timestamp: Date
}

interface ChatInterfaceProps {
  onAddView: (view: any) => void
}

export function ChatInterface({ onAddView }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const [showSql, setShowSql] = useState<string | null>(null)
  const [chartTypes, setChartTypes] = useState<Record<string, string>>({})
  const [showHistory, setShowHistory] = useState(false)
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  
  // Session management
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [showSessionManager, setShowSessionManager] = useState(false)

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ⌘K or Ctrl+K for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCommandPalette(true)
      }
      // ⌘H or Ctrl+H for history
      if ((e.metaKey || e.ctrlKey) && e.key === 'h') {
        e.preventDefault()
        setShowHistory(true)
      }
      // ⌘N or Ctrl+N for new session
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault()
        createNewSession()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Create new session
  const createNewSession = async () => {
    try {
      const response = await fetch('/api/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat' })
      })
      
      if (response.ok) {
        const session = await response.json()
        setSessionId(session.id)
        setMessages([]) // Clear messages for new session
      }
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  // Load session messages
  const loadSession = async (id: string) => {
    try {
      const response = await fetch(`/api/chat/sessions/${id}`)
      if (response.ok) {
        const session = await response.json()
        setSessionId(session.id)
        
        // Convert to Message format
        const loadedMessages: Message[] = session.messages.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sql: m.sql_generated,
          timestamp: new Date(m.created_at)
        }))
        
        setMessages(loadedMessages)
      }
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  // Persist message to backend
  const persistMessage = async (message: Message) => {
    if (!sessionId) return
    
    try {
      await fetch(`/api/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: message.role,
          content: message.content,
          sql_generated: message.sql,
          chart_type: message.chartType
        })
      })
    } catch (error) {
      console.error('Failed to persist message:', error)
    }
  }

  // Create session on first load if none exists
  useEffect(() => {
    if (!sessionId) {
      createNewSession()
    }
  }, [])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    
    // Persist user message
    await persistMessage(userMessage)

    try {
      // Start query
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: input,
          tenant_id: 'demo',
          user_id: 'demo-user'
        })
      })

      const { workflow_id } = await response.json()

      // Connect to SSE stream
      const eventSource = new EventSource(`/api/stream/${workflow_id}`)
      let assistantMessage: Message | null = null

      eventSource.onmessage = async (event) => {
        const data = JSON.parse(event.data)
        
        if (data.step === 'end') {
          eventSource.close()
          setIsLoading(false)
          // Persist complete assistant message
          if (assistantMessage) {
            await persistMessage(assistantMessage)
          }
          return
        }

        if (!assistantMessage) {
          assistantMessage = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '',
            steps: [],
            timestamp: new Date()
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
          category: data.category || 'default',
          progress: data.progress || 0
        }

        if (existingStepIndex >= 0 && assistantMessage.steps) {
          assistantMessage.steps[existingStepIndex] = newStep
        } else if (assistantMessage.steps) {
          assistantMessage.steps.push(newStep)
        }

        assistantMessage.currentStep = data.step

        // Capture results
        if (data.sql) {
          assistantMessage.sql = data.sql
        }
        if (data.result_preview) {
          assistantMessage.result = data.result_preview
          // Store full data for chart rendering
          if (data.result_preview.rows) {
            assistantMessage.resultData = data.result_preview.rows
          }
        }
        if (data.viz_config) {
          assistantMessage.chartType = data.viz_config.type
        }
        if (data.insights) {
          assistantMessage.content = data.insights
        }

        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== assistantMessage!.id)
          return [...filtered, { ...assistantMessage! }]
        })
      }

      eventSource.onerror = () => {
        eventSource.close()
        setIsLoading(false)
      }

    } catch (error) {
      console.error('Error:', error)
      setIsLoading(false)
    }
  }

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 className="w-4 h-4 text-success" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error" />
      case 'running':
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />
      default:
        return <Circle className="w-4 h-4 text-foreground-subtle" />
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'thinking':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'action':
        return 'bg-primary/20 text-primary border-primary/30'
      case 'check':
        return 'bg-success/20 text-success border-success/30'
      case 'error':
        return 'bg-error/20 text-error border-error/30'
      default:
        return 'bg-surface text-foreground-muted border-border'
    }
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`fixed right-6 bottom-6 z-50 transition-all duration-500 ${
        isExpanded ? 'w-[520px]' : 'w-auto'
      }`}
    >
      {/* Toggle Button (when collapsed) */}
      {!isExpanded && (
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsExpanded(true)}
          className="btn-primary flex items-center gap-2 px-5 py-3 rounded-full shadow-lg"
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

      {/* Expanded Chat Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="glass-card rounded-2xl overflow-hidden flex flex-col max-h-[750px] shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/50 bg-surface/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">AI Analyst</h3>
                  <p className="text-xs text-foreground-muted">Ask anything about your data</p>
                </div>
              </div>
              <button 
                onClick={() => setIsExpanded(false)}
                className="p-2 hover:bg-surface rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-foreground-muted" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-[450px] max-h-[550px]">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                  <motion.div 
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center"
                  >
                    <Database className="w-10 h-10 text-primary" />
                  </motion.div>
                  <div>
                    <p className="text-foreground font-medium text-lg">What would you like to know?</p>
                    <p className="text-sm text-foreground-muted mt-2 max-w-xs">
                      Ask me about your data and I'll analyze it step by step
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center max-w-sm">
                    {['Revenue this month', 'Top customers', 'Growth trends'].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => setInput(suggestion)}
                        className="px-3 py-1.5 text-xs bg-surface hover:bg-surface-elevated border border-border rounded-full transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[90%] space-y-3 ${
                    message.role === 'user' ? 'items-end' : 'items-start'
                  }`}>
                    {/* User Message */}
                    {message.role === 'user' && (
                      <div className="px-4 py-3 rounded-2xl bg-primary text-primary-foreground ml-auto shadow-lg shadow-primary/20">
                        <p className="text-sm leading-relaxed">{message.content}</p>
                      </div>
                    )}

                    {/* AI Response with Steps */}
                    {message.role === 'assistant' && (
                      <>
                        {/* Progress Steps */}
                        {message.steps && message.steps.length > 0 && (
                          <div className="glass-card rounded-xl p-4 space-y-2 min-w-[350px]">
                            {/* Progress Bar */}
                            <div className="flex items-center gap-3 mb-3">
                              <div className="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                                <motion.div 
                                  className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
                                  initial={{ width: 0 }}
                                  animate={{ 
                                    width: `${message.steps[message.steps.length - 1]?.progress || 0}%` 
                                  }}
                                  transition={{ duration: 0.5, ease: "easeOut" }}
                                />
                              </div>
                              <span className="text-xs text-foreground-muted">
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
                                  transition={{ delay: i * 0.05 }}
                                  className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                                    step.status === 'running' 
                                      ? 'bg-surface' 
                                      : step.status === 'complete'
                                      ? 'opacity-70'
                                      : ''
                                  }`}
                                >
                                  {/* Status Icon */}
                                  <div className="w-5 h-5 flex items-center justify-center">
                                    {getStepStatusIcon(step.status)}
                                  </div>

                                  {/* Step Icon */}
                                  <span className="text-lg">{step.icon}</span>

                                  {/* Message */}
                                  <span className={`text-sm flex-1 ${
                                    step.status === 'running' 
                                      ? 'text-foreground font-medium' 
                                      : 'text-foreground-muted'
                                  }`}>
                                    {step.message}
                                  </span>

                                  {/* Category Badge */}
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

                        {/* Results */}
                        {message.content && (
                          <motion.div
                            initial={{ opacity: 0, y: 5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="px-4 py-3 rounded-2xl glass-card"
                          >
                            <p className="text-sm leading-relaxed">{message.content}</p>
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
                                  <div className="code-block mt-2 text-xs overflow-x-auto">
                                    <pre className="text-foreground-muted">{message.sql}</pre>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}

                        {/* Results Preview with Charts */}
                        {message.result && message.resultData && (
                          <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="space-y-3"
                          >
                            {/* Chart Type Selector */}
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <BarChart3 className="w-4 h-4 text-primary" />
                                <span className="text-xs text-foreground-muted">
                                  {message.result.row_count} results found
                                </span>
                              </div>
                              <ChartTypeSelector
                                value={chartTypes[message.id] || message.chartType || 'table'}
                                onChange={(type) => setChartTypes(prev => ({ ...prev, [message.id]: type }))}
                              />
                            </div>
                            
                            {/* Chart Renderer */}
                            <ChartRenderer
                              data={message.resultData}
                              chartType={(chartTypes[message.id] || message.chartType || 'table') as any}
                              title={message.content?.slice(0, 50)}
                            />
                            
                            {/* Add to Dashboard Button */}
                            <div className="flex justify-end">
                              <button 
                                onClick={() => onAddView({
                                  title: message.content?.slice(0, 30) || 'Query Results',
                                  query: message.content,
                                  data: message.result,
                                  chartType: chartTypes[message.id] || message.chartType || 'table'
                                })}
                                className="text-xs text-primary hover:text-accent transition-colors font-medium"
                              >
                                Add to Dashboard
                              </button>
                            </div>
                          </motion.div>
                        )}
                      </>
                    )}
                  </div>
                </motion.div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-border/50 bg-surface/30">
              <form onSubmit={handleSubmit} className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about your data..."
                  className="input-field w-full pr-12 py-3"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 text-primary disabled:text-foreground-subtle transition-colors rounded-lg hover:bg-primary/10"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )
                </button>
              </form>
              <p className="text-[10px] text-foreground-subtle mt-2 text-center">
                AI-generated insights. Always verify important decisions.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History Sidebar */}
      <QueryHistorySidebar
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        onSelectQuery={(query) => {
          setInput(query)
          setShowHistory(false)
          inputRef.current?.focus()
        }}
      />

      {/* Command Palette */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        onSelectQuery={(query) => {
          setInput(query)
          setShowCommandPalette(false)
          inputRef.current?.focus()
        }}
      />

      {/* Floating Action Buttons */}
      {isExpanded && (
        <div className="absolute -left-12 top-4 flex flex-col gap-2">
          <button
            onClick={() => setShowHistory(true)}
            className="p-2 rounded-lg bg-surface hover:bg-surface-elevated border border-border text-foreground-muted hover:text-foreground transition-colors"
            title="History (⌘H)"
          >
            <History className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCommandPalette(true)}
            className="p-2 rounded-lg bg-surface hover:bg-surface-elevated border border-border text-foreground-muted hover:text-foreground transition-colors"
            title="Command Palette (⌘K)"
          >
            <Command className="w-4 h-4" />
          </button>
        </div>
      )}
    </motion.div>
  )
}
