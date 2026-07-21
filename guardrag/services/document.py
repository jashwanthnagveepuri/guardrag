"""Document management service for GuardRAG.

Handles document upload, parsing, chunking, embedding, and storage.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.core.config import get_settings
from guardrag.core.constants import DocumentStatus
from guardrag.core.models import (
    ChunkListResponse,
    ChunkResponse,
    DocumentFilterParams,
    DocumentListResponse,
    DocumentMetadata,
    DocumentResponse,
    PaginationMeta,
    SourceRange,
)
from guardrag.infra.chroma_store import ChromaStore
from guardrag.infra.database import Chunk, Document
from guardrag.infra.embedding import EmbeddingService
from guardrag.services.chunker import ChunkingService
from guardrag.services.parser import ParserFactory

logger = logging.getLogger(__name__)

# Map file extensions to normalized types
FILE_TYPE_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "md",
    ".docx": "docx",
}

# Map MIME types to extensions
MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


class DocumentService:
    """Service for document CRUD operations and processing pipeline."""

    def __init__(
        self,
        chroma_store: ChromaStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._chroma = chroma_store or ChromaStore()
        self._embedder = embedding_service or EmbeddingService()
        self._upload_dir = Path(tempfile.gettempdir()) / "guardrag_uploads"
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        file: UploadFile,
        chunking_strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        db_session: AsyncSession | None = None,
    ) -> DocumentResponse:
        """Upload and process a document.

        Pipeline:
        1. Validate file type and size
        2. Save to temp storage
        3. Parse document -> text
        4. Chunk text
        5. Embed chunks
        6. Store chunks in ChromaDB
        7. Save document metadata to PostgreSQL

        Args:
            file: The uploaded file.
            chunking_strategy: Chunking strategy name.
            chunk_size: Target chunk size in tokens.
            chunk_overlap: Token overlap between chunks.
            db_session: Database session.

        Returns:
            DocumentResponse with document info.
        """
        if db_session is None:
            raise ValueError("Database session is required")

        settings = get_settings()

        # 1. Validate
        content_type = file.content_type or "application/octet-stream"
        if content_type not in settings.allowed_mime_types_list:
            raise ValueError(f"Unsupported file type: {content_type}")

        file_content = await file.read()
        if len(file_content) > settings.upload_max_file_size:
            raise ValueError(
                f"File too large: {len(file_content)} bytes (max: {settings.upload_max_file_size})"
            )

        # Check for duplicate by hash
        content_hash = hashlib.sha256(file_content).hexdigest()
        existing = await db_session.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Document already exists (duplicate content)")

        # 2. Determine file type
        ext = MIME_TO_EXT.get(content_type, ".bin")
        file_type = FILE_TYPE_MAP.get(ext, "unknown")
        doc_id = uuid.uuid4()
        storage_path = str(self._upload_dir / f"{doc_id}{ext}")

        # Save file
        with open(storage_path, "wb") as f:
            f.write(file_content)

        # Create document record
        document = Document(
            id=doc_id,
            filename=f"{doc_id}{ext}",
            original_name=file.filename or "unnamed",
            content_type=content_type,
            file_type=file_type,
            size_bytes=len(file_content),
            content_hash=content_hash,
            storage_path=storage_path,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            status=DocumentStatus.PROCESSING,
            metadata_={},
        )
        db_session.add(document)
        await db_session.commit()

        # 3. Parse
        try:
            parse_result = ParserFactory.parse(file_content, content_type)
            document.metadata_ = {
                **parse_result.metadata,
                "parser_version": "1.0.0",
            }
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = f"Parse error: {exc}"
            await db_session.commit()
            raise

        # 4. Chunk
        try:
            chunks = ChunkingService.chunk_document(
                text=parse_result.text,
                document_id=str(doc_id),
                strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                document_metadata={
                    "document_title": document.original_name,
                    "file_type": file_type,
                },
            )
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = f"Chunking error: {exc}"
            await db_session.commit()
            raise

        # 5. Embed
        try:
            texts = [c.content for c in chunks]
            embeddings = self._embedder.embed_documents(texts)
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = f"Embedding error: {exc}"
            await db_session.commit()
            raise

        # 6. Store in ChromaDB
        try:
            chroma_ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = []
            for i, chunk in enumerate(chunks):
                meta = {
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": str(doc_id),
                    "document_title": document.original_name,
                    "document_filename": document.filename,
                    "file_type": file_type,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": len(chunks),
                    "chunking_strategy": chunking_strategy,
                    "token_count": chunk.token_count,
                    "page_number": chunk.page_number,
                }
                metadatas.append(meta)

            self._chroma.add_chunks(
                chunk_ids=chroma_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = f"ChromaDB error: {exc}"
            await db_session.commit()
            raise

        # 7. Save chunks to PostgreSQL
        for i, chunk in enumerate(chunks):
            db_chunk = Chunk(
                document_id=doc_id,
                content=chunk.content,
                embedding_stored=True,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                section_heading=chunk.section_heading,
                source_range_start=chunk.source_range_start,
                source_range_end=chunk.source_range_end,
                chroma_id=chroma_ids[i],
                metadata_=chunk.metadata,
            )
            db_session.add(db_chunk)

        document.status = DocumentStatus.COMPLETED
        document.chunk_count = len(chunks)
        await db_session.commit()
        await db_session.refresh(document)

        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_name=document.original_name,
            content_type=document.content_type,
            file_type=document.file_type,
            size_bytes=document.size_bytes,
            content_hash=document.content_hash,
            chunking_strategy=chunking_strategy,  # type: ignore[arg-type]
            chunk_size=document.chunk_size,
            chunk_overlap=document.chunk_overlap,
            chunk_count=document.chunk_count,
            status=document.status,  # type: ignore[arg-type]
            error_message=document.error_message,
            metadata=DocumentMetadata(**document.metadata_),
            created_at=document.created_at,
            updated_at=document.updated_at,
            processed_at=document.processed_at,
        )

    async def list_documents(
        self,
        filters: DocumentFilterParams,
        db_session: AsyncSession,
    ) -> DocumentListResponse:
        """List documents with pagination and filtering.

        Args:
            filters: Filter and pagination parameters.
            db_session: Database session.

        Returns:
            DocumentListResponse with paginated results.
        """
        query = select(Document).where(Document.deleted_at.is_(None))

        if filters.status:
            query = query.where(Document.status == filters.status.value)
        if filters.file_type:
            query = query.where(Document.file_type == filters.file_type)
        if filters.search:
            query = query.where(Document.original_name.ilike(f"%{filters.search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db_session.execute(count_query)
        total = total_result.scalar() or 0

        # Sort
        sort_col = getattr(Document, filters.sort_by, Document.created_at)
        if filters.sort_order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await db_session.execute(query)
        documents = result.scalars().all()

        total_pages = (total + filters.page_size - 1) // filters.page_size

        return DocumentListResponse(
            meta=PaginationMeta(
                page=filters.page,
                page_size=filters.page_size,
                total=total,
                total_pages=total_pages,
                has_next=filters.page < total_pages,
                has_prev=filters.page > 1,
            ),
            items=[
                DocumentResponse(
                    id=d.id,
                    filename=d.filename,
                    original_name=d.original_name,
                    content_type=d.content_type,
                    file_type=d.file_type,
                    size_bytes=d.size_bytes,
                    content_hash=d.content_hash,
                    chunking_strategy=d.chunking_strategy,  # type: ignore[arg-type]
                    chunk_size=d.chunk_size,
                    chunk_overlap=d.chunk_overlap,
                    chunk_count=d.chunk_count,
                    status=d.status,  # type: ignore[arg-type]
                    error_message=d.error_message,
                    metadata=DocumentMetadata(**d.metadata_),
                    created_at=d.created_at,
                    updated_at=d.updated_at,
                    processed_at=d.processed_at,
                )
                for d in documents
            ],
        )

    async def get_document(
        self,
        document_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> DocumentResponse | None:
        """Get a single document by ID.

        Args:
            document_id: The document UUID.
            db_session: Database session.

        Returns:
            DocumentResponse or None if not found.
        """
        result = await db_session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )
        d = result.scalar_one_or_none()
        if not d:
            return None

        return DocumentResponse(
            id=d.id,
            filename=d.filename,
            original_name=d.original_name,
            content_type=d.content_type,
            file_type=d.file_type,
            size_bytes=d.size_bytes,
            content_hash=d.content_hash,
            chunking_strategy=d.chunking_strategy,  # type: ignore[arg-type]
            chunk_size=d.chunk_size,
            chunk_overlap=d.chunk_overlap,
            chunk_count=d.chunk_count,
            status=d.status,  # type: ignore[arg-type]
            error_message=d.error_message,
            metadata=DocumentMetadata(**d.metadata_),
            created_at=d.created_at,
            updated_at=d.updated_at,
            processed_at=d.processed_at,
        )

    async def delete_document(
        self,
        document_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> bool:
        """Soft-delete a document and remove from ChromaDB.

        Args:
            document_id: The document UUID.
            db_session: Database session.

        Returns:
            True if deleted, False if not found.
        """
        result = await db_session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )
        d = result.scalar_one_or_none()
        if not d:
            return False

        # Soft delete in DB
        from datetime import datetime, timezone
        d.deleted_at = datetime.now(timezone.utc)
        d.status = DocumentStatus.FAILED

        # Remove from ChromaDB
        try:
            self._chroma.delete_by_document(str(document_id))
        except Exception as exc:
            logger.error("Failed to delete chunks from ChromaDB: %s", exc)

        await db_session.commit()
        return True

    async def get_chunks(
        self,
        document_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        db_session: AsyncSession | None = None,
    ) -> ChunkListResponse | None:
        """Get chunks for a document.

        Args:
            document_id: The document UUID.
            page: Page number.
            page_size: Items per page.
            db_session: Database session.

        Returns:
            ChunkListResponse or None if document not found.
        """
        if db_session is None:
            raise ValueError("Database session is required")

        # Verify document exists
        doc_result = await db_session.execute(
            select(Document).where(Document.id == document_id)
        )
        if not doc_result.scalar_one_or_none():
            return None

        # Count
        count_query = select(func.count()).where(Chunk.document_id == document_id)
        count_result = await db_session.execute(count_query)
        total = count_result.scalar() or 0

        # Get chunks
        query = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db_session.execute(query)
        chunks = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return ChunkListResponse(
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
            items=[
                ChunkResponse(
                    id=c.id,
                    document_id=c.document_id,
                    content=c.content,
                    chunk_index=c.chunk_index,
                    token_count=c.token_count,
                    page_number=c.page_number,
                    section_heading=c.section_heading,
                    source_range=SourceRange(
                        start_char=c.source_range_start or 0,
                        end_char=c.source_range_end or 0,
                    ) if c.source_range_start is not None else None,
                    metadata=c.metadata_,
                    created_at=c.created_at,
                )
                for c in chunks
            ],
        )
