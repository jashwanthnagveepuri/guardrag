"""Pydantic v2 models for all API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from guardrag.core.constants import (
    ChunkingStrategy,
    DocumentStatus,
    GuardrailAction,
    GuardrailLayer,
    MessageRole,
)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Metadata for paginated responses."""

    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total: int = Field(..., ge=0, description="Total items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether more pages exist")
    has_prev: bool = Field(..., description="Whether previous pages exist")


class PaginatedResponse(BaseModel):
    """Base class for paginated responses."""

    meta: PaginationMeta


# ---------------------------------------------------------------------------
# Document Models
# ---------------------------------------------------------------------------

class DocumentMetadata(BaseModel):
    """Parsed document metadata stored as JSON."""

    model_config = ConfigDict(extra="allow")

    title: str | None = Field(default=None, description="Extracted document title")
    total_pages: int | None = Field(default=None, description="Total page count")
    author: str | None = Field(default=None)
    creation_date: str | None = Field(default=None)
    word_count: int | None = Field(default=None)
    section_count: int | None = Field(default=None)
    parser_version: str = Field(default="1.0.0")
    parse_duration_ms: int | None = Field(default=None)


class DocumentUploadResponse(BaseModel):
    """Response after a document upload."""

    id: UUID = Field(..., description="Document UUID")
    filename: str = Field(..., description="Stored filename")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    chunk_count: int = Field(default=0, ge=0)
    is_duplicate: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentResponse(BaseModel):
    """Full document representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Document UUID")
    filename: str = Field(..., description="Stored filename")
    original_name: str = Field(..., description="User-provided filename")
    content_type: str = Field(..., description="MIME type")
    file_type: str = Field(..., description="Normalized file type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    content_hash: str = Field(..., description="SHA-256 content hash")
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.RECURSIVE)
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=50)
    chunk_count: int = Field(default=0, ge=0)
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    error_message: str | None = Field(default=None)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    processed_at: datetime | None = Field(default=None)


class DocumentListResponse(PaginatedResponse):
    """Paginated list of documents."""

    items: list[DocumentResponse] = Field(default_factory=list)


class DocumentFilterParams(BaseModel):
    """Query parameters for filtering document lists."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: DocumentStatus | None = Field(default=None)
    file_type: str | None = Field(default=None)
    search: str | None = Field(default=None, description="Search in filename")
    sort_by: str = Field(default="created_at")
    sort_order: Literal["asc", "desc"] = Field(default="desc")


# ---------------------------------------------------------------------------
# Chunk Models
# ---------------------------------------------------------------------------

class SourceRange(BaseModel):
    """Character range within the original document."""

    start_char: int = Field(..., ge=0)
    end_char: int = Field(..., ge=0)


