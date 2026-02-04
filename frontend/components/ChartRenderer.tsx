'use client'

import { useMemo } from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

// Chart color palette
const COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#84cc16', // lime-500
]

interface ChartRendererProps {
  data: any[]
  chartType: 'line' | 'bar' | 'area' | 'pie' | 'table' | 'metric'
  xAxis?: string
  yAxis?: string | string[]
  title?: string
  className?: string
}

// Detect numeric columns for Y-axis
function getNumericColumns(data: any[]): string[] {
  if (!data || data.length === 0) return []
  
  const firstRow = data[0]
  return Object.entries(firstRow)
    .filter(([_, value]) => typeof value === 'number')
    .map(([key]) => key)
}

// Detect date/string columns for X-axis
function getXAxisColumn(data: any[]): string | undefined {
  if (!data || data.length === 0) return undefined
  
  const firstRow = data[0]
  const columns = Object.keys(firstRow)
  
  // Prefer date columns
  const dateColumn = columns.find(col => 
    col.toLowerCase().includes('date') || 
    col.toLowerCase().includes('time') ||
    col.toLowerCase().includes('month') ||
    col.toLowerCase().includes('year')
  )
  if (dateColumn) return dateColumn
  
  // Otherwise first string column
  const stringColumn = columns.find(col => typeof firstRow[col] === 'string')
  return stringColumn || columns[0]
}

