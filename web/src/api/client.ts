import axios, { AxiosError } from 'axios'
import type { ApiError } from '@/types/api'

type ToastType = 'error' | 'warning' | 'success' | 'info'

let toastCallback: ((message: string, type: ToastType) => void) | null = null

export function setToastCallback(callback: (message: string, type: ToastType) => void): void {
  toastCallback = callback
}

function showToast(message: string, type: ToastType = 'error'): void {
  if (toastCallback) {
    toastCallback(message, type)
  }
}

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    showToast('Failed to send request. Please try again.', 'error')
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const code = error.response?.data?.code

    if (!status) {
      showToast('Network error. Please check your connection.', 'error')
    } else if (status === 400) {
      showToast(detail || 'Bad request. Please check your input.', 'warning')
    } else if (status === 401) {
      showToast('Authentication required. Please log in.', 'error')
    } else if (status === 403) {
      showToast('Access denied. You do not have permission.', 'error')
    } else if (status === 404) {
      showToast(detail || 'Resource not found.', 'warning')
    } else if (status === 409) {
      showToast(detail || 'Conflict. Resource may already exist.', 'warning')
    } else if (status === 422) {
      showToast(detail || 'Validation error. Please check your input.', 'warning')
    } else if (status === 429) {
      showToast('Too many requests. Please slow down.', 'warning')
    } else if (status >= 500) {
      showToast('Server error. Please try again later.', 'error')
    }

    return Promise.reject({
      message: detail || error.message || 'An unexpected error occurred',
      code: code || 'UNKNOWN_ERROR',
      status_code: status || 0,
    })
  }
)

export type ApiErrorResponse = {
  message: string
  code: string
  status_code: number
}
