'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
  TrendingDown,
  Calendar,
  Users,
  DollarSign,
  ShoppingCart,
  Activity,
  Plus,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
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
  AreaChart,
  PieChart as RePieChart,
  Pie,
  Cell,
} from 'recharts'
import { toast } from 'sonner'

interface View {
  id: string
  title: string
  query: string
  type: 'line' | 'bar' | 'table' | 'metric' | 'pie'
  data: any[]
  lastUpdated: Date
  isLoading?: boolean
}

interface DashboardCanvasProps {
  views: View[]
  onRemoveView?: (id: string) => void
  onRefreshView?: (id: string) => void
}

// Mock data for charts
const mockLineData = [
  { name: 'Mon', value: 4000, prev: 3500 },
  { name: 'Tue', value: 3000, prev: 2800 },
  { name: 'Wed', value: 5000, prev: 4200 },
  { name: 'Thu', value: 4500, prev: 3800 },
  { name: 'Fri', value: 6000, prev: 5200 },
  { name: 'Sat', value: 5500, prev: 4800 },
  { name: 'Sun', value: 7000, prev: 6000 },
]

const mockBarData = [
  { name: 'Product A', value: 12000, target: 10000 },
  { name: 'Product B', value: 8500, target: 9000 },
  { name: 'Product C', value: 15000, target: 12000 },
  { name: 'Product D', value: 9800, target: 11000 },
  { name: 'Product E', value: 11200, target: 10000 },
]

const mockPieData = [
  { name: 'Direct', value: 400, color: 'hsl(var(--primary))' },
  { name: 'Social', value: 300, color: 'hsl(var(--secondary))' },
  { name: 'Organic', value: 300, color: 'hsl(var(--accent))' },
  { name: 'Referral', value: 200, color: 'hsl(var(--success))' },
]

// Stats data
const statsData = [
  {
    id: 'revenue',
    title: 'Total Revenue',
    value: 124500,
    change: 12.5,
    isPositive: true,
    icon: DollarSign,
    sparkline: [30, 40, 35, 50, 45, 60, 55, 70],
  },
  {
    id: 'orders',
    title: 'Orders',
    value: 1842,
    change: 8.2,
    isPositive: true,
    icon: ShoppingCart,
    sparkline: [20, 25, 30, 28, 35, 40, 38, 45],
  },
  {
    id: 'users',
    title: 'Active Users',
    value: 8921,
    change: -2.4,
    isPositive: false,
    icon: Users,
    sparkline: [50, 48, 52, 45, 55, 50, 53, 48],
  },
  {
    id: 'growth',
    title: 'Growth Rate',
    value: 23.5,
    suffix: '%',
    change: 4.1,
    isPositive: true,
    icon: Activity,
    sparkline: [10, 15, 12, 20, 18, 25, 22, 28],
  },
]

