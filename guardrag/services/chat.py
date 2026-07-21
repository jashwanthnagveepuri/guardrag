"""Chat orchestration service for GuardRAG.

Orchestrates the full Q&A pipeline:
1. Input guardrail scan
2. Document retrieval
3. Retrieval guard filtering
4. LLM answer generation
5. Output guardrail verification
6. Message persistence
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.core.config import get_settings
from guardrag.core.constants import DocumentStatus, GuardrailAction, MessageRole
from guardrag.core.exceptions import GuardrailBlockedError
from guardrag.core.models import (
    ChatRequest,
    ChatResponse,
    ChunkEvent,
    DoneEvent,
    ErrorEvent,
    GuardrailChatResponse,
    GuardrailDecision,
    GuardrailEvent,
    MessageResponse,
    SourceCitation,
    SourcesEvent,
    StartEvent,
    StreamingChatEvent,
)
from guardrag.infra.database import Conversation, Document, Message
from guardrag.infra.llm import LLMService
from guardrag.services.guardrails.input_guardrail import InputGuardrail
from guardrag.services.guardrails.output_guardrail import OutputGuardrail
from guardrag.services.guardrails.retrieval_guard import RetrievalGuard
from guardrag.services.retriever import RetrieverService

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates the chat Q&A pipeline with guardrails."""

    def __init__(
        self,
        input_guardrail: InputGuardrail | None = None,
        output_guardrail: OutputGuardrail | None = None,
        retrieval_guard: RetrievalGuard | None = None,
        retriever: RetrieverService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._input_guard = input_guardrail or InputGuardrail()
        self._output_guard = output_guardrail or OutputGuardrail()
        self._retrieval_guard = retrieval_guard or RetrievalGuard()
        self._retriever = retriever or RetrieverService()
        self._llm = llm_service or LLMService()

    async def process_question(
        self,
        chat_request: ChatRequest,
        db_session: AsyncSession,
    ) -> ChatResponse | GuardrailChatResponse:
        """Process a chat question through the full pipeline.

        Args:
            chat_request: The chat request.
            db_session: Database session.

        Returns:
            ChatResponse or GuardrailChatResponse if blocked.
        """
        start_time = time.monotonic()
        guardrail_decisions: dict[str, GuardrailDecision] = {}

        # 1. Input guardrail scan
        input_result = await self._input_guard.scan(chat_request.question)
        guardrail_decisions["input"] = input_result

        if input_result.action == GuardrailAction.BLOCK:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.warning(
                "Input guardrail blocked query: %s", chat_request.question[:100]
            )
            # Log to database
            await self._log_guardrail(input_result, chat_request.question, db_session)
            return GuardrailChatResponse(
                layer=input_result.layer,
                reason=input_result.reason or "PROMPT_INJECTION",
                confidence=input_result.confidence or 0.0,
                detail=input_result.detail or "Input blocked by guardrail",
                suggestion="Please rephrase your question without instructions to ignore guidelines.",
                latency_ms=latency_ms,
            )

        # 2. Get or create conversation
        conversation = await self._get_or_create_conversation(
            chat_request.conversation_id,
            chat_request.question,
            chat_request.document_ids,
            db_session,
        )

        # 3. Get document IDs as strings for retrieval
        doc_id_strs = None
        if chat_request.document_ids:
            doc_id_strs = [str(d) for d in chat_request.document_ids]
        elif conversation.document_ids:
            doc_id_strs = conversation.document_ids

        # 4. Retrieve relevant chunks
        chunks = await self._retriever.retrieve(
            query=chat_request.question,
            document_ids=doc_id_strs,
            top_k=chat_request.top_k,
        )

        # 5. Retrieval guard
        filtered_chunks, retrieval_decision = self._retrieval_guard.filter_chunks(chunks)
        guardrail_decisions["retrieval"] = retrieval_decision

        if not filtered_chunks:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return ChatResponse(
                message_id=uuid.uuid4(),
                conversation_id=conversation.id,
                answer="I cannot find relevant information in the available documents to answer your question.",
                confidence=0.0,
                hallucination_risk=0.0,
                sources=[],
                guardrail_decisions=guardrail_decisions,
                latency_ms=latency_ms,
                tokens_used=0,
            )

        # 6. Get conversation history
        history = await self._get_conversation_history(conversation.id, db_session)

        # 7. Generate answer
        answer = await self._llm.generate_answer(
            question=chat_request.question,
            context_chunks=filtered_chunks,
            conversation_history=history,
        )

        # 8. Output guardrail
        output_decision, confidence, hallucination_risk = await self._output_guard.check(
            question=chat_request.question,
            answer=answer,
            source_chunks=filtered_chunks,
        )
        guardrail_decisions["output"] = output_decision

        if output_decision.action == GuardrailAction.BLOCK:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            answer = (
                "I apologize, but I am not confident enough to answer this question "
                "based on the available information. Please try rephrasing your question "
                "or uploading more relevant documents."
            )

        # Build source citations
        sources = self._build_sources(filtered_chunks)

        # 9. Save messages
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER.value,
            content=chat_request.question,
            guardrail_result={"input": input_result.model_dump()},
        )
        db_session.add(user_message)
        await db_session.flush()

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=answer,
            guardrail_result={
                "input": input_result.model_dump(),
                "retrieval": retrieval_decision.model_dump(),
                "output": output_decision.model_dump(),
            },
            sources=[s.model_dump(mode="json") for s in sources],
            confidence_score=confidence,
            hallucination_risk=hallucination_risk,
        )
        db_session.add(assistant_message)

        # Update conversation
        conversation.message_count += 2
        await db_session.commit()
        await db_session.refresh(assistant_message)

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Update latency
        assistant_message.latency_ms = latency_ms
        await db_session.commit()

        return ChatResponse(
            message_id=assistant_message.id,
            conversation_id=conversation.id,
            answer=answer,
            confidence=confidence,
            hallucination_risk=hallucination_risk,
            sources=sources,
            guardrail_decisions=guardrail_decisions,
            latency_ms=latency_ms,
            tokens_used=None,
        )

    async def process_question_stream(
        self,
        chat_request: ChatRequest,
        db_session: AsyncSession,
    ) -> AsyncGenerator[StreamingChatEvent, None]:
        """Process a chat question with streaming response.

        Yields streaming events: start, chunk, sources, guardrail, done, error.
        """
        start_time = time.monotonic()

        try:
            # Start event
            yield StartEvent()

            # 1. Input guardrail
            input_result = await self._input_guard.scan(chat_request.question)

            if input_result.action == GuardrailAction.BLOCK:
                yield GuardrailEvent(
                    layer=input_result.layer.value,
                    action=input_result.action.value,
                    reason=input_result.reason,
                    confidence=input_result.confidence,
                )
                yield DoneEvent(
                    message_id=uuid.uuid4(),
                    confidence=0.0,
                    hallucination_risk=1.0,
                    sources=[],
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                )
                return

            # 2. Get conversation
            conversation = await self._get_or_create_conversation(
                chat_request.conversation_id,
                chat_request.question,
                chat_request.document_ids,
                db_session,
            )

            # 3. Retrieve chunks
            doc_id_strs = None
            if chat_request.document_ids:
                doc_id_strs = [str(d) for d in chat_request.document_ids]
            elif conversation.document_ids:
                doc_id_strs = conversation.document_ids

            chunks = await self._retriever.retrieve(
                query=chat_request.question,
                document_ids=doc_id_strs,
                top_k=chat_request.top_k,
            )

            # 4. Retrieval guard
            filtered_chunks, retrieval_decision = self._retrieval_guard.filter_chunks(chunks)
            sources = self._build_sources(filtered_chunks)

            yield SourcesEvent(sources=sources, confidence=0.8)

            # 5. Get history and generate
            history = await self._get_conversation_history(conversation.id, db_session)

            # 6. Stream answer tokens
            answer_parts: list[str] = []
            async for token in self._llm.generate_answer_stream(
                question=chat_request.question,
                context_chunks=filtered_chunks,
                conversation_history=history,
            ):
                answer_parts.append(token)
                yield ChunkEvent(token=token)

            answer = "".join(answer_parts)

            # 7. Output guardrail
            output_decision, confidence, hallucination_risk = await self._output_guard.check(
                question=chat_request.question,
                answer=answer,
                source_chunks=filtered_chunks,
            )

            yield GuardrailEvent(
                layer=output_decision.layer.value,
                action=output_decision.action.value,
                reason=output_decision.reason,
                confidence=output_decision.confidence,
            )

            # Save messages
            await self._save_messages(
                conversation.id,
                chat_request.question,
                answer,
                input_result,
                retrieval_decision,
                output_decision,
                sources,
                confidence,
                hallucination_risk,
                db_session,
            )

            latency_ms = int((time.monotonic() - start_time) * 1000)

            yield DoneEvent(
                message_id=uuid.uuid4(),
                confidence=confidence,
                hallucination_risk=hallucination_risk,
                sources=sources,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            logger.error("Streaming error: %s", exc)
            yield ErrorEvent(
                code="UNKNOWN",
                detail=str(exc),
            )

    async def _get_or_create_conversation(
        self,
        conversation_id: uuid.UUID | None,
        first_question: str,
        document_ids: list[uuid.UUID] | None,
        db_session: AsyncSession,
    ) -> Conversation:
        """Get existing or create new conversation."""
        if conversation_id:
            result = await db_session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        # Create new conversation
        title = first_question[:100] if first_question else "New Conversation"
        doc_ids = [str(d) for d in document_ids] if document_ids else []

        conv = Conversation(
            title=title,
            document_ids=doc_ids,
        )
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)
        return conv

    async def _get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> list[dict[str, str]]:
        """Get last 10 messages for context."""
        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        messages = result.scalars().all()
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

    @staticmethod
    def _build_sources(chunks: list[dict[str, Any]]) -> list[SourceCitation]:
        """Build SourceCitation objects from retrieved chunks."""
        sources: list[SourceCitation] = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata", {})
            sources.append(
                SourceCitation(
                    source_number=i,
                    chunk_id=chunk.get("id", chunk.get("metadata", {}).get("chunk_id", uuid.uuid4())),
                    document_id=meta.get("document_id", ""),
                    document_title=meta.get("document_title", "Unknown"),
                    document_filename=meta.get("document_filename", ""),
                    page_number=meta.get("page_number"),
                    chunk_text=chunk.get("document", "")[:500],
                    similarity_score=chunk.get("similarity_score", 0.0),
                    rerank_score=chunk.get("rerank_score"),
                )
            )
        return sources

    async def _log_guardrail(
        self,
        decision: GuardrailDecision,
        input_text: str,
        db_session: AsyncSession,
    ) -> None:
        """Log guardrail decision to database."""
        from guardrag.infra.database import GuardrailLog
        log = GuardrailLog(
            layer=decision.layer.value,
            action=decision.action.value,
            reason=decision.reason,
            confidence=decision.confidence,
            input_text=input_text[:1000],
            query_hash=__import__("hashlib").sha256(input_text.encode()).hexdigest(),
            details=decision.model_dump(),
        )
        db_session.add(log)
        await db_session.commit()

    async def _save_messages(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: str,
        input_decision: GuardrailDecision,
        retrieval_decision: GuardrailDecision,
        output_decision: GuardrailDecision,
        sources: list[SourceCitation],
        confidence: float,
        hallucination_risk: float,
        db_session: AsyncSession,
    ) -> None:
        """Save user and assistant messages."""
        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=question,
            guardrail_result={"input": input_decision.model_dump()},
        )
        db_session.add(user_msg)
        await db_session.flush()

        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=answer,
            guardrail_result={
                "input": input_decision.model_dump(),
                "retrieval": retrieval_decision.model_dump(),
                "output": output_decision.model_dump(),
            },
            sources=[s.model_dump(mode="json") for s in sources],
            confidence_score=confidence,
            hallucination_risk=hallucination_risk,
        )
        db_session.add(assistant_msg)

        result = await db_session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.message_count += 2

        await db_session.commit()
