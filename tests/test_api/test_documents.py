"""API tests for document management routes.

Tests: upload, list, get, delete, upload_invalid_type
All external services are mocked — no real API calls.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from guardrag.api.main import create_app
from guardrag.core.constants import DocumentStatus
from guardrag.core.models import DocumentListResponse, DocumentResponse


# =============================================================================
# Test: Upload Document
# =============================================================================


@pytest.mark.api
class TestUploadDocument:
    """Tests for POST /api/v1/documents — document upload."""

    async def test_upload_pdf_success(
        self,
        test_client: AsyncClient,
        sample_pdf_bytes: bytes,
    ) -> None:
        """Uploading a valid PDF should return 201 with document metadata."""
        doc_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        now = datetime.now(timezone.utc)

        mock_response = DocumentResponse(
            id=doc_id,
            filename="test-document.pdf",
            original_name="test.pdf",
            content_type="application/pdf",
            file_type="pdf",
            size_bytes=len(sample_pdf_bytes),
            content_hash=hashlib.sha256(sample_pdf_bytes).hexdigest(),
            chunking_strategy="recursive",
            chunk_size=512,
            chunk_overlap=50,
            chunk_count=0,
            status=DocumentStatus.PENDING,
            error_message=None,
            metadata={"title": None, "parser_version": "1.0.0"},  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            processed_at=None,
        )

        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_document = AsyncMock(return_value=mock_response)
            mock_service_cls.return_value = mock_service

            response = await test_client.post(
                "/api/v1/documents",
                data={
                    "chunking_strategy": "recursive",
                    "chunk_size": "512",
                    "chunk_overlap": "50",
                },
                files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["filename"] == "test-document.pdf"
        assert data["file_type"] == "pdf"
        assert data["status"] == "pending"
        assert data["chunk_count"] == 0

    async def test_upload_txt_success(
        self,
        test_client: AsyncClient,
        sample_txt_bytes: bytes,
    ) -> None:
        """Uploading a valid TXT file should return 201."""
        doc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        mock_response = DocumentResponse(
            id=doc_id,
            filename="test-document.txt",
            original_name="test.txt",
            content_type="text/plain",
            file_type="txt",
            size_bytes=len(sample_txt_bytes),
            content_hash=hashlib.sha256(sample_txt_bytes).hexdigest(),
            metadata={"line_count": 7, "word_count": 42, "parser_version": "1.0.0"},  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            chunking_strategy="recursive",
            chunk_size=512,
            chunk_overlap=50,
            chunk_count=0,
            status=DocumentStatus.PENDING,
            processed_at=None,
        )

        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_document = AsyncMock(return_value=mock_response)
            mock_service_cls.return_value = mock_service

            response = await test_client.post(
                "/api/v1/documents",
                files={"file": ("test.txt", sample_txt_bytes, "text/plain")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["file_type"] == "txt"
        assert data["content_type"] == "text/plain"


# =============================================================================
# Test: List Documents
# =============================================================================


@pytest.mark.api
class TestListDocuments:
    """Tests for GET /api/v1/documents — document listing."""

    async def test_list_documents_pagination(
        self,
        test_client: AsyncClient,
        sample_document: DocumentResponse,
    ) -> None:
        """Listing documents should return paginated results."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.list_documents = AsyncMock(
                return_value=DocumentListResponse(
                    items=[sample_document],
                    meta={
                        "page": 1,
                        "page_size": 20,
                        "total": 1,
                        "total_pages": 1,
                        "has_next": False,
                        "has_prev": False,
                    },
                )
            )
            mock_service_cls.return_value = mock_service

            response = await test_client.get("/api/v1/documents?page=1&page_size=20")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert data["meta"]["page"] == 1
        assert data["meta"]["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["filename"] == "test-document.pdf"

    async def test_list_documents_with_filters(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Listing with status filter should work."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.list_documents = AsyncMock(
                return_value=DocumentListResponse(
                    items=[],
                    meta={
                        "page": 1,
                        "page_size": 20,
                        "total": 0,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": False,
                    },
                )
            )
            mock_service_cls.return_value = mock_service

            response = await test_client.get(
                "/api/v1/documents?status=completed&file_type=pdf&search=annual"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meta"]["total"] == 0
        assert data["items"] == []


# =============================================================================
# Test: Get Document
# =============================================================================


@pytest.mark.api
class TestGetDocument:
    """Tests for GET /api/v1/documents/{id} — get single document."""

    async def test_get_document_success(
        self,
        test_client: AsyncClient,
        sample_document: DocumentResponse,
    ) -> None:
        """Getting an existing document should return 200 with full details."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_document = AsyncMock(return_value=sample_document)
            mock_service_cls.return_value = mock_service

            response = await test_client.get(
                f"/api/v1/documents/{sample_document.id}"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_document.id)
        assert data["filename"] == "test-document.pdf"
        assert data["original_name"] == "Annual Report 2024.pdf"
        assert data["file_type"] == "pdf"
        assert data["status"] == "completed"
        assert data["chunk_count"] == 24
        assert data["metadata"]["total_pages"] == 42

    async def test_get_document_not_found(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Getting a non-existent document should return 404."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_document = AsyncMock(return_value=None)
            mock_service_cls.return_value = mock_service

            response = await test_client.get(
                f"/api/v1/documents/{uuid.uuid4()}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Delete Document
# =============================================================================


@pytest.mark.api
class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{id} — delete document."""

    async def test_delete_document_success(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Deleting an existing document should return 204."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_document = AsyncMock(return_value=True)
            mock_service_cls.return_value = mock_service

            response = await test_client.delete(
                f"/api/v1/documents/{uuid.uuid4()}"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_document_not_found(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Deleting a non-existent document should return 404."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_document = AsyncMock(return_value=False)
            mock_service_cls.return_value = mock_service

            response = await test_client.delete(
                f"/api/v1/documents/{uuid.uuid4()}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Upload Invalid Type
# =============================================================================


@pytest.mark.api
class TestUploadInvalid:
    """Tests for invalid upload scenarios."""

    async def test_upload_invalid_file_type(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Uploading an unsupported file type should return 400."""
        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_document = AsyncMock(
                side_effect=ValueError("Unsupported content type: image/png")
            )
            mock_service_cls.return_value = mock_service

            response = await test_client.post(
                "/api/v1/documents",
                files={"file": ("image.png", b"fake-image-data", "image/png")},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_upload_file_too_large(self, test_client: AsyncClient) -> None:
        """Uploading a file exceeding max size should be rejected."""
        # This is handled by the endpoint's max file size validation
        # FastAPI/Starlette raises 413 for files exceeding max size
        large_file = b"x" * (60 * 1024 * 1024)  # 60MB

        with patch(
            "guardrag.api.routes.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_document = AsyncMock(
                side_effect=ValueError("File exceeds maximum size of 50MB")
            )
            mock_service_cls.return_value = mock_service

            response = await test_client.post(
                "/api/v1/documents",
                files={"file": ("huge.pdf", large_file, "application/pdf")},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_upload_missing_file(self, test_client: AsyncClient) -> None:
        """Uploading without a file should return 422."""
        response = await test_client.post(
            "/api/v1/documents",
            data={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
