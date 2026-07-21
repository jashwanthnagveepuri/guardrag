"""Unit tests for document parser service.

Tests: parse_pdf, parse_txt, parse_md, parse_docx
No external API calls — all parsing is local.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

import pytest

from guardrag.services.parser import (
    DocxParser,
    MarkdownParser,
    ParserFactory,
    PDFParser,
    TextParser,
)


# =============================================================================
# Test: Parse PDF
# =============================================================================


@pytest.mark.services
class TestParsePDF:
    """Tests for PDFParser."""

    def test_parse_pdf_extracts_text(self, sample_pdf_bytes: bytes) -> None:
        """PDF parser should extract text content from valid PDF bytes."""
        parser = PDFParser()
        result = parser.parse(sample_pdf_bytes)

        assert result.text is not None
        assert len(result.text) > 0
        assert "page" in result.text.lower() or "revenue" in result.text.lower()

    def test_parse_pdf_returns_metadata(self, sample_pdf_bytes: bytes) -> None:
        """PDF parser should return metadata including page count."""
        parser = PDFParser()
        result = parser.parse(sample_pdf_bytes)

        assert result.page_count is not None
        assert result.page_count > 0
        assert "total_pages" in result.metadata
        assert result.metadata["total_pages"] == result.page_count

    def test_parse_pdf_supported_types(self) -> None:
        """PDF parser should declare application/pdf support."""
        parser = PDFParser()
        assert "application/pdf" in parser.supported_types
        assert len(parser.supported_types) == 1

    def test_parse_invalid_pdf_raises_error(self) -> None:
        """Parsing invalid PDF bytes should raise an error."""
        parser = PDFParser()
        with pytest.raises(Exception):
            parser.parse(b"this is not a pdf file")

    def test_parse_empty_pdf(self) -> None:
        """Parsing empty bytes should raise an error."""
        parser = PDFParser()
        with pytest.raises(Exception):
            parser.parse(b"")


# =============================================================================
# Test: Parse TXT
# =============================================================================


@pytest.mark.services
class TestParseTXT:
    """Tests for TextParser."""

    def test_parse_txt_extracts_content(self, sample_txt_bytes: bytes) -> None:
        """Text parser should extract all content from a text file."""
        parser = TextParser()
        result = parser.parse(sample_txt_bytes)

        assert "Annual Report 2024" in result.text
        assert "Revenue grew by 23%" in result.text
        assert "Operating margin expanded" in result.text

    def test_parse_txt_returns_metadata(self, sample_txt_bytes: bytes) -> None:
        """Text parser should return line and word count metadata."""
        parser = TextParser()
        result = parser.parse(sample_txt_bytes)

        assert "line_count" in result.metadata
        assert "word_count" in result.metadata
        assert result.metadata["line_count"] > 0
        assert result.metadata["word_count"] > 0
        assert result.page_count is None

    def test_parse_txt_supported_types(self) -> None:
        """Text parser should declare text/plain support."""
        parser = TextParser()
        assert "text/plain" in parser.supported_types

    def test_parse_utf8_text(self) -> None:
        """Text parser should handle UTF-8 content correctly."""
        parser = TextParser()
        content = "Unicode test: 你好世界 ñoño émojis 🚀\nSecond line.".encode("utf-8")
        result = parser.parse(content)

        assert "Unicode test" in result.text
        assert "你好世界" in result.text
        assert "🚀" in result.text

    def test_parse_txt_handles_binary_garbage(self) -> None:
        """Text parser should handle binary content gracefully with replacement."""
        parser = TextParser()
        # Mix of valid text and binary garbage
        content = b"Valid text\n\xff\xfe\x00Binary garbage\nMore valid text"
        result = parser.parse(content)

        assert "Valid text" in result.text
        assert "More valid text" in result.text


# =============================================================================
# Test: Parse MD
# =============================================================================


@pytest.mark.services
class TestParseMD:
    """Tests for MarkdownParser."""

    def test_parse_md_extracts_content(self, sample_md_bytes: bytes) -> None:
        """Markdown parser should extract all markdown content."""
        parser = MarkdownParser()
        result = parser.parse(sample_md_bytes)

        assert "# Annual Report 2024" in result.text
        assert "Revenue grew by **23%**" in result.text
        assert "### Cloud Services" in result.text

    def test_parse_md_returns_header_metadata(self, sample_md_bytes: bytes) -> None:
        """Markdown parser should count headers by level."""
        parser = MarkdownParser()
        result = parser.parse(sample_md_bytes)

        assert "section_count" in result.metadata
        assert "headers" in result.metadata
        assert result.metadata["section_count"] >= 4
        headers = result.metadata["headers"]
        assert "h1" in headers
        assert "h2" in headers
        assert headers["h1"] >= 1  # At least one H1
        assert headers["h2"] >= 2  # At least two H2s

    def test_parse_md_supported_types(self) -> None:
        """Markdown parser should declare markdown MIME type support."""
        parser = MarkdownParser()
        assert "text/markdown" in parser.supported_types
        assert "text/x-markdown" in parser.supported_types

    def test_parse_md_without_headers(self) -> None:
        """Markdown parser should handle files without headers."""
        parser = MarkdownParser()
        content = b"Just some plain markdown text.\nNo headers here.\n"
        result = parser.parse(content)

        assert result.metadata["section_count"] == 0
        assert result.metadata["headers"] == {}
        assert "word_count" in result.metadata


# =============================================================================
# Test: Parse DOCX
# =============================================================================


@pytest.mark.services
class TestParseDOCX:
    """Tests for DocxParser."""

    def _create_minimal_docx(self, paragraphs: list[str]) -> bytes:
        """Create a minimal valid DOCX file in memory.

        DOCX is a ZIP archive containing XML files. We create a minimal
        structure that python-docx can parse.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # [Content_Types].xml
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>",
            )
            # _rels/.rels
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                "</Relationships>",
            )
            # word/_rels/document.xml.rels
            zf.writestr(
                "word/_rels/document.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                "</Relationships>",
            )
            # word/document.xml — the actual content
            body_xml = ""
            for para in paragraphs:
                escaped = (
                    para.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                body_xml += (
                    f'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f'<w:r><w:t>{escaped}</w:t></w:r></w:p>'
                )

            document_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f"<w:body>{body_xml}</w:body></w:document>"
            )
            zf.writestr("word/document.xml", document_xml)

        buf.seek(0)
        return buf.read()

    def test_parse_docx_extracts_text(self) -> None:
        """DOCX parser should extract paragraph text from a valid DOCX file."""
        paragraphs = [
            "Annual Report 2024",
            "",
            "Executive Summary",
            "Revenue grew by 23% year-over-year to $4.2 billion.",
            "Cloud services contributed $1.8B, up 34% YoY.",
        ]
        docx_bytes = self._create_minimal_docx(paragraphs)

        parser = DocxParser()
        result = parser.parse(docx_bytes)

        assert "Annual Report 2024" in result.text
        assert "Revenue grew by 23%" in result.text
        assert "Cloud services contributed" in result.text

    def test_parse_docx_returns_metadata(self) -> None:
        """DOCX parser should return word count metadata."""
        paragraphs = [
            "First paragraph with some content.",
            "Second paragraph with more content here.",
        ]
        docx_bytes = self._create_minimal_docx(paragraphs)

        parser = DocxParser()
        result = parser.parse(docx_bytes)

        assert "word_count" in result.metadata
        assert result.metadata["word_count"] > 0
        assert result.page_count is None

    def test_parse_docx_supported_types(self) -> None:
        """DOCX parser should declare correct MIME type support."""
        parser = DocxParser()
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in parser.supported_types
        )

    def test_parse_docx_empty_paragraphs(self) -> None:
        """DOCX parser should handle documents with empty paragraphs."""
        paragraphs = ["First para.", "", "", "Last para."]
        docx_bytes = self._create_minimal_docx(paragraphs)

        parser = DocxParser()
        result = parser.parse(docx_bytes)

        assert "First para." in result.text
        assert "Last para." in result.text

    def test_parse_invalid_docx_raises_error(self) -> None:
        """Parsing invalid DOCX bytes should raise an error."""
        parser = DocxParser()
        with pytest.raises(Exception):
            parser.parse(b"this is not a docx file")


