import { useEffect, useState } from 'react'
import { X, AlertCircle, AlertTriangle, CheckCircle, Info } from 'lucide-react'

interface ToastProps {
  message: string
  type: 'error' | 'warning' | 'success' | 'info'
  onClose: () => void
}

const iconMap = {
  error: AlertCircle,
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
}

const styleMap = {
  error: 'bg-danger-50 text-danger-700 border-danger-200',
  warning: 'bg-warning-50 text-warning-700 border-warning-200',
  success: 'bg-success-50 text-success-700 border-success-200',
  info: 'bg-secondary-50 text-secondary-700 border-secondary-200',
}

const iconColorMap = {
  error: 'text-danger-500',
  warning: 'text-warning-500',
  success: 'text-success-500',
  info: 'text-secondary-500',
}

export default function Toast({ message, type, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(false)
  const Icon = iconMap[type]

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  const handleClose = () => {
    setIsVisible(false)
    setTimeout(onClose, 200)
  }

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-lg border shadow-sm min-w-[320px] max-w-md transition-all duration-200 ${styleMap[type]} ${
        isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
      }`}
    >
      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconColorMap[type]}`} />
      <p className="text-sm flex-1">{message}</p>
      <button
        onClick={handleClose}
        className="text-warm-400 hover:text-warm-600 transition-colors shrink-0 mt-0.5"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
