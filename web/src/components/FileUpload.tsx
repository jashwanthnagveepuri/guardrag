import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, X, Loader2, File, Trash2 } from 'lucide-react'
import type { DocumentResponse } from '@/types/api'

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>
  onDelete: (id: string) => Promise<void>
  documents: DocumentResponse[]
  isUploading: boolean
  uploadProgress: number
  uploadingFile: string | null
}

const ALLOWED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx']

function getFileIcon(contentType: string) {
  if (contentType.includes('pdf')) return 'bg-danger-50 text-danger-600'
  if (contentType.includes('word') || contentType.includes('docx')) return 'bg-primary-50 text-primary-600'
  if (contentType.includes('markdown') || contentType.includes('md')) return 'bg-secondary-50 text-secondary-600'
  return 'bg-warm-100 text-warm-600'
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function FileUpload({
  onUpload,
  onDelete,
  documents,
  isUploading,
  uploadProgress,
  uploadingFile,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)
      const files = e.dataTransfer.files
      for (const file of files) {
        if (ALLOWED_TYPES.includes(file.type)) {
          await onUpload(file)
          break
        }
      }
    },
    [onUpload]
  )

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        await onUpload(file)
        e.target.value = ''
      }
    },
    [onUpload]
  )

  const handleDelete = useCallback(
    async (id: string) => {
      setDeletingId(id)
      try {
        await onDelete(id)
      } finally {
        setDeletingId(null)
      }
    },
    [onDelete]
  )

  const statusBadge = (status: DocumentResponse['status']) => {
    const styles = {
      pending: 'bg-warm-100 text-warm-600',
      processing: 'bg-primary-50 text-primary-600 animate-pulse',
      completed: 'bg-success-50 text-success-600',
      failed: 'bg-danger-50 text-danger-600',
    }
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${styles[status]}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragOver
            ? 'border-primary-400 bg-primary-50'
            : 'border-warm-300 bg-white hover:border-warm-400 hover:bg-warm-50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragOver ? 'text-primary-500' : 'text-warm-400'}`} />
        <p className="text-sm font-medium text-secondary-700 mb-1">
          Drop your document here, or click to browse
        </p>
        <p className="text-xs text-warm-400">
          Supports: PDF, TXT, MD, DOCX (max 50MB)
        </p>
      </div>

      {/* Upload Progress */}
      {isUploading && uploadingFile && (
        <div className="bg-white border border-warm-200 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
            <span className="text-sm font-medium text-secondary-700 truncate">
              Uploading {uploadingFile}...
            </span>
            <span className="text-sm text-warm-500 ml-auto">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-warm-100 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Document List */}
      {documents.length > 0 && (
        <div className="bg-white border border-warm-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-warm-100">
            <h3 className="text-sm font-semibold text-secondary-800">
              Uploaded Documents ({documents.length})
            </h3>
          </div>
          <div className="divide-y divide-warm-100 max-h-96 overflow-auto">
            {documents.map((doc) => (
              <div key={doc.id} className="px-4 py-3 flex items-center gap-3 hover:bg-warm-50 transition-colors">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${getFileIcon(doc.content_type)}`}>
                  <FileText className="w-4.5 h-4.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-secondary-800 truncate">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {statusBadge(doc.status)}
                    <span className="text-xs text-warm-400">
                      {formatBytes(doc.size_bytes)} · {doc.chunk_count} chunks
                    </span>
                  </div>
                </div>
                <span className="text-xs text-warm-400 shrink-0 hidden sm:block">
                  {formatDate(doc.created_at)}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(doc.id)
                  }}
                  disabled={deletingId === doc.id}
                  className="p-1.5 rounded-lg text-warm-400 hover:text-danger-500 hover:bg-danger-50 transition-colors shrink-0"
                  aria-label={`Delete ${doc.filename}`}
                >
                  {deletingId === doc.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {documents.length === 0 && !isUploading && (
        <div className="text-center py-8">
          <File className="w-12 h-12 text-warm-300 mx-auto mb-3" />
          <p className="text-sm text-warm-500">No documents uploaded yet</p>
          <p className="text-xs text-warm-400 mt-1">Upload a document to get started</p>
        </div>
      )}
    </div>
  )
}
