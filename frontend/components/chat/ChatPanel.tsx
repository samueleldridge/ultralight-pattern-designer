'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  steps?: any[]
  sql?: string
  result?: any
}

interface ChatPanelProps {
  onAddView: (view: any) => void
}

export function ChatPanel({ onAddView }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Start workflow
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: input,
          tenant_id: 'demo-tenant',
          user_id: 'demo-user'
        })
      })

      const { workflow_id } = await response.json()

      // Connect to SSE stream
      const eventSource = new EventSource(`/api/stream/${workflow_id}`)
      
      let assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        steps: []
      }

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.step === 'end') {
          eventSource.close()
          setIsLoading(false)
          return
        }

        // Update assistant message with step info
        assistantMessage.steps = [...(assistantMessage.steps || []), data]
        
        if (data.sql) {
          assistantMessage.sql = data.sql
        }
        
        if (data.result_preview) {
          assistantMessage.result = data.result_preview
        }

        if (data.insights) {
          assistantMessage.content = data.insights
        }

        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== assistantMessage.id)
          return [...filtered, { ...assistantMessage }]
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

  return (
    <div className={`fixed bottom-0 right-0 bg-white border-l border-t shadow-2xl transition-all duration-300 ${
      isExpanded ? 'w-[480px] h-[600px]' : 'w-[480px] h-14'
    }`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 border-b cursor-pointer bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-600" />
          <span className="font-medium">AI Analyst</span>
        </div>
        <button className="text-gray-400 hover:text-gray-600">
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Messages */}
      {isExpanded && (
        <>
          <div className="flex-1 overflow-y-auto p-4 h-[480px]">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-20">
                <Bot className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>Ask me anything about your data</p>
                <p className="text-sm mt-2">Try: "What was revenue last month?"</p>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id} className={`mb-4 ${message.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-flex items-start gap-2 max-w-[90%] ${
                  message.role === 'user' ? 'flex-row-reverse' : ''
                }`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user' ? 'bg-blue-100' : 'bg-green-100'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="w-4 h-4 text-blue-600" />
                    ) : (
                      <Bot className="w-4 h-4 text-green-600" />
                    )}
                  </div>
                  
                  <div className={`p-3 rounded-lg text-left ${
                    message.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    {message.role === 'assistant' && message.steps && (
                      <div className="mb-2 text-xs text-gray-500">
                        {message.steps.map((step, i) => (
                          <div key={i} className="flex items-center gap-1">
                            <span>{step.step}</span>
                            <span className={step.status === 'complete' ? 'text-green-500' : 'text-yellow-500'}>
                              {step.status === 'complete' ? '✓' : '⋯'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {message.sql && (
                      <div className="mb-2 p-2 bg-gray-800 text-gray-300 rounded text-xs font-mono overflow-x-auto">
                        <code>{message.sql}</code>
                      </div>
                    )}
                    
                    {message.content && <p>{message.content}</p>}
                    
                    {message.result && (
                      <div className="mt-2 text-sm">
                        <p className="text-gray-500">
                          Found {message.result.row_count} rows
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question..."
                className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  )
}