# =============================================================================
# Test: ParserFactory
# =============================================================================


@pytest.mark.services
class TestParserFactory:
    """Tests for ParserFactory."""

    def test_factory_returns_correct_parser_for_pdf(self) -> None:
        """Factory should return PDFParser for application/pdf."""
        parser = ParserFactory.get_parser("application/pdf")
        assert isinstance(parser, PDFParser)

    def test_factory_returns_correct_parser_for_txt(self) -> None:
        """Factory should return TextParser for text/plain."""
        parser = ParserFactory.get_parser("text/plain")
        assert isinstance(parser, TextParser)

    def test_factory_returns_correct_parser_for_md(self) -> None:
        """Factory should return MarkdownParser for text/markdown."""
        parser = ParserFactory.get_parser("text/markdown")
        assert isinstance(parser, MarkdownParser)

    def test_factory_returns_correct_parser_for_docx(self) -> None:
        """Factory should return DocxParser for DOCX MIME type."""
        parser = ParserFactory.get_parser(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert isinstance(parser, DocxParser)

    def test_factory_raises_for_unsupported_type(self) -> None:
        """Factory should raise ValueError for unsupported MIME types."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            ParserFactory.get_parser("image/png")

    def test_factory_is_supported(self) -> None:
        """is_supported should correctly identify supported types."""
        assert ParserFactory.is_supported("application/pdf") is True
        assert ParserFactory.is_supported("text/plain") is True
        assert ParserFactory.is_supported("text/markdown") is True
        assert ParserFactory.is_supported("image/png") is False
        assert ParserFactory.is_supported("application/json") is False

    def test_factory_case_insensitive(self) -> None:
        """Factory should handle MIME types case-insensitively."""
        parser = ParserFactory.get_parser("APPLICATION/PDF")
        assert isinstance(parser, PDFParser)

    def test_factory_parse_integration(self, sample_txt_bytes: bytes) -> None:
        """Factory.parse should correctly delegate to the right parser."""
        result = ParserFactory.parse(sample_txt_bytes, "text/plain")

        assert "Annual Report 2024" in result.text
        assert "line_count" in result.metadata

    def test_all_supported_types(self) -> None:
        """All expected types should be supported."""
        supported = [
            "application/pdf",
            "text/plain",
            "text/markdown",
            "text/x-markdown",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        for mime_type in supported:
            assert ParserFactory.is_supported(mime_type), f"{mime_type} should be supported"
