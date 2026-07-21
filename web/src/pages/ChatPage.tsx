import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageSquare, Shield, FileText, Sparkles } from 'lucide-react'
import ChatInput from '@/components/ChatInput'
import ChatMessage from '@/components/ChatMessage'
import { useDocuments } from '@/hooks/useDocuments'
import { useSSE } from '@/hooks/useSSE'
import { sendMessage } from '@/api/chat'
import type { MessageResponse, SourceCitation, GuardrailResult } from '@/types/api'

interface ChatPageProps {
  isOnline: boolean
}

interface StreamingMessage extends MessageResponse {
  isStreaming?: boolean
}

const EXAMPLE_QUESTIONS = [
  'What are the key findings in the uploaded documents?',
  'Summarize the main points from all documents.',
  'What does the document say about security policies?',
  'Compare and contrast the approaches mentioned.',
]

export default function ChatPage({ isOnline }: ChatPageProps) {
  const [messages, setMessages] = useState<StreamingMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { documents } = useDocuments()
  const sse = useSSE()

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sse.text])

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      sse.closeConnection()
    }
  }, [sse])

  const handleSendMessage = useCallback(
    async (question: string, documentIds: string[]) => {
      if (!isOnline) return

      const userMessage: StreamingMessage = {
        id: `user-${Date.now()}`,
        conversation_id: conversationId || '',
        role: 'user',
        content: question,
        created_at: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, userMessage])
      setIsLoading(true)

      try {
        const request = {
          question,
          conversation_id: conversationId || undefined,
          document_ids: documentIds.length > 0 ? documentIds : undefined,
        }

        const response = await sendMessage(request)
        setConversationId(response.conversation_id)

        // Start SSE streaming
        sse.startStream(response.conversation_id)

        // Add placeholder assistant message
        const assistantMessage: StreamingMessage = {
          id: `assistant-${Date.now()}`,
          conversation_id: response.conversation_id,
          role: 'assistant',
          content: '',
          sources: [],
          confidence_score: undefined,
          guardrail_result: undefined,
          created_at: new Date().toISOString(),
          isStreaming: true,
        }

        setMessages((prev) => [...prev, assistantMessage])
      } catch {
        setIsLoading(false)
      }
    },
    [isOnline, conversationId, sse]
  )

  // Update assistant message as SSE tokens arrive
  useEffect(() => {
    if (!sse.isStreaming && !sse.isComplete) return

    setMessages((prev) => {
      const lastMsg = prev[prev.length - 1]
      if (!lastMsg || lastMsg.role !== 'assistant') return prev

      return [
        ...prev.slice(0, -1),
        {
          ...lastMsg,
          content: sse.text,
          sources: sse.sources.length > 0 ? sse.sources : lastMsg.sources,
          guardrail_result: sse.guardrail || lastMsg.guardrail_result,
          isStreaming: sse.isStreaming,
        },
      ]
    })

    if (sse.isComplete) {
      setIsLoading(false)
    }
  }, [sse.text, sse.sources, sse.guardrail, sse.isStreaming, sse.isComplete])

  const hasCompletedDocs = documents.some((d) => d.status === 'completed')

  return (
    <div className="h-full flex flex-col -m-6">
      {/* Messages Area */}
      <div className="flex-1 overflow-auto px-4 py-6 sm:px-6 lg:px-8">
        {messages.length === 0 ? (
          /* Welcome Screen */
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mb-6">
              <Shield className="w-8 h-8 text-primary-500" />
            </div>
            <h2 className="text-2xl font-bold text-secondary-900 mb-2">
              Welcome to GuardRAG
            </h2>
            <p className="text-sm text-warm-500 text-center mb-8 max-w-md">
              Ask questions about your uploaded documents. Our secure RAG system with
              multi-layer guardrails will provide trustworthy answers with cited sources.
            </p>

            {!hasCompletedDocs ? (
              <div className="bg-warning-50 border border-warning-200 rounded-xl p-4 flex items-start gap-3 max-w-md">
                <FileText className="w-5 h-5 text-warning-500 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-warning-700">No documents available</p>
                  <p className="text-xs text-warning-600 mt-1">
                    Go to the Documents page to upload files before asking questions.
                  </p>
                </div>
              </div>
            ) : (
              <div className="w-full space-y-2">
                <p className="text-xs font-medium text-warm-400 uppercase tracking-wider mb-3 text-center">
                  Try asking
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {EXAMPLE_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(q, [])}
                      className="text-left p-3 bg-white border border-warm-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors group"
                    >
                      <div className="flex items-start gap-2">
                        <Sparkles className="w-4 h-4 text-warm-400 group-hover:text-primary-500 mt-0.5 shrink-0" />
                        <span className="text-sm text-secondary-700 group-hover:text-primary-700">
                          {q}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Stats row */}
            <div className="flex items-center gap-6 mt-8 text-xs text-warm-400">
              <div className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" />
                <span>3-Layer Guardrails</span>
              </div>
              <div className="flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Source Citations</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Real-time Streaming</span>
              </div>
            </div>
          </div>
        ) : (
          /* Message List */
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isStreaming={msg.isStreaming}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="shrink-0">
        <ChatInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          documents={documents}
          disabled={!hasCompletedDocs || !isOnline}
        />
      </div>
    </div>
  )
}
