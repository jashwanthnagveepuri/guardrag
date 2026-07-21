import { Routes, Route } from 'react-router-dom'
import { useState, useCallback } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Toast from './components/Toast'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import GuardrailsPage from './pages/GuardrailsPage'
import StatsPage from './pages/StatsPage'
import { setToastCallback } from './api/client'

export interface ToastMessage {
  id: string
  message: string
  type: 'error' | 'warning' | 'success' | 'info'
}

function App() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [isOnline, setIsOnline] = useState(true)

  const addToast = useCallback((message: string, type: ToastMessage['type'] = 'info') => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 5000)
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  // Register toast callback for API errors
  setToastCallback((message: string, type: 'error' | 'warning' | 'success' | 'info') => {
    addToast(message, type)
  })

  return (
    <div className="flex h-screen bg-warm-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 ml-64">
        <Header isOnline={isOnline} setIsOnline={setIsOnline} />
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<ChatPage isOnline={isOnline} />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/guardrails" element={<GuardrailsPage />} />
            <Route path="/stats" element={<StatsPage />} />
          </Routes>
        </main>
      </div>
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </div>
  )
}

export default App
