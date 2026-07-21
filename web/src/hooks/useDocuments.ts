import { useState, useCallback, useEffect } from 'react'
import { listDocuments, uploadDocument, deleteDocument } from '@/api/documents'
import type { DocumentResponse } from '@/types/api'

interface UseDocumentsReturn {
  documents: DocumentResponse[]
  isLoading: boolean
  isUploading: boolean
  uploadProgress: number
  uploadingFile: string | null
  error: string | null
  fetchDocuments: () => Promise<void>
  upload: (file: File) => Promise<void>
  remove: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadingFile, setUploadingFile] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await listDocuments()
      setDocuments(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch documents'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const upload = useCallback(
    async (file: File) => {
      setIsUploading(true)
      setUploadProgress(0)
      setUploadingFile(file.name)
      setError(null)
      try {
        await uploadDocument(file, (percent) => {
          setUploadProgress(percent)
        })
        await fetchDocuments()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to upload document'
        setError(message)
      } finally {
        setIsUploading(false)
        setUploadProgress(0)
        setUploadingFile(null)
      }
    },
    [fetchDocuments]
  )

  const remove = useCallback(
    async (id: string) => {
      setError(null)
      try {
        await deleteDocument(id)
        await fetchDocuments()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete document'
        setError(message)
      }
    },
    [fetchDocuments]
  )

  const refresh = useCallback(async () => {
    await fetchDocuments()
  }, [fetchDocuments])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  return {
    documents,
    isLoading,
    isUploading,
    uploadProgress,
    uploadingFile,
    error,
    fetchDocuments,
    upload,
    remove,
    refresh,
  }
}
