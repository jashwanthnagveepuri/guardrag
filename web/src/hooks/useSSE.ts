import { useState, useCallback, useRef } from 'react'
import type { SourceCitation, GuardrailResult } from '@/types/api'

interface SSEState {
  tokens: string[]
  text: string
  sources: SourceCitation[]
  guardrail: GuardrailResult | null
  isStreaming: boolean
  isComplete: boolean
  error: string | null
}

const initialState: SSEState = {
  tokens: [],
  text: '',
  sources: [],
  guardrail: null,
  isStreaming: false,
  isComplete: false,
  error: null,
}

export function useSSE() {
  const [state, setState] = useState<SSEState>(initialState)
  const eventSourceRef = useRef<EventSource | null>(null)

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  const startStream = useCallback(
    (conversationId: string) => {
      closeConnection()
      setState({ ...initialState, isStreaming: true })

      const eventSource = new EventSource(`/api/stream/chat/${conversationId}`)
      eventSourceRef.current = eventSource

      eventSource.addEventListener('start', () => {
        setState((prev) => ({ ...prev, isStreaming: true }))
      })

      eventSource.addEventListener('token', (event) => {
        try {
          const data = JSON.parse(event.data) as { token: string }
          setState((prev) => ({
            ...prev,
            tokens: [...prev.tokens, data.token],
            text: prev.text + data.token,
          }))
        } catch {
          setState((prev) => ({
            ...prev,
            tokens: [...prev.tokens, event.data],
            text: prev.text + event.data,
          }))
        }
      })

      eventSource.addEventListener('sources', (event) => {
        try {
          const data = JSON.parse(event.data) as { sources: SourceCitation[] }
          setState((prev) => ({ ...prev, sources: data.sources }))
        } catch {
          // ignore parse errors
        }
      })

      eventSource.addEventListener('guardrail', (event) => {
        try {
          const data = JSON.parse(event.data) as { guardrail: GuardrailResult }
          setState((prev) => ({ ...prev, guardrail: data.guardrail }))
        } catch {
          // ignore parse errors
        }
      })

      eventSource.addEventListener('done', (event) => {
        try {
          const data = JSON.parse(event.data) as {
            answer: string
            confidence_score: number
            conversation_id: string
          }
          setState((prev) => ({
            ...prev,
            text: data.answer || prev.text,
            isStreaming: false,
            isComplete: true,
          }))
        } catch {
          setState((prev) => ({ ...prev, isStreaming: false, isComplete: true }))
        }
        eventSource.close()
        eventSourceRef.current = null
      })

      eventSource.addEventListener('error', (event) => {
        let message = 'Stream error occurred'
        try {
          const data = JSON.parse((event as MessageEvent).data || '{}') as {
            message?: string
          }
          if (data.message) message = data.message
        } catch {
          // use default
        }
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: message,
        }))
        eventSource.close()
        eventSourceRef.current = null
      })
    },
    [closeConnection]
  )

  const reset = useCallback(() => {
    closeConnection()
    setState(initialState)
  }, [closeConnection])

  return {
    ...state,
    startStream,
    closeConnection,
    reset,
  }
}
