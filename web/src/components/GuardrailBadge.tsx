import { ShieldCheck, ShieldAlert, ShieldX, Info } from 'lucide-react'
import type { GuardrailResult } from '@/types/api'

interface GuardrailBadgeProps {
  guardrail: GuardrailResult
  showLayer?: boolean
  size?: 'sm' | 'md'
}

const config = {
  pass: {
    icon: ShieldCheck,
    label: 'Passed',
    className: 'bg-success-50 text-success-700 border-success-200',
    iconColor: 'text-success-500',
  },
  block: {
    icon: ShieldX,
    label: 'Blocked',
    className: 'bg-danger-50 text-danger-700 border-danger-200',
    iconColor: 'text-danger-500',
  },
  warn: {
    icon: ShieldAlert,
    label: 'Warning',
    className: 'bg-warning-50 text-warning-700 border-warning-200',
    iconColor: 'text-warning-500',
  },
}

const layerLabels: Record<string, string> = {
  input: 'Input Filter',
  retrieval: 'Retrieval Filter',
  output: 'Output Filter',
}

export default function GuardrailBadge({ guardrail, showLayer = false, size = 'sm' }: GuardrailBadgeProps) {
  const c = config[guardrail.action]
  const Icon = c.icon
  const isSmall = size === 'sm'

  return (
    <div className="group relative inline-flex items-center">
      <div
        className={`inline-flex items-center gap-1.5 rounded-full border ${c.className} ${
          isSmall ? 'px-2.5 py-1' : 'px-3 py-1.5'
        }`}
      >
        <Icon className={`${isSmall ? 'w-3.5 h-3.5' : 'w-4 h-4'} ${c.iconColor}`} />
        <span className={`font-medium ${isSmall ? 'text-xs' : 'text-sm'}`}>{c.label}</span>
        {guardrail.confidence > 0 && (
          <span className={`${isSmall ? 'text-[10px]' : 'text-xs'} opacity-70`}>
            {Math.round(guardrail.confidence * 100)}%
          </span>
        )}
      </div>

      {/* Tooltip */}
      <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-30">
        <div className="bg-secondary-800 text-white text-xs rounded-lg py-2 px-3 shadow-lg max-w-xs whitespace-normal">
          <div className="flex items-start gap-2 mb-1">
            <Info className="w-3.5 h-3.5 text-warm-400 mt-0.5 shrink-0" />
            <div>
              {showLayer && (
                <p className="font-medium text-warm-200 mb-0.5">{layerLabels[guardrail.layer]}</p>
              )}
              <p className="text-warm-400">{guardrail.reason}</p>
            </div>
          </div>
          <div className="absolute left-4 -bottom-1 w-2 h-2 bg-secondary-800 rotate-45" />
        </div>
      </div>
    </div>
  )
}
