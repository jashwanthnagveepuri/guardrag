import { apiClient } from './client'
import type { DocumentResponse, DocumentChunk } from '@/types/api'

export interface UploadDocumentResponse {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
}

export async function uploadDocument(file: File, onProgress?: (percent: number) => void): Promise<UploadDocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<UploadDocumentResponse>('/documents', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percent)
      }
    },
  })
  return response.data
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  const response = await apiClient.get<DocumentResponse[]>('/documents')
  return response.data
}

export async function getDocument(id: string): Promise<DocumentResponse> {
  const response = await apiClient.get<DocumentResponse>(`/documents/${id}`)
  return response.data
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}`)
}

export async function getDocumentChunks(id: string): Promise<DocumentChunk[]> {
  const response = await apiClient.get<DocumentChunk[]>(`/documents/${id}/chunks`)
  return response.data
}
