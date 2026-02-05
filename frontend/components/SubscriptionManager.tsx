'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Bell, 
  Plus, 
  Clock, 
  Pause, 
  Play, 
  Trash2, 
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Filter,
  X
} from 'lucide-react'

interface Subscription {
  id: string
  name: string
  description?: string
  query_template: string
  frequency: string
  condition_type: string
  status: 'active' | 'paused' | 'cancelled'
  next_run_at?: string
  last_run_at?: string
  run_count: number
  hit_count: number
  created_at: string
}

interface CreateSubscriptionModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (subscription: any) => void
}

function CreateSubscriptionModal({ isOpen, onClose, onCreate }: CreateSubscriptionModalProps) {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    query_template: '',
    frequency: 'weekly',
    condition_type: 'threshold',
    condition_config: { column: '', operator: '<', value: '' }
  })

  const handleSubmit = () => {
    onCreate(formData)
    onClose()
    setStep(1)
    setFormData({
      name: '',
      description: '',
      query_template: '',
      frequency: 'weekly',
      condition_type: 'threshold',
      condition_config: { column: '', operator: '<', value: '' }
    })
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
          >
            <div className="w-full max-w-lg glass-card rounded-xl overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-border">
                <h3 className="font-semibold">Create Subscription</h3>
                <button onClick={onClose} className="p-2 hover:bg-surface rounded-lg">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Progress */}
              <div className="flex gap-2 p-4">
                {[1, 2, 3].map(i => (
                  <div
                    key={i}
                    className={`flex-1 h-1 rounded-full ${
                      i <= step ? 'bg-primary' : 'bg-surface'
                    }`}
                  />
                ))}
              </div>

              {/* Content */}
              <div className="p-4 space-y-4">
                {step === 1 && (
                  <>
                    <div>
                      <label className="text-sm font-medium text-foreground-muted">Name</label>
                      <input
                        type="text"
                        placeholder="e.g., Low Margin Alert"
                        value={formData.name}
                        onChange={e => setFormData({...formData, name: e.target.value})}
                        className="input-field w-full mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-foreground-muted">Description</label>
                      <textarea
                        placeholder="What should I watch for?"
                        value={formData.description}
                        onChange={e => setFormData({...formData, description: e.target.value})}
                        className="input-field w-full mt-1 h-20"
                      />
                    </div>
                  </>
                )}

                {step === 2 && (
                  <>
                    <div>
                      <label className="text-sm font-medium text-foreground-muted">Query</label>
                      <textarea
                        placeholder="SELECT * FROM clients WHERE gross_margin < 0.20"
                        value={formData.query_template}
                        onChange={e => setFormData({...formData, query_template: e.target.value})}
                        className="input-field w-full mt-1 h-24 font-mono text-xs"
                      />
                      <p className="text-xs text-foreground-muted mt-1">
                        Or use natural language: "clients with gross margin below 20%"
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-foreground-muted">Frequency</label>
                      <select
                        value={formData.frequency}
                        onChange={e => setFormData({...formData, frequency: e.target.value})}
                        className="input-field w-full mt-1"
                      >
                        <option value="hourly">Hourly</option>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    </div>
                  </>
                )}

                {step === 3 && (
                  <>
                    <div>
                      <label className="text-sm font-medium text-foreground-muted">Condition Type</label>
                      <select
                        value={formData.condition_type}
                        onChange={e => setFormData({...formData, condition_type: e.target.value})}
                        className="input-field w-full mt-1"
                      >
                        <option value="threshold">Threshold (value above/below)</option>
                        <option value="new_items">New Items</option>
                        <option value="change">Change Percentage</option>
                        <option value="always">Always Report</option>
                      </select>
                    </div>
                    {formData.condition_type === 'threshold' && (
                      <div className="grid grid-cols-3 gap-2">
                        <input
                          type="text"
                          placeholder="Column"
                          value={formData.condition_config.column}
                          onChange={e => setFormData({...formData, condition_config: {...formData.condition_config, column: e.target.value}})}
                          className="input-field"
                        />
                        <select
                          value={formData.condition_config.operator}
                          onChange={e => setFormData({...formData, condition_config: {...formData.condition_config, operator: e.target.value}})}
                          className="input-field"
                        >
                          <option value="<">&lt;</option>
                          <option value=">">&gt;</option>
                          <option value="=">=</option>
                          <option value="<=">&lt;=</option>
                          <option value=">=">&gt;=</option>
                        </select>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Value"
                          value={formData.condition_config.value}
                          onChange={e => setFormData({...formData, condition_config: {...formData.condition_config, value: e.target.value}})}
                          className="input-field"
                        />
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Footer */}
              <div className="flex justify-between p-4 border-t border-border">
                {step > 1 ? (
                  <button
                    onClick={() => setStep(step - 1)}
                    className="btn-secondary"
                  >
                    Back
                  </button>
                ) : (
                  <div />
                )}
                {step < 3 ? (
                  <button
                    onClick={() => setStep(step + 1)}
                    className="btn-primary"
                  >
                    Next
                  </button>
                ) : (
                  <button
                    onClick={handleSubmit}
                    className="btn-primary"
                  >
                    Create Subscription
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export function SubscriptionManager() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'paused'>('all')

  useEffect(() => {
    fetchSubscriptions()
  }, [filter])

  const fetchSubscriptions = async () => {
    setIsLoading(true)
    try {
      const url = filter === 'all' 
        ? '/api/subscriptions' 
        : `/api/subscriptions?status=${filter}`
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setSubscriptions(data)
      }
    } catch (error) {
      console.error('Failed to fetch subscriptions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async (formData: any) => {
    try {
      const response = await fetch('/api/subscriptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (response.ok) {
        fetchSubscriptions()
      }
    } catch (error) {
      console.error('Failed to create subscription:', error)
    }
  }

  const handlePause = async (id: string) => {
    try {
      await fetch(`/api/subscriptions/${id}/pause`, { method: 'POST' })
      fetchSubscriptions()
    } catch (error) {
      console.error('Failed to pause:', error)
    }
  }

  const handleResume = async (id: string) => {
    try {
      await fetch(`/api/subscriptions/${id}/resume`, { method: 'POST' })
      fetchSubscriptions()
    } catch (error) {
      console.error('Failed to resume:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure? This will permanently delete this subscription.')) return
    try {
      await fetch(`/api/subscriptions/${id}`, { method: 'DELETE' })
      fetchSubscriptions()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const handleRunNow = async (id: string) => {
    try {
      const response = await fetch(`/api/subscriptions/${id}/run-now`, { method: 'POST' })
      if (response.ok) {
        const result = await response.json()
        alert(`Check complete! Condition met: ${result.condition_met}, Rows: ${result.rows_found}`)
      }
    } catch (error) {
      console.error('Failed to run:', error)
    }
  }

  const formatFrequency = (freq: string) => {
    return freq.charAt(0).toUpperCase() + freq.slice(1)
  }

  const formatNextRun = (dateStr?: string) => {
    if (!dateStr) return 'Not scheduled'
    const date = new Date(dateStr)
    const now = new Date()
    const diff = date.getTime() - now.getTime()
    const hours = Math.floor(diff / 3600000)
    
    if (hours < 1) return 'Soon'
    if (hours < 24) return `In ${hours}h`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Subscriptions</h2>
          <p className="text-sm text-foreground-muted">
            Get notified when conditions are met
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Subscription
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(['all', 'active', 'paused'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === f
                ? 'bg-primary text-white'
                : 'bg-surface text-foreground-muted hover:text-foreground'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Subscriptions List */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-surface animate-pulse rounded-xl" />
          ))}
        </div>
      ) : subscriptions.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-xl">
          <Bell className="w-12 h-12 mx-auto text-foreground-muted mb-4" />
          <h3 className="text-lg font-medium">No subscriptions yet</h3>
          <p className="text-sm text-foreground-muted mt-1">
            Create one to get notified about important changes
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {subscriptions.map(sub => (
            <motion.div
              key={sub.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="glass-card rounded-xl overflow-hidden"
            >
              <div
                className="flex items-center gap-3 p-4 cursor-pointer hover:bg-surface/50 transition-colors"
                onClick={() => setExpandedId(expandedId === sub.id ? null : sub.id)}
              >
                <div className={`w-2 h-2 rounded-full ${
                  sub.status === 'active' ? 'bg-emerald-400' :
                  sub.status === 'paused' ? 'bg-amber-400' : 'bg-red-400'
                }`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{sub.name}</h4>
                    <span className="text-xs px-2 py-0.5 bg-surface rounded-full text-foreground-muted">
                      {formatFrequency(sub.frequency)}
                    </span>
                  </div>
                  <p className="text-xs text-foreground-muted line-clamp-1">
                    {sub.description || sub.query_template}
                  </p>
                </div>
                <div className="text-right text-xs text-foreground-muted">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatNextRun(sub.next_run_at)}
                  </div>
                  <div className="mt-1">
                    {sub.hit_count}/{sub.run_count} hits
                  </div>
                </div>
                {expandedId === sub.id ? (
                  <ChevronDown className="w-4 h-4 text-foreground-muted" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-foreground-muted" />
                )}
              </div>

              <AnimatePresence>
                {expandedId === sub.id && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-4 space-y-3 border-t border-border">
                      <div className="pt-3 space-y-2">
                        <div className="text-sm">
                          <span className="text-foreground-muted">Query:</span>
                          <code className="ml-2 px-2 py-1 bg-surface rounded text-xs">
                            {sub.query_template}
                          </code>
                        </div>
                        <div className="text-sm">
                          <span className="text-foreground-muted">Condition:</span>
                          <span className="ml-2 text-xs">
                            {sub.condition_type}
                          </span>
                        </div>
                        {sub.last_run_at && (
                          <div className="text-sm">
                            <span className="text-foreground-muted">Last run:</span>
                            <span className="ml-2 text-xs">
                              {new Date(sub.last_run_at).toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        {sub.status === 'active' ? (
                          <button
                            onClick={() => handlePause(sub.id)}
                            className="btn-secondary flex items-center gap-1 text-xs"
                          >
                            <Pause className="w-3 h-3" />
                            Pause
                          </button>
                        ) : (
                          <button
                            onClick={() => handleResume(sub.id)}
                            className="btn-secondary flex items-center gap-1 text-xs"
                          >
                            <Play className="w-3 h-3" />
                            Resume
                          </button>
                        )}
                        <button
                          onClick={() => handleRunNow(sub.id)}
                          className="btn-secondary flex items-center gap-1 text-xs"
                        >
                          <TrendingUp className="w-3 h-3" />
                          Run Now
                        </button>
                        <button
                          onClick={() => handleDelete(sub.id)}
                          className="ml-auto btn-secondary flex items-center gap-1 text-xs text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-3 h-3" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      )}

      <CreateSubscriptionModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onCreate={handleCreate}
      />
    </div>
  )
}
