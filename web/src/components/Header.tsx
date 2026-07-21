import { Shield, Wifi, WifiOff } from 'lucide-react'
import { Link } from 'react-router-dom'
import { healthCheck } from '@/api/system'
import { useEffect, useState } from 'react'

interface HeaderProps {
  isOnline: boolean
  setIsOnline: (online: boolean) => void
}

export default function Header({ isOnline, setIsOnline }: HeaderProps) {
  const [version, setVersion] = useState<string>('')

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await healthCheck()
        setIsOnline(data.status === 'healthy')
        setVersion(data.version)
      } catch {
        setIsOnline(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [setIsOnline])

  return (
    <header className="h-16 bg-white border-b border-warm-200 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="w-9 h-9 bg-primary-500 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div className="flex items-baseline gap-2">
            <h1 className="text-xl font-bold text-secondary-900 tracking-tight">
              GuardRAG
            </h1>
            <span className="text-xs text-warm-400 font-medium">Secure Document Q&A</span>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-4">
        {version && (
          <span className="text-xs text-warm-400 font-mono">v{version}</span>
        )}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
            isOnline
              ? 'bg-success-50 text-success-600'
              : 'bg-danger-50 text-danger-600'
          }`}
        >
          {isOnline ? (
            <>
              <Wifi className="w-3.5 h-3.5" />
              <span>Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5" />
              <span>Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
