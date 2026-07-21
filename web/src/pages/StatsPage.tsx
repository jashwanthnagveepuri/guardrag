import { useState, useEffect, useCallback } from 'react'
import {
  FileText,
  Layers,
  MessageSquare,
  TrendingUp,
  Shield,
  ShieldX,
  Activity,
  Clock,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { getStats } from '@/api/system'
import type { SystemStats } from '@/types/api'

export default function StatsPage() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getStats()
      setStats(data)
    } catch {
      setError('Failed to load system statistics')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  if (isLoading && !stats) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center py-24">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-sm text-warm-500">Loading system statistics...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center py-24">
        <div className="text-center">
          <Activity className="w-8 h-8 text-danger-500 mx-auto mb-4" />
          <p className="text-sm text-danger-600 mb-3">{error}</p>
          <button
            onClick={fetchStats}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-medium transition-colors mx-auto"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!stats) return null

  const statCards = [
    {
      label: 'Documents',
      value: stats.document_count.toLocaleString(),
      icon: FileText,
      color: 'primary' as const,
      subtitle: 'Total uploaded',
    },
    {
      label: 'Chunks',
      value: stats.chunk_count.toLocaleString(),
      icon: Layers,
      color: 'secondary' as const,
      subtitle: 'Indexed segments',
    },
    {
      label: 'Queries',
      value: stats.query_count.toLocaleString(),
      icon: MessageSquare,
      color: 'primary' as const,
      subtitle: 'Total processed',
    },
    {
      label: 'Avg Confidence',
      value: `${(stats.avg_confidence * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'success' as const,
      subtitle: 'Answer quality',
    },
    {
      label: 'Block Rate',
      value: `${(stats.block_rate * 100).toFixed(1)}%`,
      icon: ShieldX,
      color: 'danger' as const,
      subtitle: 'Threats blocked',
    },
    {
      label: 'Uptime',
      value: formatUptime(stats.uptime_seconds),
      icon: Clock,
      color: 'secondary' as const,
      subtitle: 'System online',
    },
  ]

  const colorMap = {
    primary: {
      bg: 'bg-primary-50',
      icon: 'text-primary-600',
      border: 'border-primary-100',
    },
    secondary: {
      bg: 'bg-secondary-50',
      icon: 'text-secondary-600',
      border: 'border-secondary-100',
    },
    success: {
      bg: 'bg-success-50',
      icon: 'text-success-600',
      border: 'border-success-100',
    },
    warning: {
      bg: 'bg-warning-50',
      icon: 'text-warning-600',
      border: 'border-warning-100',
    },
    danger: {
      bg: 'bg-danger-50',
      icon: 'text-danger-600',
      border: 'border-danger-100',
    },
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">System Statistics</h1>
          <p className="text-sm text-warm-500 mt-1">
            Real-time overview of GuardRAG system performance
          </p>
        </div>
        <button
          onClick={fetchStats}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-warm-200 hover:bg-warm-50 text-secondary-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Version Badge */}
      <div className="bg-white border border-warm-200 rounded-xl px-4 py-3 flex items-center gap-3">
        <Shield className="w-5 h-5 text-primary-500" />
        <div>
          <p className="text-sm font-medium text-secondary-800">
            GuardRAG v{stats.version}
          </p>
          <p className="text-xs text-warm-500">
            All systems operational
          </p>
        </div>
      </div>

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((card) => {
          const colors = colorMap[card.color]
          return (
            <div
              key={card.label}
              className={`bg-white border ${colors.border} rounded-xl p-5 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${colors.bg}`}>
                  <card.icon className={`w-5.5 h-5.5 ${colors.icon}`} />
                </div>
                <span className="text-[10px] font-medium text-warm-400 uppercase tracking-wider">
                  {card.subtitle}
                </span>
              </div>
              <p className="text-3xl font-bold text-secondary-900 tracking-tight">
                {card.value}
              </p>
              <p className="text-sm text-warm-500 mt-1">{card.label}</p>
            </div>
          )
        })}
      </div>

      {/* Confidence & Block Rate Visual */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Confidence Meter */}
        <div className="bg-white border border-warm-200 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-secondary-800 mb-4">
            Average Confidence Score
          </h3>
          <div className="flex items-center gap-4">
            <div className="relative w-32 h-32">
              <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                {/* Background circle */}
                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke="#e7e5e4"
                  strokeWidth="10"
                />
                {/* Progress arc */}
                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke={stats.avg_confidence >= 0.7 ? '#059669' : stats.avg_confidence >= 0.5 ? '#d97706' : '#dc2626'}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 50}`}
                  strokeDashoffset={`${2 * Math.PI * 50 * (1 - stats.avg_confidence)}`}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-secondary-900">
                  {Math.round(stats.avg_confidence * 100)}%
                </span>
              </div>
            </div>
            <div className="flex-1">
              <div className="space-y-2">
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-warm-500">High (&gt;70%)</span>
                    <span className="font-medium text-success-600">
                      {stats.avg_confidence >= 0.7 ? 'Current' : ''}
                    </span>
                  </div>
                  <div className="w-full bg-warm-100 rounded-full h-2">
                    <div className="bg-success-500 h-2 rounded-full" style={{ width: '70%' }} />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-warm-500">Moderate (50-70%)</span>
                    <span className="font-medium text-warning-600">
                      {stats.avg_confidence >= 0.5 && stats.avg_confidence < 0.7 ? 'Current' : ''}
                    </span>
                  </div>
                  <div className="w-full bg-warm-100 rounded-full h-2">
                    <div className="bg-warning-500 h-2 rounded-full" style={{ width: '50%' }} />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-warm-500">Low (&lt;50%)</span>
                    <span className="font-medium text-danger-600">
                      {stats.avg_confidence < 0.5 ? 'Current' : ''}
                    </span>
                  </div>
                  <div className="w-full bg-warm-100 rounded-full h-2">
                    <div className="bg-danger-500 h-2 rounded-full" style={{ width: '30%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Block Rate Visual */}
        <div className="bg-white border border-warm-200 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-secondary-800 mb-4">
            Security Block Rate
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-danger-500" />
                <span className="text-sm text-secondary-700">Blocked Threats</span>
              </div>
              <span className="text-sm font-semibold text-danger-600">
                {(stats.block_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-warm-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-danger-500 h-3 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(stats.block_rate * 100, 100)}%` }}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-success-500" />
                <span className="text-sm text-secondary-700">Allowed Queries</span>
              </div>
              <span className="text-sm font-semibold text-success-600">
                {((1 - stats.block_rate) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-warm-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-success-500 h-3 rounded-full transition-all duration-700"
                style={{ width: `${Math.min((1 - stats.block_rate) * 100, 100)}%` }}
              />
            </div>

            <div className="pt-3 border-t border-warm-100">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-primary-500" />
                <div>
                  <p className="text-sm font-medium text-secondary-700">
                    {stats.query_count > 0
                      ? `${Math.round(stats.block_rate * stats.query_count)} of ${stats.query_count} queries blocked`
                      : 'No queries processed yet'}
                  </p>
                  <p className="text-xs text-warm-500">
                    Multi-layer guardrail protection active
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Summary */}
      <div className="bg-white border border-warm-200 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-secondary-800 mb-4">
          Activity Summary
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-primary-50 rounded-xl mx-auto mb-2">
              <FileText className="w-6 h-6 text-primary-500" />
            </div>
            <p className="text-lg font-bold text-secondary-900">
              {stats.document_count > 0 ? 'Active' : 'Idle'}
            </p>
            <p className="text-xs text-warm-500">Document Processing</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-success-50 rounded-xl mx-auto mb-2">
              <Layers className="w-6 h-6 text-success-500" />
            </div>
            <p className="text-lg font-bold text-secondary-900">
              {stats.chunk_count.toLocaleString()}
            </p>
            <p className="text-xs text-warm-500">Chunks Indexed</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-secondary-50 rounded-xl mx-auto mb-2">
              <MessageSquare className="w-6 h-6 text-secondary-500" />
            </div>
            <p className="text-lg font-bold text-secondary-900">
              {stats.query_count.toLocaleString()}
            </p>
            <p className="text-xs text-warm-500">Queries Served</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-warning-50 rounded-xl mx-auto mb-2">
              <Activity className="w-6 h-6 text-warning-500" />
            </div>
            <p className="text-lg font-bold text-secondary-900">
              {formatUptime(stats.uptime_seconds)}
            </p>
            <p className="text-xs text-warm-500">System Uptime</p>
          </div>
        </div>
      </div>
    </div>
  )
}
