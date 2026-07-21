import { useState, useCallback, useRef, useEffect } from 'react'
import { User, Bot, Copy, Check } from 'lucide-react'
import type { MessageResponse } from '@/types/api'
import GuardrailBadge from './GuardrailBadge'
import ConfidenceMeter from './ConfidenceMeter'
import SourcePanel from './SourcePanel'

interface ChatMessageProps {
  message: MessageResponse
  isStreaming?: boolean
}

function renderMarkdown(content: string): string {
  let html = content

  // Escape HTML entities
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // Code blocks with language
  html = html.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (_match, lang, code) => {
      const language = lang || ''
      return `<div class="relative group"><pre class="bg-secondary-900 text-warm-100 p-4 rounded-lg mb-4 overflow-x-auto"><div class="flex items-center justify-between mb-2 text-xs text-warm-400 font-mono"><span>${language}</span><button class="copy-btn opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 rounded bg-warm-700 hover:bg-warm-600 text-warm-200 text-xs">Copy</button></div><code>${code.trim()}</code></pre></div>`
    }
  )

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-warm-200 text-secondary-800 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>')

  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // Italic
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mb-2 mt-4 text-secondary-800">$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mb-3 mt-5 text-secondary-900">$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mb-4 mt-6 text-secondary-900">$1</h1>')

  // Unordered lists
  html = html.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')

  // Blockquote
  html = html.replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-primary-400 pl-4 italic text-secondary-600 mb-4">$1</blockquote>')

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr class="my-6 border-warm-300" />')

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary-600 hover:text-primary-700 underline" target="_blank" rel="noopener noreferrer">$1</a>')

  // Tables (simple)
  const tableRegex = /\|(.+)\|\n\|([-:\|\s]+)\|\n((?:\|.+\|\n?)+)/g
  html = html.replace(tableRegex, (_match, header, _sep, rows) => {
    const headers = header.split('|').map((h: string) => h.trim()).filter(Boolean)
    const bodyRows = rows.trim().split('\n').map((row: string) =>
      row.split('|').map((cell: string) => cell.trim()).filter(Boolean)
    )
    let tableHtml = '<table class="w-full border-collapse mb-4"><thead><tr>'
    headers.forEach((h: string) => {
      tableHtml += `<th class="border border-warm-300 bg-warm-100 px-4 py-2 text-left font-semibold text-secondary-700">${h}</th>`
    })
    tableHtml += '</tr></thead><tbody>'
    bodyRows.forEach((row: string[]) => {
      tableHtml += '<tr>'
      row.forEach((cell: string) => {
        tableHtml += `<td class="border border-warm-300 px-4 py-2">${cell}</td>`
      })
      tableHtml += '</tr>'
    })
    tableHtml += '</tbody></table>'
    return tableHtml
  })

  // Paragraphs (wrap remaining text)
  const lines = html.split('\n')
  let inList = false
  let result: string[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (inList) {
        inList = false
      }
      continue
    }
    if (trimmed.startsWith('<li') || trimmed.startsWith('<h') || trimmed.startsWith('<pre') || trimmed.startsWith('<blockquote') || trimmed.startsWith('<hr') || trimmed.startsWith('<table') || trimmed.startsWith('<div') || trimmed.startsWith('</div')) {
      result.push(line)
      continue
    }
    result.push(`<p class="mb-4 leading-relaxed">${trimmed}</p>`)
  }

  return result.join('\n')
}

export default function ChatMessage({ message, isStreaming = false }: ChatMessageProps) {
  const [copiedBlock, setCopiedBlock] = useState<string | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const isUser = message.role === 'user'

  // Handle copy buttons
  useEffect(() => {
    if (!contentRef.current) return
    const buttons = contentRef.current.querySelectorAll('.copy-btn')
    buttons.forEach((btn, idx) => {
      const handler = () => {
        const pre = btn.closest('pre')
        const code = pre?.querySelector('code')
        if (code) {
          const text = code.textContent || ''
          navigator.clipboard.writeText(text)
          setCopiedBlock(`${idx}`)
          setTimeout(() => setCopiedBlock(null), 2000)
        }
      }
      btn.addEventListener('click', handler)
    })
  }, [message.content])

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content)
    setCopiedBlock('content')
    setTimeout(() => setCopiedBlock(null), 2000)
  }, [message.content])

  const htmlContent = isUser ? message.content : renderMarkdown(message.content)

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} animate-fade-in`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isUser ? 'bg-primary-500' : 'bg-secondary-700'
        }`}
      >
        {isUser ? (
          <User className="w-4.5 h-4.5 text-white" />
        ) : (
          <Bot className="w-4.5 h-4.5 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : 'text-left'}`}>
        <div
          className={`inline-block text-left rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-primary-500 text-white'
              : 'bg-white border border-warm-200 text-secondary-800 shadow-sm'
          }`}
        >
          {/* Role label */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-xs font-medium ${isUser ? 'text-primary-100' : 'text-warm-400'}`}>
              {isUser ? 'You' : 'GuardRAG'}
            </span>
            {!isUser && !isStreaming && (
              <button
                onClick={handleCopy}
                className="text-warm-400 hover:text-secondary-600 transition-colors"
                title="Copy response"
                aria-label="Copy response"
              >
                {copiedBlock === 'content' ? (
                  <Check className="w-3.5 h-3.5 text-success-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>

          {/* Content */}
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div
              ref={contentRef}
              className="markdown-content text-sm"
              dangerouslySetInnerHTML={{ __html: htmlContent }}
            />
          )}

          {/* Streaming cursor */}
          {!isUser && isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-primary-500 ml-0.5 animate-pulse align-middle" />
          )}
        </div>

        {/* Assistant metadata below message */}
        {!isUser && !isStreaming && (
          <div className="mt-2 space-y-2">
            {/* Guardrail Badge */}
            {message.guardrail_result && (
              <GuardrailBadge guardrail={message.guardrail_result} showLayer />
            )}

            {/* Confidence Meter */}
            {typeof message.confidence_score === 'number' && (
              <ConfidenceMeter score={message.confidence_score} />
            )}

            {/* Source Panel */}
            {message.sources && message.sources.length > 0 && (
              <SourcePanel sources={message.sources} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
