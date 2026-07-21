import { useState } from 'react'
import { ChevronDown, FileText, ExternalLink } from 'lucide-react'
import type { SourceCitation } from '@/types/api'

interface SourcePanelProps {
  sources: SourceCitation[]
}

function getScoreColor(score: number): string {
  if (score >= 0.7) return 'bg-success-500'
  if (score >= 0.5) return 'bg-warning-500'
  return 'bg-danger-500'
}

function getScoreTextColor(score: number): string {
  if (score >= 0.7) return 'text-success-600'
  if (score >= 0.5) return 'text-warning-600'
  return 'text-danger-600'
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="bg-warm-50 border border-warm-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-warm-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-warm-500" />
          <span className="text-xs font-medium text-secondary-700">
            Sources ({sources.length})
          </span>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-warm-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-warm-200 divide-y divide-warm-200 max-h-72 overflow-auto">
          {sources.map((source, index) => (
            <div key={source.chunk_id} className="px-3 py-3">
              {/* Source header */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="flex items-center justify-center w-5 h-5 bg-warm-200 text-warm-600 rounded-full text-[10px] font-semibold shrink-0">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-secondary-700 truncate">
                      {source.document_name}
                    </p>
                    <p className="text-[10px] text-warm-400">ID: {source.chunk_id.slice(0, 8)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-semibold ${getScoreTextColor(source.similarity_score)}`}>
                    {Math.round(source.similarity_score * 100)}%
                  </span>
                  <ExternalLink className="w-3 h-3 text-warm-400 hover:text-primary-500 cursor-pointer" />
                </div>
              </div>

              {/* Similarity bar */}
              <div className="w-full bg-warm-200 rounded-full h-1 mb-2">
                <div
                  className={`${getScoreColor(source.similarity_score)} h-1 rounded-full`}
                  style={{ width: `${Math.round(source.similarity_score * 100)}%` }}
                />
              </div>

              {/* Content preview */}
              <p className="text-xs text-secondary-600 leading-relaxed bg-white rounded-md p-2 border border-warm-100">
                {source.content_preview}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
