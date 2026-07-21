import { useState, useCallback } from 'react'
import { FileText, Loader2, Eye, X, ChevronLeft, ChevronRight } from 'lucide-react'
import FileUpload from '@/components/FileUpload'
import { useDocuments } from '@/hooks/useDocuments'
import { getDocumentChunks } from '@/api/documents'
import type { DocumentChunk, DocumentResponse } from '@/types/api'

export default function DocumentsPage() {
  const {
    documents,
    isLoading,
    isUploading,
    uploadProgress,
    uploadingFile,
    upload,
    remove,
  } = useDocuments()

  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null)
  const [chunks, setChunks] = useState<DocumentChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [chunksPage, setChunksPage] = useState(0)
  const [showChunksModal, setShowChunksModal] = useState(false)
  const CHUNKS_PER_PAGE = 10

  const handleViewChunks = useCallback(async (doc: DocumentResponse) => {
    setSelectedDoc(doc)
    setChunksPage(0)
    setChunksLoading(true)
    setShowChunksModal(true)
    try {
      const data = await getDocumentChunks(doc.id)
      setChunks(data)
    } catch {
      setChunks([])
    } finally {
      setChunksLoading(false)
    }
  }, [])

  const closeChunksModal = useCallback(() => {
    setShowChunksModal(false)
    setSelectedDoc(null)
    setChunks([])
  }, [])

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const statusBadge = (status: DocumentResponse['status']) => {
    const styles = {
      pending: 'bg-warm-100 text-warm-600',
      processing: 'bg-primary-50 text-primary-600 animate-pulse',
      completed: 'bg-success-50 text-success-600',
      failed: 'bg-danger-50 text-danger-600',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${styles[status]}`}>
        {status}
      </span>
    )
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('pdf')) return 'bg-danger-50 text-danger-600'
    if (contentType.includes('word') || contentType.includes('docx')) return 'bg-primary-50 text-primary-600'
    if (contentType.includes('markdown') || contentType.includes('md')) return 'bg-secondary-50 text-secondary-600'
    return 'bg-warm-100 text-warm-600'
  }

  const paginatedChunks = chunks.slice(
    chunksPage * CHUNKS_PER_PAGE,
    (chunksPage + 1) * CHUNKS_PER_PAGE
  )
  const totalChunkPages = Math.ceil(chunks.length / CHUNKS_PER_PAGE)

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Documents</h1>
        <p className="text-sm text-warm-500 mt-1">
          Upload and manage your documents for secure Q&A
        </p>
      </div>

      {/* Upload Section */}
      <FileUpload
        onUpload={upload}
        onDelete={remove}
        documents={documents}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        uploadingFile={uploadingFile}
      />

      {/* Document Table */}
      {documents.length > 0 && (
        <div className="bg-white border border-warm-200 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-warm-100">
            <h2 className="text-sm font-semibold text-secondary-800">
              All Documents
            </h2>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-warm-400 animate-spin" />
              <span className="ml-2 text-sm text-warm-500">Loading documents...</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-warm-50 text-left">
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Chunks
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-warm-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-warm-100">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-warm-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${getFileIcon(doc.content_type)}`}>
                            <FileText className="w-4 h-4" />
                          </div>
                          <span className="text-sm font-medium text-secondary-800 truncate max-w-[200px]">
                            {doc.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs text-warm-500 font-mono">
                          {doc.content_type.split('/')[1]?.toUpperCase() || doc.content_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-warm-600">
                        {formatBytes(doc.size_bytes)}
                      </td>
                      <td className="px-6 py-4 text-sm text-warm-600">
                        {doc.chunk_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        {statusBadge(doc.status)}
                      </td>
                      <td className="px-6 py-4 text-sm text-warm-500">
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleViewChunks(doc)}
                            className="p-1.5 rounded-lg text-warm-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                            title="View chunks"
                            aria-label={`View chunks for ${doc.filename}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Chunks Modal */}
      {showChunksModal && selectedDoc && (
        <div className="fixed inset-0 bg-secondary-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-warm-200">
              <div>
                <h3 className="text-lg font-semibold text-secondary-900">
                  Document Chunks
                </h3>
                <p className="text-xs text-warm-500 mt-0.5">
                  {selectedDoc.filename} · {chunks.length} chunks total
                </p>
              </div>
              <button
                onClick={closeChunksModal}
                className="p-1.5 rounded-lg text-warm-400 hover:text-secondary-700 hover:bg-warm-100 transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-auto px-6 py-4">
              {chunksLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-5 h-5 text-warm-400 animate-spin" />
                  <span className="ml-2 text-sm text-warm-500">Loading chunks...</span>
                </div>
              ) : paginatedChunks.length === 0 ? (
                <p className="text-center text-sm text-warm-500 py-12">
                  No chunks found for this document.
                </p>
              ) : (
                <div className="space-y-3">
                  {paginatedChunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="bg-warm-50 border border-warm-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-warm-400">
                          Chunk {chunk.chunk_index}
                        </span>
                        <span className="text-[10px] text-warm-400">
                          ID: {chunk.id.slice(0, 12)}...
                        </span>
                      </div>
                      <p className="text-sm text-secondary-700 leading-relaxed whitespace-pre-wrap">
                        {chunk.content}
                      </p>
                      {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {Object.entries(chunk.metadata).map(([key, value]) => (
                            <span
                              key={key}
                              className="px-2 py-0.5 bg-white rounded text-[10px] text-warm-500 border border-warm-200"
                            >
                              {key}: {String(value).slice(0, 50)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer with Pagination */}
            {chunks.length > CHUNKS_PER_PAGE && (
              <div className="flex items-center justify-between px-6 py-3 border-t border-warm-200">
                <span className="text-xs text-warm-500">
                  Page {chunksPage + 1} of {totalChunkPages}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setChunksPage((p) => Math.max(0, p - 1))}
                    disabled={chunksPage === 0}
                    className="p-1.5 rounded-lg text-warm-400 hover:text-secondary-700 hover:bg-warm-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setChunksPage((p) => Math.min(totalChunkPages - 1, p + 1))}
                    disabled={chunksPage >= totalChunkPages - 1}
                    className="p-1.5 rounded-lg text-warm-400 hover:text-secondary-700 hover:bg-warm-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    aria-label="Next page"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
