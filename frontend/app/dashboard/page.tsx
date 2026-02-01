'use client'

import { useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { DashboardCanvas } from '@/components/dashboard/DashboardCanvas'
import { ChatInterface } from '@/components/chat/ChatInterface'

interface View {
  id: string
  title: string
  query: string
  type: 'line' | 'bar' | 'table' | 'metric' | 'pie'
  data: any[]
  lastUpdated: Date
  isLoading?: boolean
}

export default function Dashboard() {
  const [views, setViews] = useState<View[]>([])

  const handleAddView = (viewData: any) => {
    const newView: View = {
      id: Date.now().toString(),
      title: viewData.title || 'New View',
      query: viewData.query || '',
      type: viewData.type || 'line',
      data: viewData.data || [],
      lastUpdated: new Date()
    }
    setViews(prev => [...prev, newView])
  }

  const handleRemoveView = (id: string) => {
    setViews(prev => prev.filter(v => v.id !== id))
  }

  const handleRefreshView = (id: string) => {
    setViews(prev => prev.map(v => 
      v.id === id ? { ...v, isLoading: true } : v
    ))
    setTimeout(() => {
      setViews(prev => prev.map(v => 
        v.id === id ? { ...v, isLoading: false, lastUpdated: new Date() } : v
      ))
    }, 1500)
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        
        <main className="flex-1 overflow-auto">
          <DashboardCanvas 
            views={views} 
            onRemoveView={handleRemoveView}
            onRefreshView={handleRefreshView}
          />
        </main>
      </div>

      <ChatInterface onAddView={handleAddView} />
    </div>
  )
}
