import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, ChevronDown, FileText } from 'lucide-react'
import type { DocumentResponse } from '@/types/api'

interface ChatInputProps {
  onSend: (message: string, documentIds: string[]) => void
  isLoading: boolean
  documents: DocumentResponse[]
  disabled?: boolean
}

export default function ChatInput({ onSend, isLoading, documents, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [showDocSelector, setShowDocSelector] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const docSelectorRef = useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [message])

  // Close doc selector on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        docSelectorRef.current &&
        !docSelectorRef.current.contains(event.target as Node)
      ) {
        setShowDocSelector(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSend = useCallback(() => {
    const trimmed = message.trim()
    if (!trimmed || isLoading || disabled) return
    onSend(trimmed, selectedDocIds)
    setMessage('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [message, isLoading, disabled, selectedDocIds, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  const toggleDoc = useCallback((docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    )
  }, [])

  const completedDocs = documents.filter((d) => d.status === 'completed')

  return (
    <div className="border-t border-warm-200 bg-white px-4 py-3">
      {/* Selected documents chips */}
      {selectedDocIds.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selectedDocIds.map((docId) => {
            const doc = documents.find((d) => d.id === docId)
            if (!doc) return null
            return (
              <span
                key={docId}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 rounded-md text-xs font-medium"
              >
                <FileText className="w-3 h-3" />
                {doc.filename}
                <button
                  onClick={() => toggleDoc(docId)}
                  className="hover:text-primary-900 ml-0.5"
                  aria-label={`Remove ${doc.filename}`}
                >
                  ×
                </button>
              </span>
            )
          })}
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Document Selector */}
        {completedDocs.length > 0 && (
          <div className="relative" ref={docSelectorRef}>
            <button
              onClick={() => setShowDocSelector(!showDocSelector)}
              className="flex items-center gap-1 px-3 py-2.5 text-xs font-medium text-secondary-600 bg-warm-100 hover:bg-warm-200 rounded-lg transition-colors"
              aria-label="Select documents"
            >
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">
                {selectedDocIds.length > 0 ? `${selectedDocIds.length} doc` : 'All docs'}
              </span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {showDocSelector && (
              <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-warm-200 rounded-xl shadow-lg z-20 py-1 max-h-64 overflow-auto">
                <div className="px-3 py-2 border-b border-warm-100">
                  <p className="text-xs font-medium text-warm-500 uppercase">Select documents</p>
                </div>
                {completedDocs.map((doc) => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-2.5 px-3 py-2 hover:bg-warm-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocIds.includes(doc.id)}
                      onChange={() => toggleDoc(doc.id)}
                      className="w-4 h-4 rounded border-warm-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-secondary-700 truncate flex-1">{doc.filename}</span>
                    <span className="text-xs text-warm-400">{doc.chunk_count} chunks</span>
                  </label>
                ))}
                {selectedDocIds.length > 0 && (
                  <div className="border-t border-warm-100 px-3 py-2">
                    <button
                      onClick={() => setSelectedDocIds([])}
                      className="text-xs text-warm-500 hover:text-secondary-700 font-medium"
                    >
                      Clear selection
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Upload documents to start chatting...' : 'Ask a question about your documents...'}
          disabled={isLoading || disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-warm-300 bg-warm-50 px-4 py-2.5 text-sm text-secondary-800 placeholder:text-warm-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed min-h-[42px] max-h-[200px]"
        />

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={isLoading || !message.trim() || disabled}
          className="flex items-center justify-center w-10 h-10 bg-primary-500 hover:bg-primary-600 disabled:bg-warm-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors shrink-0"
          aria-label="Send message"
        >
          {isLoading ? (
            <Loader2 className="w-4.5 h-4.5 animate-spin" />
          ) : (
            <Send className="w-4.5 h-4.5" />
          )}
        </button>
      </div>

      <p className="text-[11px] text-warm-400 mt-1.5 ml-1">
        Ctrl+Enter to send
      </p>
    </div>
  )
}
