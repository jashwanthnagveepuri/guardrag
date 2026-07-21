"""FastAPI dependencies for GuardRAG."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.infra.chroma_store import ChromaStore
from guardrag.infra.database import get_db_session
from guardrag.infra.embedding import EmbeddingService
from guardrag.infra.llm import LLMService
from guardrag.services.chat import ChatService
from guardrag.services.document import DocumentService
from guardrag.services.guardrails.input_guardrail import InputGuardrail
from guardrag.services.guardrails.output_guardrail import OutputGuardrail
from guardrag.services.retriever import RetrieverService


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_db_session():
        request.state.db_session = session
        yield session


def get_chroma_store(request: Request) -> ChromaStore:
    """Get or create a ChromaStore instance."""
    if not hasattr(request.app.state, "chroma_store"):
        request.app.state.chroma_store = ChromaStore()
    return request.app.state.chroma_store


def get_embedding_service(request: Request) -> EmbeddingService:
    """Get or create an EmbeddingService instance."""
    if not hasattr(request.app.state, "embedding_service"):
        request.app.state.embedding_service = EmbeddingService()
    return request.app.state.embedding_service


def get_llm_service(request: Request) -> LLMService:
    """Get or create an LLMService instance."""
    if not hasattr(request.app.state, "llm_service"):
        request.app.state.llm_service = LLMService()
    return request.app.state.llm_service


def get_retriever(request: Request) -> RetrieverService:
    """Get or create a RetrieverService instance."""
    if not hasattr(request.app.state, "retriever"):
        chroma = get_chroma_store(request)
        embedder = get_embedding_service(request)
        request.app.state.retriever = RetrieverService(
            chroma_store=chroma,
            embedding_service=embedder,
        )
    return request.app.state.retriever


def get_input_guardrail(request: Request) -> InputGuardrail:
    """Get or create an InputGuardrail instance."""
    if not hasattr(request.app.state, "input_guardrail"):
        request.app.state.input_guardrail = InputGuardrail()
    return request.app.state.input_guardrail


def get_output_guardrail(request: Request) -> OutputGuardrail:
    """Get or create an OutputGuardrail instance."""
    if not hasattr(request.app.state, "output_guardrail"):
        request.app.state.output_guardrail = OutputGuardrail()
    return request.app.state.output_guardrail


def get_chat_service(request: Request) -> ChatService:
    """Get or create a ChatService instance."""
    if not hasattr(request.app.state, "chat_service"):
        request.app.state.chat_service = ChatService(
            input_guardrail=get_input_guardrail(request),
            output_guardrail=get_output_guardrail(request),
            retriever=get_retriever(request),
            llm_service=get_llm_service(request),
        )
    return request.app.state.chat_service


def get_document_service(request: Request) -> DocumentService:
    """Get or create a DocumentService instance."""
    if not hasattr(request.app.state, "document_service"):
        request.app.state.document_service = DocumentService(
            chroma_store=get_chroma_store(request),
            embedding_service=get_embedding_service(request),
        )
    return request.app.state.document_service
