'use client'

import { useState } from 'react'
import { 
  MoreHorizontal, 
  RefreshCw, 
  Download, 
  Maximize2,
  X,
  BarChart3,
  LineChart,
  PieChart,
  Table2,
  TrendingUp,
  Calendar
} from 'lucide-react'
import { motion } from 'framer-motion'
import {
  LineChart as ReLineChart,
  Line,
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'

interface View {
  id: string
  title: string
  query: string
  type: 'line' | 'bar' | 'table' | 'metric'
  data: any[]
  lastUpdated: Date
  isLoading?: boolean
}

interface DashboardCanvasProps {
  views: View[]
  onRemoveView?: (id: string) => void
  onRefreshView?: (id: string) => void
}

const mockData = [
  { name: 'Jan', value: 4000, prev: 3500 },
  { name: 'Feb', value: 3000, prev: 2800 },
  { name: 'Mar', value: 5000, prev: 4200 },
  { name: 'Apr', value: 4500, prev: 3800 },
  { name: 'May', value: 6000, prev: 5200 },
  { name: 'Jun', value: 5500, prev: 4800 },
]

export function DashboardCanvas({ views, onRemoveView, onRefreshView }: DashboardCanvasProps) {
  const [hoveredCard, setHoveredCard] = useState<string | null>(null)

  const formatValue = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`
    return `$${value}`
  }

  const calculateChange = (current: number, previous: number) => {
    const change = ((current - previous) / previous) * 100
    return change.toFixed(1)
  }

  const renderChart = (view: View) => {
    const data = view.data || mockData
    
    switch (view.type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${view.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis 
                dataKey="name" 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
                dy={10}
              />
              <YAxis 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
                tickFormatter={formatValue}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--surface))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                }}
                itemStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="hsl(var(--primary))" 
                strokeWidth={2}
                fill={`url(#gradient-${view.id})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        )
      
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <ReBarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis 
                dataKey="name" 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
                dy={10}
              />
              <YAxis 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
                tickFormatter={formatValue}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--surface))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                cursor={{ fill: 'hsl(var(--primary) / 0.1)' }}
              />
              <Bar 
                dataKey="value" 
                fill="hsl(var(--primary))" 
                radius={[4, 4, 0, 0]}
              />
            </ReBarChart>
          </ResponsiveContainer>
        )
      
      case 'metric':
        const currentValue = data[data.length - 1]?.value || 0
        const previousValue = data[data.length - 2]?.value || 0
        const change = calculateChange(currentValue, previousValue)
        const isPositive = parseFloat(change) >= 0
        
        return (
          <div className="h-full flex flex-col justify-center">
            <div className="text-4xl font-bold gradient-text">
              {formatValue(currentValue)}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className={`flex items-center gap-1 text-sm font-medium ${
                isPositive ? 'text-success' : 'text-error'
              }`}>
                <TrendingUp className={`w-4 h-4 ${!isPositive && 'rotate-180'}`} />
                {isPositive ? '+' : ''}{change}%
              </span>
              <span className="text-sm text-foreground-muted">vs last month</span>
            </div>
          </div>
        )
      
      default:
        return (
          <div className="h-full overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {data[0] && Object.keys(data[0]).map((key) => (
                    <th key={key} className="text-left py-2 px-3 text-foreground-muted font-medium capitalize">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 5).map((row, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-surface/50">
                    {Object.values(row).map((value: any, j) => (
                      <td key={j} className="py-2 px-3 text-foreground">
                        {typeof value === 'number' ? formatValue(value) : String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
    }
  }

  const getChartIcon = (type: string) => {
    switch (type) {
      case 'line': return <LineChart className="w-4 h-4" />
      case 'bar': return <BarChart3 className="w-4 h-4" />
      case 'metric': return <TrendingUp className="w-4 h-4" />
      default: return <Table2 className="w-4 h-4" />
    }
  }

  return (
    <div className="p-6">
      {views.length === 0 ? (
        <div className="h-[60vh] flex flex-col items-center justify-center text-center">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-24 h-24 rounded-3xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center mb-6"
          >
            <BarChart3 className="w-10 h-10 text-primary" />
          </motion.div>
          <h2 className="text-xl font-semibold mb-2">Your dashboard is empty</h2>
          <p className="text-foreground-muted max-w-sm">
            Ask the AI Analyst to generate insights, or create views from your saved queries.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {views.map((view, index) => (
            <motion.div
              key={view.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`glass-card rounded-2xl overflow-hidden ${
                view.type === 'metric' ? 'md:col-span-1' : 'md:col-span-2'
              }`}
              onMouseEnter={() => setHoveredCard(view.id)}
              onMouseLeave={() => setHoveredCard(null)}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center text-foreground-muted">
                    {getChartIcon(view.type)}
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">{view.title}</h3>
                    <div className="flex items-center gap-2 text-xs text-foreground-muted">
                      <Calendar className="w-3 h-3" />
                      <span>Updated {view.lastUpdated.toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                
                {/* Actions */}
                <div className={`flex items-center gap-1 transition-opacity ${
                  hoveredCard === view.id ? 'opacity-100' : 'opacity-0'
                }`}>
                  <button 
                    onClick={() => onRefreshView?.(view.id)}
                    className="p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                  >
                    <RefreshCw className={`w-4 h-4 ${view.isLoading && 'animate-spin'}`} />
                  </button>
                  <button className="p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground">
                    <Download className="w-4 h-4" />
                  </button>
                  <button className="p-2 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground">
                    <Maximize2 className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => onRemoveView?.(view.id)}
                    className="p-2 hover:bg-error/10 rounded-lg transition-colors text-foreground-muted hover:text-error"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className={`p-5 ${view.type === 'metric' ? 'h-40' : 'h-80'}`}>
                {renderChart(view)}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