// Format numbers for display
function formatValue(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`
  return `$${value.toFixed(0)}`
}

// Metric Card Component
function MetricCard({ data, title }: { data: any[]; title?: string }) {
  const metric = useMemo(() => {
    if (!data || data.length === 0) return null
    
    const firstRow = data[0]
    const numericKeys = Object.entries(firstRow)
      .filter(([_, v]) => typeof v === 'number')
      .map(([k]) => k)
    
    if (numericKeys.length === 0) return null
    
    const key = numericKeys[0]
    const value = firstRow[key]
    
    // Look for comparison/metric data
    const prevKey = numericKeys.find(k => 
      k.toLowerCase().includes('prev') || 
      k.toLowerCase().includes('last') ||
      k.toLowerCase().includes('before')
    )
    
    if (prevKey) {
      const prevValue = firstRow[prevKey]
      const change = ((value - prevValue) / prevValue) * 100
      return { value, change, label: key }
    }
    
    return { value, change: null, label: key }
  }, [data])
  
  if (!metric) return null
  
  return (
    <div className="glass-card rounded-xl p-6">
      <h3 className="text-sm font-medium text-foreground-muted mb-2">
        {title || metric.label}
      </h3>
      <div className="flex items-end gap-4">
        <span className="text-4xl font-bold text-foreground">
          {formatValue(metric.value)}
        </span>
        {metric.change !== null && (
          <div className={`flex items-center gap-1 text-sm ${
            metric.change > 0 ? 'text-emerald-400' : 
            metric.change < 0 ? 'text-red-400' : 'text-foreground-muted'
          }`}>
            {metric.change > 0 ? <TrendingUp className="w-4 h-4" /> : 
             metric.change < 0 ? <TrendingDown className="w-4 h-4" /> : 
             <Minus className="w-4 h-4" />}
            <span>{Math.abs(metric.change).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  )
}

// Table View Component
function TableView({ data }: { data: any[] }) {
  if (!data || data.length === 0) return null
  
  const columns = Object.keys(data[0])
  
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="overflow-x-auto max-h-[300px]">
        <table className="w-full text-sm">
          <thead className="bg-surface sticky top-0">
            <tr>
              {columns.map(col => (
                <th key={col} className="px-4 py-3 text-left font-medium text-foreground-muted">
                  {col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {data.slice(0, 50).map((row, i) => (
              <tr key={i} className="hover:bg-surface/50">
                {columns.map(col => (
                  <td key={col} className="px-4 py-2.5 text-foreground">
                    {typeof row[col] === 'number' ? formatValue(row[col]) : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > 50 && (
        <div className="px-4 py-2 text-xs text-foreground-muted border-t border-border/50">
          Showing 50 of {data.length} rows
        </div>
      )}
    </div>
  )
}

// Main Chart Renderer
export function ChartRenderer({ 
  data, 
  chartType = 'table', 
  xAxis: xAxisProp,
  yAxis: yAxisProp,
  title,
  className = ''
}: ChartRendererProps) {
  
  // Auto-detect columns
  const xAxis = xAxisProp || getXAxisColumn(data)
  const yAxis = yAxisProp || getNumericColumns(data)
  
  const yAxisArray = Array.isArray(yAxis) ? yAxis : [yAxis].filter(Boolean)
  
  // Handle metric/single value
  if (chartType === 'metric' || (data.length === 1 && yAxisArray.length === 1)) {
    return <MetricCard data={data} title={title} />
  }
  
  // Handle table view
  if (chartType === 'table' || !xAxis || yAxisArray.length === 0) {
    return <TableView data={data} />
  }
  
  // Prepare data - ensure x values are strings
  const chartData = data.map(row => ({
    ...row,
    [xAxis]: String(row[xAxis])
  }))
  
  const commonProps = {
    data: chartData,
    margin: { top: 10, right: 30, left: 0, bottom: 0 }
  }
  
  const tooltipStyle = {
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '8px',
    padding: '12px'
  }
  
  return (
    <div className={`glass-card rounded-xl p-4 ${className}`}>
      {title && (
        <h3 className="text-sm font-medium text-foreground-muted mb-4">{title}</h3>
      )}
      
      <ResponsiveContainer width="100%" height={280}>
        {chartType === 'line' ? (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis 
              dataKey={xAxis} 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatValue(v)} />
            {yAxisArray.length > 1 && <Legend />}
            {yAxisArray.map((yKey, i) => (
              <Line
                key={yKey}
                type="monotone"
                dataKey={yKey}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        ) : chartType === 'area' ? (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis 
              dataKey={xAxis} 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatValue(v)} />
            {yAxisArray.length > 1 && <Legend />}
            {yAxisArray.map((yKey, i) => (
              <Area
                key={yKey}
                type="monotone"
                dataKey={yKey}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.2}
              />
            ))}
          </AreaChart>
        ) : chartType === 'pie' ? (
          <PieChart>
            <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatValue(v)} />
            <Legend />
            <Pie
              data={chartData}
              dataKey={yAxisArray[0]}
              nameKey={xAxis}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            >
              {chartData.map((_, i) => (
                <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        ) : (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis 
              dataKey={xAxis} 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              stroke="rgba(148, 163, 184, 0.5)"
              fontSize={12}
              tickLine={false}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatValue(v)} />
            {yAxisArray.length > 1 && <Legend />}
            {yAxisArray.map((yKey, i) => (
              <Bar
                key={yKey}
                dataKey={yKey}
                fill={COLORS[i % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

// Chart type selector
interface ChartTypeSelectorProps {
  value: string
  onChange: (type: 'line' | 'bar' | 'area' | 'pie' | 'table' | 'metric') => void
  availableTypes?: string[]
}

export function ChartTypeSelector({ 
  value, 
  onChange, 
  availableTypes = ['table', 'bar', 'line', 'area', 'pie', 'metric'] 
}: ChartTypeSelectorProps) {
  const types = [
    { id: 'table', label: 'Table', icon: '⊞' },
    { id: 'metric', label: 'Metric', icon: '◎' },
    { id: 'bar', label: 'Bar', icon: '▤' },
    { id: 'line', label: 'Line', icon: '╱' },
    { id: 'area', label: 'Area', icon: '◢' },
    { id: 'pie', label: 'Pie', icon: '◐' },
  ]
  
  return (
    <div className="flex gap-1">
      {types
        .filter(t => availableTypes.includes(t.id))
        .map(type => (
          <button
            key={type.id}
            onClick={() => onChange(type.id as any)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              value === type.id
                ? 'bg-primary text-primary-foreground'
                : 'bg-surface hover:bg-surface-elevated text-foreground-muted'
            }`}
            title={type.label}
          >
            {type.icon}
          </button>
        ))}
    </div>
  )
}

export default ChartRenderer
