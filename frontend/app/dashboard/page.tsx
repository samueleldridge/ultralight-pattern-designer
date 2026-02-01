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
  type: 'line' | 'bar' | 'table' | 'metric'
  data: any[]
  lastUpdated: Date
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

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        
        <main className="flex-1 overflow-auto">
          <DashboardCanvas 
            views={views} 
            onRemoveView={handleRemoveView}
          />
        </main>
      </div>

      <ChatInterface onAddView={handleAddView} />
    </div>
  )
}
