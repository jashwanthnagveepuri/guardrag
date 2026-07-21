import { apiClient } from './client'
import type { ChatRequest, ChatResponse, MessageResponse } from '@/types/api'

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/chat', request)
  return response.data
}

export async function getMessages(conversationId: string): Promise<MessageResponse[]> {
  const response = await apiClient.get<MessageResponse[]>(`/chat/${conversationId}/messages`)
  return response.data
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/chat/${conversationId}`)
}

export function createSSEConnection(
  conversationId: string,
  callbacks: {
    onStart: () => void
    onToken: (token: string) => void
    onSources: (sources: MessageResponse['sources']) => void
    onGuardrail: (guardrail: NonNullable<MessageResponse['guardrail_result']>) => void
    onDone: (data: { answer: string; confidence_score: number; conversation_id: string }) => void
    onError: (message: string) => void
  }
): EventSource {
  const eventSource = new EventSource(`/api/stream/chat/${conversationId}`)

  eventSource.addEventListener('start', () => {
    callbacks.onStart()
  })

  eventSource.addEventListener('token', (event) => {
    try {
      const data = JSON.parse(event.data) as { token: string }
      callbacks.onToken(data.token)
    } catch {
      callbacks.onToken(event.data)
    }
  })

  eventSource.addEventListener('sources', (event) => {
    try {
      const data = JSON.parse(event.data) as { sources: MessageResponse['sources'] }
      callbacks.onSources(data.sources)
    } catch {
      // ignore
    }
  })

  eventSource.addEventListener('guardrail', (event) => {
    try {
      const data = JSON.parse(event.data) as { guardrail: NonNullable<MessageResponse['guardrail_result']> }
      callbacks.onGuardrail(data.guardrail)
    } catch {
      // ignore
    }
  })

  eventSource.addEventListener('done', (event) => {
    try {
      const data = JSON.parse(event.data) as { answer: string; confidence_score: number; conversation_id: string }
      callbacks.onDone(data)
    } catch {
      callbacks.onDone({ answer: '', confidence_score: 0, conversation_id: conversationId })
    }
    eventSource.close()
  })

  eventSource.addEventListener('error', (event) => {
    let message = 'Stream error occurred'
    try {
      const data = JSON.parse((event as MessageEvent).data || '{}') as { message?: string }
      if (data.message) message = data.message
    } catch {
      // use default message
    }
    callbacks.onError(message)
    eventSource.close()
  })

  return eventSource
}