class ChunkResponse(BaseModel):
    """Single document chunk for inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Chunk UUID")
    document_id: UUID = Field(...)
    content: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., ge=0, description="0-based index within document")
    token_count: int = Field(..., ge=0)
    page_number: int | None = Field(default=None)
    section_heading: str | None = Field(default=None)
    source_range: SourceRange | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(...)


class ChunkListResponse(PaginatedResponse):
    """Paginated list of chunks for a document."""

    items: list[ChunkResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Non-streaming chat query request."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User question to answer from documents",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation UUID; null creates new conversation",
    )
    document_ids: list[UUID] | None = Field(
        default=None,
        description="Scope search to specific documents; null = search all",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve",
    )
    stream: bool = Field(default=False, description="Enable streaming response")


class SourceCitation(BaseModel):
    """A cited source in the LLM answer."""

    source_number: int = Field(..., ge=1, description="Source number as cited [Source N]")
    chunk_id: UUID = Field(...)
    document_id: UUID = Field(...)
    document_title: str = Field(...)
    document_filename: str = Field(...)
    page_number: int | None = Field(default=None)
    chunk_text: str = Field(..., description="Full chunk text for transparency")
    similarity_score: float = Field(..., ge=0, le=1, description="Initial vector similarity")
    rerank_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Cross-encoder re-rank score",
    )


class GuardrailDecision(BaseModel):
    """Guardrail decision for a single layer."""

    triggered: bool = Field(default=False)
    layer: GuardrailLayer | None = Field(default=None)
    action: GuardrailAction = Field(default=GuardrailAction.PASS)
    reason: str | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0, le=1)
    detail: str | None = Field(default=None)
    pii_redacted: int | None = Field(default=None)
    toxic_filtered: int | None = Field(default=None)
    entailment_ratio: float | None = Field(default=None, ge=0, le=1)
    citation_accuracy: float | None = Field(default=None, ge=0, le=1)


class ChatResponse(BaseModel):
    """Successful chat response with full provenance."""

    message_id: UUID = Field(...)
    conversation_id: UUID = Field(...)
    answer: str = Field(..., description="LLM-generated answer with inline citations")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence score")
    hallucination_risk: float = Field(..., ge=0, le=1, description="Hallucination risk score")
    sources: list[SourceCitation] = Field(default_factory=list)
    guardrail_decisions: dict[str, GuardrailDecision] = Field(
        default_factory=dict,
        description="Decisions per layer: input, retrieval, output",
    )
    latency_ms: int = Field(..., ge=0, description="End-to-end latency")
    tokens_used: int | None = Field(default=None)


class GuardrailChatResponse(BaseModel):
    """Response when a guardrail blocks the query."""

    guardrail_triggered: bool = Field(default=True)
    layer: GuardrailLayer = Field(...)
    reason: str = Field(...)
    confidence: float = Field(..., ge=0, le=1)
    detail: str = Field(..., description="Human-readable explanation")
    suggestion: str = Field(..., description="Guidance for the user")
    incident_logged: bool = Field(default=True)
    latency_ms: int = Field(..., ge=0)


# ---------------------------------------------------------------------------
# Streaming Chat Models
# ---------------------------------------------------------------------------

class StreamingChatEvent(BaseModel):
    """Base for all SSE events in streaming chat."""

    event_type: Literal["start", "chunk", "sources", "guardrail", "done", "error"] = Field(
        ...
    )


class StartEvent(StreamingChatEvent):
    """Stream start event."""

    event_type: Literal["start"] = "start"
    message: str = "Stream started"


class ChunkEvent(StreamingChatEvent):
    """Individual token in the streaming answer."""

    event_type: Literal["chunk"] = "chunk"
    token: str = Field(..., description="Token text (may be partial word)")


class SourcesEvent(StreamingChatEvent):
    """Sources retrieved during streaming."""

    event_type: Literal["sources"] = "sources"
    sources: list[SourceCitation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class GuardrailEvent(StreamingChatEvent):
    """Guardrail result event."""

    event_type: Literal["guardrail"] = "guardrail"
    layer: str = Field(...)
    action: str = Field(...)
    reason: str | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0, le=1)


class DoneEvent(StreamingChatEvent):
    """Final event when streaming completes."""

    event_type: Literal["done"] = "done"
    message_id: UUID = Field(...)
    confidence: float = Field(...)
    hallucination_risk: float = Field(...)
    sources: list[SourceCitation] = Field(default_factory=list)
    latency_ms: int = Field(...)


class ErrorEvent(StreamingChatEvent):
    """Error event during streaming."""

    event_type: Literal["error"] = "error"
    code: str = Field(..., description="Error code: LLM_UNAVAILABLE, TIMEOUT, UNKNOWN")
    detail: str = Field(...)


# ---------------------------------------------------------------------------
# Message & Conversation Models
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Single message in a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(...)
    conversation_id: UUID = Field(...)
    role: MessageRole = Field(...)
    content: str = Field(...)
    guardrail_result: GuardrailDecision | None = Field(default=None)
    sources: list[SourceCitation] = Field(default_factory=list)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    hallucination_risk: float | None = Field(default=None, ge=0, le=1)
    latency_ms: int | None = Field(default=None)
    created_at: datetime = Field(...)


class MessageListResponse(PaginatedResponse):
    """Paginated messages for a conversation."""

    items: list[MessageResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    """Conversation summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(...)
    title: str | None = Field(default=None)
    document_ids: list[str] = Field(default_factory=list)
    message_count: int = Field(default=0)
    status: str = Field(default="active")
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class ConversationListResponse(PaginatedResponse):
    """Paginated conversation list."""

    items: list[ConversationResponse] = Field(default_factory=list)


class ConversationFilterParams(BaseModel):
    """Query parameters for listing conversations."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, description="Search in conversation title")


class MessageFilterParams(BaseModel):
    """Query parameters for listing messages."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ---------------------------------------------------------------------------
# Guardrail Models
# ---------------------------------------------------------------------------

