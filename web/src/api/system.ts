import { apiClient } from './client'
import type { HealthCheck, SystemStats } from '@/types/api'

export async function healthCheck(): Promise<HealthCheck> {
  const response = await apiClient.get<HealthCheck>('/health')
  return response.data
}

export async function getStats(): Promise<SystemStats> {
  const response = await apiClient.get<SystemStats>('/stats')
  return response.data
}
