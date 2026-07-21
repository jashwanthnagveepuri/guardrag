"""Chat API routes."""

from __future__ import annotations

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.api.dependencies import get_chat_service, get_db
from guardrag.core.models import (
    ChatRequest,
    ChatResponse,
    ConversationFilterParams,
    ConversationListResponse,
    DoneEvent,
    ErrorEvent,
    ErrorResponse,
    GuardrailChatResponse,
    MessageFilterParams,
    MessageListResponse,
    StreamingChatEvent,
)
from guardrag.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        403: {"model": GuardrailChatResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse | GuardrailChatResponse:
    """Ask a question and get an answer from documents.

    The question flows through input guardrail -> retrieval -> LLM generation -> output guardrail.
    """
    result = await chat_service.process_question(chat_request, db)
    if isinstance(result, GuardrailChatResponse):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.model_dump(),
        )
    return result


@router.get(
    "/stream",
    response_model=None,
)
async def chat_stream(
    request: Request,
    question: str = Query(..., min_length=1, max_length=4000),
    conversation_id: uuid.UUID | None = None,
    document_ids: list[uuid.UUID] | None = None,
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> AsyncGenerator[str, None]:
    """Stream a chat response as Server-Sent Events.

    Yields SSE events: start, chunk, sources, guardrail, done, error.
    """
    from fastapi.responses import StreamingResponse
    import json

    chat_request = ChatRequest(
        question=question,
        conversation_id=conversation_id,
        document_ids=document_ids,
        top_k=top_k,
        stream=True,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in chat_service.process_question_stream(chat_request, db):
            data = event.model_dump_json()
            yield f"event: {event.event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# Conversation routes

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """List conversations."""
    from guardrag.infra.database import Conversation
    from guardrag.core.models import ConversationResponse, PaginationMeta
    from sqlalchemy import func, select

    query = select(Conversation).where(Conversation.deleted_at.is_(None))
    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = query.order_by(Conversation.updated_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    conversations = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return ConversationListResponse(
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
        items=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                document_ids=c.document_ids,
                message_count=c.message_count,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ],
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """Get messages for a conversation."""
    from guardrag.infra.database import Conversation, Message
    from guardrag.core.models import MessageResponse, PaginationMeta, SourceCitation
    from guardrag.core.constants import MessageRole, GuardrailDecision
    from sqlalchemy import func, select

    # Verify conversation exists
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    count_query = select(func.count()).where(Message.conversation_id == conversation_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return MessageListResponse(
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
        items=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=MessageRole(m.role),
                content=m.content,
                guardrail_result=GuardrailDecision(**m.guardrail_result) if m.guardrail_result else None,
                sources=[SourceCitation(**s) for s in m.sources] if m.sources else [],
                confidence_score=m.confidence_score,
                hallucination_risk=m.hallucination_risk,
                latency_ms=m.latency_ms,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a conversation."""
    from guardrag.infra.database import Conversation
    from sqlalchemy import select
    from datetime import datetime, timezone

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    conv.deleted_at = datetime.now(timezone.utc)
    await db.commit()
