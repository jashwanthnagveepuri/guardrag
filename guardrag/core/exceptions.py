"""Custom exceptions for GuardRAG."""

from __future__ import annotations


class GuardRAGError(Exception):
    """Base exception for all GuardRAG errors."""

    def __init__(self, message: str, *, status_code: int = 500, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class DocumentParsingError(GuardRAGError):
    """Raised when a document cannot be parsed."""

    def __init__(self, message: str, filename: str | None = None) -> None:
        super().__init__(message, status_code=422, detail=filename)
        self.filename = filename


class ChunkingError(GuardRAGError):
    """Raised when document chunking fails."""

    def __init__(self, message: str, document_id: str | None = None) -> None:
        super().__init__(message, status_code=500)
        self.document_id = document_id


class EmbeddingError(GuardRAGError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class GuardrailBlockedError(GuardRAGError):
    """Raised when a guardrail blocks a request."""

    def __init__(self, message: str, layer: str, reason: str, confidence: float) -> None:
        super().__init__(message, status_code=403)
        self.layer = layer
        self.reason = reason
        self.confidence = confidence


class GuardrailWarningError(GuardRAGError):
    """Raised when a guardrail issues a warning (non-blocking)."""

    def __init__(self, message: str, layer: str, reason: str) -> None:
        super().__init__(message, status_code=200)
        self.layer = layer
        self.reason = reason


class VectorDBError(GuardRAGError):
    """Raised when a vector database operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class RetrievalError(GuardRAGError):
    """Raised when document retrieval fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)
