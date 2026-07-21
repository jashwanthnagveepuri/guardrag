import { useState, useCallback } from 'react'
import { Shield, Loader2, AlertTriangle, ShieldCheck, ShieldX, Scan, Trash2 } from 'lucide-react'
import { scanText, getGuardrailStats } from '@/api/guardrails'
import type { GuardrailResult, GuardrailStats, GuardrailScan } from '@/types/api'

type TabType = 'scanner' | 'stats' | 'history'

export default function GuardrailsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('scanner')
  const [scanTextValue, setScanTextValue] = useState('')
  const [scanResult, setScanResult] = useState<GuardrailResult | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [stats, setStats] = useState<GuardrailStats | null>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(false)
  const [scanHistory, setScanHistory] = useState<GuardrailScan[]>([])

  const handleScan = useCallback(async () => {
    const trimmed = scanTextValue.trim()
    if (!trimmed) return
    setIsScanning(true)
    setScanResult(null)
    try {
      const response = await scanText(trimmed)
      setScanResult(response.result)
      // Add to history
      const newScan: GuardrailScan = {
        id: response.scan_id,
        text: trimmed,
        result: response.result,
        timestamp: new Date().toISOString(),
      }
      setScanHistory((prev) => [newScan, ...prev].slice(0, 50))
    } catch {
      // error handled by API client
    } finally {
      setIsScanning(false)
    }
  }, [scanTextValue])

  const handleLoadStats = useCallback(async () => {
    setIsLoadingStats(true)
    try {
      const data = await getGuardrailStats()
      setStats(data)
    } catch {
      // error handled by API client
    } finally {
      setIsLoadingStats(false)
    }
  }, [])

  const handleTabChange = useCallback(
    (tab: TabType) => {
      setActiveTab(tab)
      if (tab === 'stats' && !stats) {
        handleLoadStats()
      }
    },
    [stats, handleLoadStats]
  )

  const clearHistory = useCallback(() => {
    setScanHistory([])
  }, [])

  const getActionConfig = (action: GuardrailResult['action']) => {
    switch (action) {
      case 'pass':
        return {
          icon: ShieldCheck,
          label: 'Passed',
          bgClass: 'bg-success-50 border-success-200',
          iconClass: 'text-success-500',
          textClass: 'text-success-700',
        }
      case 'block':
        return {
          icon: ShieldX,
          label: 'Blocked',
          bgClass: 'bg-danger-50 border-danger-200',
          iconClass: 'text-danger-500',
          textClass: 'text-danger-700',
        }
      case 'warn':
        return {
          icon: AlertTriangle,
          label: 'Warning',
          bgClass: 'bg-warning-50 border-warning-200',
          iconClass: 'text-warning-500',
          textClass: 'text-warning-700',
        }
    }
  }

  const layerLabels: Record<string, string> = {
    input: 'Input Filter',
    retrieval: 'Retrieval Filter',
    output: 'Output Filter',
  }

  const tabs = [
    { id: 'scanner' as TabType, label: 'Scanner', icon: Scan },
    { id: 'stats' as TabType, label: 'Statistics', icon: Shield },
    { id: 'history' as TabType, label: 'History', icon: ShieldCheck },
  ]

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Guardrails</h1>
        <p className="text-sm text-warm-500 mt-1">
          Multi-layer security system for prompt injection detection and content filtering
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-white border border-warm-200 rounded-lg p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-primary-50 text-primary-700'
                : 'text-secondary-600 hover:bg-warm-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Scanner Tab */}
      {activeTab === 'scanner' && (
        <div className="bg-white border border-warm-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="text-sm font-medium text-secondary-800 mb-2 block">
              Test Text Scan
            </label>
            <textarea
              value={scanTextValue}
              onChange={(e) => setScanTextValue(e.target.value)}
              placeholder="Enter text to scan for security threats..."
              rows={4}
              className="w-full resize-none rounded-lg border border-warm-300 bg-warm-50 px-4 py-3 text-sm text-secondary-800 placeholder:text-warm-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-xs text-warm-400">
              Tests all three guardrail layers: Input, Retrieval, and Output
            </p>
            <button
              onClick={handleScan}
              disabled={isScanning || !scanTextValue.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 disabled:bg-warm-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Scan className="w-4 h-4" />
                  Scan Text
                </>
              )}
            </button>
          </div>

          {/* Scan Result */}
          {scanResult && (
            <div className={`rounded-lg border p-4 ${getActionConfig(scanResult.action).bgClass}`}>
              <div className="flex items-start gap-3">
                {(() => {
                  const config = getActionConfig(scanResult.action)
                  const Icon = config.icon
                  return <Icon className={`w-5 h-5 mt-0.5 ${config.iconClass}`} />
                })()}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-semibold ${getActionConfig(scanResult.action).textClass}`}>
                      {getActionConfig(scanResult.action).label}
                    </span>
                    <span className="text-xs text-warm-500">
                      via {layerLabels[scanResult.layer]}
                    </span>
                  </div>
                  <p className="text-sm text-secondary-700">{scanResult.reason}</p>
                  {scanResult.confidence > 0 && (
                    <div className="mt-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-warm-500">Confidence</span>
                        <div className="flex-1 max-w-[200px] bg-white/50 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              scanResult.confidence > 0.7
                                ? 'bg-success-500'
                                : scanResult.confidence > 0.4
                                ? 'bg-warning-500'
                                : 'bg-danger-500'
                            }`}
                            style={{ width: `${Math.round(scanResult.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-secondary-700">
                          {Math.round(scanResult.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === 'stats' && (
        <div className="space-y-6">
          {!stats && isLoadingStats && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 text-warm-400 animate-spin" />
              <span className="ml-2 text-sm text-warm-500">Loading statistics...</span>
            </div>
          )}

          {stats && (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  label="Total Queries"
                  value={stats.total_queries.toLocaleString()}
                  icon={Shield}
                  color="primary"
                />
                <StatCard
                  label="Blocked"
                  value={stats.blocked_queries.toLocaleString()}
                  icon={ShieldX}
                  color="danger"
                />
                <StatCard
                  label="Warnings"
                  value={stats.warned_queries.toLocaleString()}
                  icon={AlertTriangle}
                  color="warning"
                />
                <StatCard
                  label="Block Rate"
                  value={`${(stats.block_rate * 100).toFixed(1)}%`}
                  icon={ShieldCheck}
                  color="success"
                />
              </div>

              {/* Layer Breakdown Chart */}
              <div className="bg-white border border-warm-200 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-secondary-800 mb-4">
                  Layer Breakdown
                </h3>
                <div className="space-y-4">
                  {(['input', 'retrieval', 'output'] as const).map((layer) => {
                    const layerStats = stats.layer_stats[layer]
                    const total = layerStats.total || 1
                    const blockedWidth = (layerStats.blocked / total) * 100
                    const warnedWidth = (layerStats.warned / total) * 100
                    const passedWidth = 100 - blockedWidth - warnedWidth

                    return (
                      <div key={layer}>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-secondary-700">
                            {layerLabels[layer]}
                          </span>
                          <span className="text-xs text-warm-500">
                            {layerStats.total.toLocaleString()} checks
                          </span>
                        </div>
                        <div className="flex h-8 rounded-lg overflow-hidden">
                          {passedWidth > 0 && (
                            <div
                              className="bg-success-500 flex items-center justify-center text-white text-xs font-medium"
                              style={{ width: `${passedWidth}%` }}
                            >
                              {passedWidth > 15 && `${Math.round(passedWidth)}%`}
                            </div>
                          )}
                          {warnedWidth > 0 && (
                            <div
                              className="bg-warning-500 flex items-center justify-center text-white text-xs font-medium"
                              style={{ width: `${warnedWidth}%` }}
                            >
                              {warnedWidth > 15 && `${Math.round(warnedWidth)}%`}
                            </div>
                          )}
                          {blockedWidth > 0 && (
                            <div
                              className="bg-danger-500 flex items-center justify-center text-white text-xs font-medium"
                              style={{ width: `${blockedWidth}%` }}
                            >
                              {blockedWidth > 15 && `${Math.round(blockedWidth)}%`}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-1">
                          <span className="text-xs text-success-600">
                            {layerStats.total - layerStats.blocked - layerStats.warned} passed
                          </span>
                          <span className="text-xs text-warning-600">
                            {layerStats.warned} warned
                          </span>
                          <span className="text-xs text-danger-600">
                            {layerStats.blocked} blocked
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="bg-white border border-warm-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-warm-100">
            <h3 className="text-sm font-semibold text-secondary-800">
              Recent Scans ({scanHistory.length})
            </h3>
            {scanHistory.length > 0 && (
              <button
                onClick={clearHistory}
                className="flex items-center gap-1.5 text-xs text-warm-500 hover:text-danger-600 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear
              </button>
            )}
          </div>

          {scanHistory.length === 0 ? (
            <div className="text-center py-12">
              <Shield className="w-10 h-10 text-warm-300 mx-auto mb-3" />
              <p className="text-sm text-warm-500">No scan history yet</p>
              <p className="text-xs text-warm-400 mt-1">
                Use the scanner to test guardrails
              </p>
            </div>
          ) : (
            <div className="divide-y divide-warm-100 max-h-[600px] overflow-auto">
              {scanHistory.map((scan) => {
                const config = getActionConfig(scan.result.action)
                const Icon = config.icon
                return (
                  <div key={scan.id} className="px-6 py-4 hover:bg-warm-50 transition-colors">
                    <div className="flex items-start gap-3">
                      <Icon className={`w-4 h-4 mt-1 ${config.iconClass}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-semibold ${config.textClass}`}>
                            {config.label}
                          </span>
                          <span className="text-[10px] text-warm-400">
                            {layerLabels[scan.result.layer]}
                          </span>
                          <span className="text-[10px] text-warm-400 ml-auto">
                            {new Date(scan.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm text-secondary-700 truncate mb-1">{scan.text}</p>
                        <p className="text-xs text-warm-500">{scan.result.reason}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  color: 'primary' | 'success' | 'warning' | 'danger'
}) {
  const colorClasses = {
    primary: 'bg-primary-50 text-primary-600',
    success: 'bg-success-50 text-success-600',
    warning: 'bg-warning-50 text-warning-600',
    danger: 'bg-danger-50 text-danger-600',
  }

  return (
    <div className="bg-white border border-warm-200 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-2xl font-bold text-secondary-900">{value}</p>
      <p className="text-xs text-warm-500 mt-1">{label}</p>
    </div>
  )
}