class GuardrailResult(BaseModel):
    """Composite guardrail result across all layers."""

    input: GuardrailDecision = Field(
        default_factory=lambda: GuardrailDecision(triggered=False)
    )
    retrieval: GuardrailDecision = Field(
        default_factory=lambda: GuardrailDecision(triggered=False)
    )
    output: GuardrailDecision = Field(
        default_factory=lambda: GuardrailDecision(triggered=False)
    )
    composite_score: float = Field(default=0.0, ge=0, le=1)
    blocked: bool = Field(default=False)


class GuardrailScanRequest(BaseModel):
    """Request to scan arbitrary text for prompt injection."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text to analyze",
    )
    paranoid_mode: bool = Field(
        default=False,
        description="If True, always run LLM classifier even if heuristic is clean",
    )


class HeuristicDetail(BaseModel):
    """Detailed results from heuristic scanner."""

    score: float = Field(..., ge=0, le=1)
    matched_patterns: list[str] = Field(default_factory=list)
    delimiter_detected: bool = Field(default=False)
    length_anomaly: bool = Field(default=False)
    special_char_ratio: float = Field(default=0.0)


class LLMClassifierDetail(BaseModel):
    """Detailed results from LLM classifier."""

    is_malicious: bool = Field(...)
    confidence: float = Field(..., ge=0, le=1)
    category: str | None = Field(default=None)
    reasoning: str | None = Field(default=None)


class GuardrailScanResponse(BaseModel):
    """Response from guardrail scan endpoint."""

    scanned: bool = Field(default=True)
    action: GuardrailAction = Field(...)
    composite_score: float = Field(..., ge=0, le=1)
    threshold: float = Field(default=0.75, description="Blocking threshold applied")
    heuristic: HeuristicDetail | None = Field(default=None)
    llm_classifier: LLMClassifierDetail | None = Field(default=None)
    latency_ms: int = Field(..., ge=0)


class GuardrailLayerStats(BaseModel):
    """Statistics for a single guardrail layer."""

    total_scanned: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    blocked: int = Field(..., ge=0)
    warned: int = Field(..., ge=0)
    block_rate_percent: float = Field(..., ge=0, le=100)
    avg_latency_ms: float = Field(..., ge=0)
    top_reasons: list[dict[str, Any]] = Field(default_factory=list)


class GuardrailStats(BaseModel):
    """Aggregated guardrail statistics."""

    period: str = Field(..., description="Aggregation period: 1h, 24h, 7d, 30d")
    input_layer: GuardrailLayerStats = Field(...)
    retrieval_layer: GuardrailLayerStats = Field(...)
    output_layer: GuardrailLayerStats = Field(...)
    overall_block_rate_percent: float = Field(..., ge=0, le=100)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# System / Health Models
# ---------------------------------------------------------------------------

class ComponentHealth(BaseModel):
    """Health status of a single dependency."""

    name: str = Field(..., description="Component name")
    status: Literal["healthy", "unhealthy", "unknown"] = Field(...)
    latency_ms: int | None = Field(default=None)
    detail: str | None = Field(default=None)


class HealthResponse(BaseModel):
    """System health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(...)
    version: str = Field(default="1.0.0")
    components: dict[str, ComponentHealth] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatsCounters(BaseModel):
    """Aggregate counters for system stats."""

    total_documents: int = Field(..., ge=0)
    documents_by_status: dict[str, int] = Field(default_factory=dict)
    total_chunks: int = Field(..., ge=0)
    total_conversations: int = Field(..., ge=0)
    total_messages: int = Field(..., ge=0)
    total_queries: int = Field(..., ge=0)
    total_guardrail_blocks: int = Field(..., ge=0)
    guardrail_block_rate_percent: float = Field(..., ge=0, le=100)
    avg_query_latency_ms: float | None = Field(default=None)
    total_tokens_consumed: int | None = Field(default=None)


class StatsResponse(BaseModel):
    """System-wide statistics."""

    counters: StatsCounters = Field(...)
    guardrail: GuardrailStats | None = Field(default=None)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = Field(
        default="about:blank",
        description="A URI reference that identifies the problem type",
    )
    title: str = Field(..., description="Short human-readable summary")
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence",
    )
    instance: str | None = Field(
        default=None,
        description="URI reference that identifies the specific occurrence",
    )
    status: int | None = Field(
        default=None,
        description="HTTP status code",
    )
    trace_id: str | None = Field(default=None)
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="Validation errors [{loc, msg, type}]",
    )
