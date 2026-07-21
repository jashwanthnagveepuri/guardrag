import { apiClient } from './client'
import type { GuardrailResult, GuardrailStats } from '@/types/api'

export interface ScanTextRequest {
  text: string;
}

export interface ScanTextResponse {
  result: GuardrailResult;
  scan_id: string;
}

export async function scanText(text: string): Promise<ScanTextResponse> {
  const response = await apiClient.post<ScanTextResponse>('/guardrails/scan', { text })
  return response.data
}

export async function getGuardrailStats(): Promise<GuardrailStats> {
  const response = await apiClient.get<GuardrailStats>('/guardrails/stats')
  return response.data
}
