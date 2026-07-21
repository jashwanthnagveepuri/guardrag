"""Document management API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.api.dependencies import get_db, get_document_service
from guardrag.core.models import (
    ChunkListResponse,
    DocumentFilterParams,
    DocumentListResponse,
    DocumentResponse,
    ErrorResponse,
)
from guardrag.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
    },
)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    chunking_strategy: Annotated[str, Form()] = "recursive",
    chunk_size: Annotated[int, Form()] = 512,
    chunk_overlap: Annotated[int, Form()] = 50,
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Upload a document for processing.

    Supports PDF, TXT, MD, and DOCX files up to 50MB.
    """
    try:
        return await doc_service.upload_document(
            file=file,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            db_session=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    file_type: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """List documents with pagination and filtering."""
    from guardrag.core.constants import DocumentStatus

    filters = DocumentFilterParams(
        page=page,
        page_size=page_size,
        status=DocumentStatus(status) if status else None,
        file_type=file_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,  # type: ignore[arg-type]
    )
    return await doc_service.list_documents(filters, db)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Get a single document by ID."""
    doc = await doc_service.get_document(document_id, db)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
) -> None:
    """Delete a document."""
    deleted = await doc_service.delete_document(document_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )


@router.get(
    "/{document_id}/chunks",
    response_model=ChunkListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_document_chunks(
    document_id: uuid.UUID,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
) -> ChunkListResponse:
    """Get chunks for a document."""
    chunks = await doc_service.get_chunks(document_id, page, page_size, db)
    if chunks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return chunks
