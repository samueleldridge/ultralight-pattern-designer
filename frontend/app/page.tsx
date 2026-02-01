'use client'

import { useState } from 'react'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { DashboardCanvas } from '@/components/dashboard/DashboardCanvas'
import { SuggestionsPanel } from '@/components/suggestions/SuggestionsPanel'

export default function Home() {
  const [views, setViews] = useState<any[]>([])

  const handleAddView = (view: any) => {
    setViews([...views, view])
  }

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold">AI Analytics</h1>
          <span className="text-sm text-gray-500">Dashboard: Sales Overview</span>
        </div>
        <div className="flex items-center gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + Add View
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-64px)]">
        {/* Sidebar - Suggestions */}
        <aside className="w-80 bg-white border-r overflow-y-auto">
          <SuggestionsPanel />
        </aside>

        {/* Dashboard Canvas */}
        <div className="flex-1 overflow-auto p-6">
          <DashboardCanvas views={views} />
        </div>
      </div>

      {/* Chat Panel */}
      <ChatPanel onAddView={handleAddView} />
    </main>
  )
}