// Mini Sparkline Component
function MiniSparkline({ data, isPositive }: { data: number[]; isPositive: boolean }) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * 60
    const y = 20 - ((value - min) / range) * 20
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width="60" height="24" className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={isPositive ? 'hsl(var(--success))' : 'hsl(var(--error))'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Stat Card Component
function StatCard({ stat }: { stat: typeof statsData[0] }) {
  const Icon = stat.icon
  
  const formatValue = (val: number) => {
    if (stat.id === 'revenue') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(val)
    }
    if (stat.id === 'users' || stat.id === 'orders') {
      return new Intl.NumberFormat('en-US').format(val)
    }
    return `${val}${stat.suffix || ''}`
  }

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="stat-card group"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-subtle flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-foreground-muted">{stat.title}</p>
            <p className="text-2xl font-bold text-foreground mt-0.5">
              {formatValue(stat.value)}
            </p>
          </div>
        </div>
        <MiniSparkline data={stat.sparkline} isPositive={stat.isPositive} />
      </div>
      
      <div className="flex items-center gap-2 mt-4">
        <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
          stat.isPositive 
            ? 'bg-success-subtle text-success' 
            : 'bg-error-subtle text-error'
        }`}>
          {stat.isPositive ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          {stat.change}%
        </span>
        <span className="text-xs text-foreground-muted">vs last month</span>
      </div>
    </motion.div>
  )
}

// Recent Activity Component
function RecentActivity() {
  const activities = [
    { id: 1, type: 'query', title: 'Q4 revenue analysis', user: 'You', time: '2m ago' },
    { id: 2, type: 'alert', title: 'Anomaly detected in sales', user: 'System', time: '15m ago' },
    { id: 3, type: 'share', title: 'Dashboard shared with team', user: 'You', time: '1h ago' },
    { id: 4, type: 'query', title: 'Customer segmentation', user: 'Sarah', time: '3h ago' },
  ]

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm">Recent Activity</h3>
        <button className="text-xs text-primary hover:underline">View all</button>
      </div>
      <div className="space-y-3">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              activity.type === 'query' ? 'bg-primary-subtle text-primary' :
              activity.type === 'alert' ? 'bg-warning-subtle text-warning' :
              'bg-success-subtle text-success'
            }`}>
              {activity.type === 'query' ? <Sparkles className="w-4 h-4" /> :
               activity.type === 'alert' ? <TrendingUp className="w-4 h-4" /> :
               <Users className="w-4 h-4" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{activity.title}</p>
              <p className="text-xs text-foreground-muted">{activity.user} • {activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Quick Actions Component
function QuickActions() {
  const actions = [
    { id: 'new', label: 'New Query', icon: Sparkles, color: 'primary' },
    { id: 'report', label: 'Generate Report', icon: BarChart3, color: 'secondary' },
    { id: 'share', label: 'Share', icon: Users, color: 'accent' },
    { id: 'export', label: 'Export', icon: Download, color: 'success' },
  ]

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="font-semibold text-sm mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-2">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <motion.button
              key={action.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => toast.success(`${action.label} coming soon!`)}
              className="flex items-center gap-2 p-3 rounded-xl bg-surface hover:bg-surface-hover border border-border hover:border-border-strong transition-all text-left"
            >
              <div className={`w-8 h-8 rounded-lg bg-${action.color}-subtle flex items-center justify-center`}>
                <Icon className={`w-4 h-4 text-${action.color}`} />
              </div>
              <span className="text-sm font-medium">{action.label}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}

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
    const data = view.data?.length ? view.data : view.type === 'pie' ? mockPieData : view.type === 'bar' ? mockBarData : mockLineData

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
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
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
                  borderRadius: '8px',
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

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <RePieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {data.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry.color || `hsl(var(--primary) / ${1 - index * 0.2})`} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--surface))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
            </RePieChart>
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
                  {data[0] && Object.keys(data[0]).filter(k => k !== 'color').map((key) => (
                    <th key={key} className="text-left py-2 px-3 text-foreground-muted font-medium capitalize">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 5).map((row: any, i: number) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-surface/50">
                    {Object.entries(row).filter(([k]) => k !== 'color').map(([key, value]: [string, any], j: number) => (
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
      case 'pie': return <PieChart className="w-4 h-4" />
      case 'metric': return <TrendingUp className="w-4 h-4" />
      default: return <Table2 className="w-4 h-4" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsData.map((stat) => (
          <StatCard key={stat.id} stat={stat} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Charts Area */}
        <div className="lg:col-span-2">
          {views.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl p-12 text-center"
            >
              <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-primary/10 via-secondary/10 to-accent/10 flex items-center justify-center mb-6">
                <BarChart3 className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Your dashboard is empty</h2>
              <p className="text-foreground-muted max-w-sm mx-auto mb-6">
                Ask the AI Analyst to generate insights, or create views from your saved queries.
              </p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => toast.info('Chat with the AI Analyst to get started!')}
                className="btn-primary inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Ask AI Analyst
              </motion.button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {views.map((view, index) => (
                <motion.div
                  key={view.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`glass-card rounded-xl overflow-hidden ${
                    view.type === 'metric' ? '' : 'md:col-span-1'
                  }`}
                  onMouseEnter={() => setHoveredCard(view.id)}
                  onMouseLeave={() => setHoveredCard(null)}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center text-foreground-muted">
                        {getChartIcon(view.type)}
                      </div>
                      <div>
                        <h3 className="font-medium text-sm">{view.title}</h3>
                        <div className="flex items-center gap-1 text-[10px] text-foreground-muted">
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
                        className="p-1.5 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                        title="Refresh"
                      >
                        <RefreshCw className={`w-4 h-4 ${view.isLoading && 'animate-spin'}`} />
                      </button>
                      <button 
                        className="p-1.5 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                        title="Download"
                        onClick={() => toast.success('Downloading...')}
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button 
                        className="p-1.5 hover:bg-surface rounded-lg transition-colors text-foreground-muted hover:text-foreground"
                        title="Maximize"
                        onClick={() => toast.success('Fullscreen view coming soon')}
                      >
                        <Maximize2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onRemoveView?.(view.id)}
                        className="p-1.5 hover:bg-error/10 rounded-lg transition-colors text-foreground-muted hover:text-error"
                        title="Remove"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Content */}
                  <div className={`p-4 ${view.type === 'metric' ? 'h-40' : 'h-64'}`}>
                    {renderChart(view)}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <QuickActions />
          <RecentActivity />
        </div>
      </div>
    </div>
  )
}
