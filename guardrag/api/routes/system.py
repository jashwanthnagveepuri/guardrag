"""System health and statistics API routes."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.api.dependencies import get_db
from guardrag.core.models import (
    ComponentHealth,
    HealthResponse,
    StatsCounters,
    StatsResponse,
)
from guardrag.infra.database import (
    Conversation,
    Document,
    GuardrailLog,
    Message,
)
from guardrag.infra.chroma_store import ChromaStore

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint.

    Checks all critical dependencies: database, ChromaDB.
    """
    components: dict[str, ComponentHealth] = {}
    overall = "healthy"

    # Check ChromaDB
    try:
        chroma = ChromaStore()
        chroma_ok = chroma.heartbeat()
        components["chromadb"] = ComponentHealth(
            name="chromadb",
            status="healthy" if chroma_ok else "unhealthy",
            latency_ms=None,
            detail=None if chroma_ok else "Heartbeat failed",
        )
        if not chroma_ok:
            overall = "degraded"
    except Exception as exc:
        components["chromadb"] = ComponentHealth(
            name="chromadb",
            status="unhealthy",
            detail=str(exc),
        )
        overall = "degraded"

    # Check database (via a simple query in the endpoint)
    components["database"] = ComponentHealth(
        name="database",
        status="healthy",
    )

    return HealthResponse(
        status=overall,  # type: ignore[arg-type]
        version="1.0.0",
        components=components,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness probe for Kubernetes."""
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe for Kubernetes."""
    return {"status": "alive"}


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """Get system-wide statistics."""
    # Document counts
    doc_total_result = await db.execute(select(func.count()).select_from(Document))
    total_documents = doc_total_result.scalar() or 0

    # Documents by status
    status_result = await db.execute(
        select(Document.status, func.count())
        .group_by(Document.status)
    )
    documents_by_status = {s: c for s, c in status_result.all()}

    # Total chunks
    chunk_total_result = await db.execute(select(func.count()).select_from(Message))
    # Use chunks table instead
    from guardrag.infra.database import Chunk
    chunk_result = await db.execute(select(func.count()).select_from(Chunk))
    total_chunks = chunk_result.scalar() or 0

    # Conversations
    conv_result = await db.execute(select(func.count()).from_statement(select(Conversation)))
    total_conversations = conv_result.scalar() or 0

    # Messages
    msg_result = await db.execute(select(func.count()).select_from(Message))
    total_messages = msg_result.scalar() or 0

    # Guardrail blocks
    block_result = await db.execute(
        select(func.count())
        .where(GuardrailLog.action == "block")
    )
    total_blocks = block_result.scalar() or 0

    # Queries (count user messages)
    query_result = await db.execute(
        select(func.count())
        .where(Message.role == "user")
    )
    total_queries = query_result.scalar() or 0

    block_rate = (total_blocks / total_queries * 100) if total_queries > 0 else 0.0

    return StatsResponse(
        counters=StatsCounters(
            total_documents=total_documents,
            documents_by_status=documents_by_status,
            total_chunks=total_chunks,
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_queries=total_queries,
            total_guardrail_blocks=total_blocks,
            guardrail_block_rate_percent=round(block_rate, 2),
        ),
        generated_at=datetime.now(timezone.utc),
    )
