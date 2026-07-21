"""Document parser service for GuardRAG."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing a document."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int | None = None


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, content: bytes) -> ParseResult:
        """Parse raw file content into text and metadata.

        Args:
            content: Raw file bytes.

        Returns:
            ParseResult with extracted text and metadata.
        """
        ...

    @property
    @abstractmethod
    def supported_types(self) -> list[str]:
        """Return list of supported MIME types."""
        ...


class PDFParser(BaseParser):
    """Parser for PDF documents using pypdf."""

    @property
    def supported_types(self) -> list[str]:
        return ["application/pdf"]

    def parse(self, content: bytes) -> ParseResult:
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)

            pages: list[str] = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(f"--- Page {i + 1} ---\n{text.strip()}")
                except Exception as exc:
                    logger.warning("Failed to extract text from page %d: %s", i + 1, exc)

            full_text = "\n\n".join(pages)

            metadata: dict[str, Any] = {
                "total_pages": page_count,
                "title": reader.metadata.title if reader.metadata else None,
                "author": reader.metadata.author if reader.metadata else None,
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}

            return ParseResult(
                text=full_text,
                metadata=metadata,
                page_count=page_count,
            )
        except Exception as exc:
            logger.error("PDF parsing failed: %s", exc)
            raise


class TextParser(BaseParser):
    """Parser for plain text files."""

    @property
    def supported_types(self) -> list[str]:
        return ["text/plain"]

    def parse(self, content: bytes) -> ParseResult:
        try:
            text = content.decode("utf-8", errors="replace")
            lines = text.splitlines()
            return ParseResult(
                text=text,
                metadata={
                    "line_count": len(lines),
                    "word_count": len(text.split()),
                },
                page_count=None,
            )
        except Exception as exc:
            logger.error("Text parsing failed: %s", exc)
            raise


class MarkdownParser(BaseParser):
    """Parser for Markdown files preserving header structure."""

    @property
    def supported_types(self) -> list[str]:
        return ["text/markdown", "text/x-markdown"]

    def parse(self, content: bytes) -> ParseResult:
        try:
            text = content.decode("utf-8", errors="replace")
            lines = text.splitlines()

            # Count headers by level
            header_counts: dict[str, int] = {}
            for line in lines:
                match = re.match(r"^(#{1,6})\\s", line)
                if match:
                    level = len(match.group(1))
                    header_counts[f"h{level}"] = header_counts.get(f"h{level}", 0) + 1

            return ParseResult(
                text=text,
                metadata={
                    "line_count": len(lines),
                    "word_count": len(text.split()),
                    "section_count": sum(header_counts.values()),
                    "headers": header_counts,
                },
                page_count=None,
            )
        except Exception as exc:
            logger.error("Markdown parsing failed: %s", exc)
            raise


class DocxParser(BaseParser):
    """Parser for DOCX files using python-docx."""

    @property
    def supported_types(self) -> list[str]:
        return [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

    def parse(self, content: bytes) -> ParseResult:
        try:
            import io
            from docx import Document as DocxDocument

            doc = DocxDocument(io.BytesIO(content))
            paragraphs: list[str] = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())

            full_text = "\n\n".join(paragraphs)

            # Extract core properties
            core_props = doc.core_properties
            metadata: dict[str, Any] = {
                "title": core_props.title,
                "author": core_props.author,
                "word_count": len(full_text.split()),
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}

            return ParseResult(
                text=full_text,
                metadata=metadata,
                page_count=None,
            )
        except Exception as exc:
            logger.error("DOCX parsing failed: %s", exc)
            raise


class ParserFactory:
    """Factory for creating the appropriate parser based on content type."""

    _parsers: list[BaseParser] = [
        PDFParser(),
        TextParser(),
        MarkdownParser(),
        DocxParser(),
    ]

    @classmethod
    def get_parser(cls, content_type: str) -> BaseParser:
        """Get the appropriate parser for a given MIME type.

        Args:
            content_type: The MIME type of the file.

        Returns:
            A parser instance capable of handling the content type.

        Raises:
            ValueError: If no parser supports the content type.
        """
        content_type = content_type.lower().strip()
        for parser in cls._parsers:
            if content_type in parser.supported_types:
                return parser
        raise ValueError(f"Unsupported content type: {content_type}")

    @classmethod
    def parse(cls, content: bytes, content_type: str) -> ParseResult:
        """Parse content using the appropriate parser.

        Args:
            content: Raw file bytes.
            content_type: The MIME type of the file.

        Returns:
            ParseResult with extracted text and metadata.
        """
        parser = cls.get_parser(content_type)
        return parser.parse(content)

    @classmethod
    def is_supported(cls, content_type: str) -> bool:
        """Check if a content type is supported.

        Args:
            content_type: The MIME type to check.

        Returns:
            True if a parser exists for the content type.
        """
        content_type = content_type.lower().strip()
        return any(
            content_type in p.supported_types for p in cls._parsers
        )
