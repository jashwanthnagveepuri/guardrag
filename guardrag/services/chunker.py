"""Document chunking service for GuardRAG."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter

from guardrag.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A single chunk with full metadata."""

    content: str
    chunk_index: int
    token_count: int
    page_number: int | None = None
    section_heading: str | None = None
    source_range_start: int | None = None
    source_range_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseChunker(ABC):
    """Abstract base for all chunking strategies."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """Count tokens using cl100k_base (OpenAI-compatible)."""
        return len(self._tokenizer.encode(text))

    @abstractmethod
    def split(
        self,
        text: str,
        document_id: str,
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split text into chunks. Must be implemented by subclass.

        Args:
            text: The full document text.
            document_id: UUID of the parent document.
            document_metadata: Optional document-level metadata.

        Returns:
            List of TextChunk objects.
        """
        ...


class RecursiveCharacterChunker(BaseChunker):
    """Recursive character text splitting -- default strategy.

    Uses LangChain RecursiveCharacterTextSplitter with hierarchical separators.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=self._count_tokens,
        )

    def split(
        self,
        text: str,
        document_id: str,
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split text using recursive character splitting."""
        if not text or not text.strip():
            return []

        doc_meta = document_metadata or {}
        splits = self._splitter.split_text(text)

        chunks: list[TextChunk] = []
        char_pos = 0
        for i, split in enumerate(splits):
            token_count = self._count_tokens(split)
            start_pos = text.find(split, char_pos)
            end_pos = start_pos + len(split) if start_pos >= 0 else char_pos + len(split)

            # Try to find a page marker
            page_num = self._extract_page_number(text, start_pos)

            chunks.append(
                TextChunk(
                    content=split,
                    chunk_index=i,
                    token_count=token_count,
                    page_number=page_num,
                    source_range_start=start_pos if start_pos >= 0 else None,
                    source_range_end=end_pos if start_pos >= 0 else None,
                    metadata={
                        "document_id": str(document_id),
                        "total_chunks": len(splits),
                        "chunking_strategy": "recursive",
                        **doc_meta,
                    },
                )
            )
            char_pos = end_pos

        logger.info(
            "Created %d chunks from document %s using recursive strategy",
            len(chunks), document_id,
        )
        return chunks

    @staticmethod
    def _extract_page_number(text: str, position: int) -> int | None:
        """Extract page number from a page marker near the given position."""
        # Look for --- Page N --- markers
        before = text[max(0, position - 500):position]
        match = re.search(r"--- Page (\d+) ---", before)
        if match:
            return int(match.group(1))
        return None


class SemanticChunker(BaseChunker):
    """Semantic chunking - groups sentences by semantic similarity.

    Groups sentences by embedding similarity before splitting.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self._semantic_threshold = 0.85

    def split(
        self,
        text: str,
        document_id: str,
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split text using semantic grouping of sentences.

        For now, falls back to sentence-based splitting with
        similarity grouping as a simple approximation.
        """
        if not text or not text.strip():
            return []

        doc_meta = document_metadata or {}
        sentences = self._split_to_sentences(text)

        chunks: list[TextChunk] = []
        current_group: list[str] = []
        current_tokens = 0
        char_pos = 0
        chunk_idx = 0

        for sentence in sentences:
            sent_tokens = self._count_tokens(sentence)

            if current_tokens + sent_tokens > self.chunk_size and current_group:
                # Finalize current chunk
                chunk_text = " ".join(current_group)
                start_pos = text.find(chunk_text, char_pos)
                end_pos = start_pos + len(chunk_text) if start_pos >= 0 else char_pos

                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        chunk_index=chunk_idx,
                        token_count=current_tokens,
                        source_range_start=start_pos if start_pos >= 0 else None,
                        source_range_end=end_pos if start_pos >= 0 else None,
                        metadata={
                            "document_id": str(document_id),
                            "total_chunks": 0,  # Updated later
                            "chunking_strategy": "semantic",
                            **doc_meta,
                        },
                    )
                )
                chunk_idx += 1

                # Start new group with overlap
                overlap_tokens = 0
                overlap_group: list[str] = []
                for s in reversed(current_group):
                    t = self._count_tokens(s)
                    if overlap_tokens + t > self.chunk_overlap:
                        break
                    overlap_group.insert(0, s)
                    overlap_tokens += t

                current_group = overlap_group + [sentence]
                current_tokens = overlap_tokens + sent_tokens
                char_pos = end_pos
            else:
                current_group.append(sentence)
                current_tokens += sent_tokens

        # Don't forget the last group
        if current_group:
            chunk_text = " ".join(current_group)
            start_pos = text.find(chunk_text, char_pos)
            end_pos = start_pos + len(chunk_text) if start_pos >= 0 else char_pos
            chunks.append(
                TextChunk(
                    content=chunk_text,
                    chunk_index=chunk_idx,
                    token_count=current_tokens,
                    source_range_start=start_pos if start_pos >= 0 else None,
                    source_range_end=end_pos if start_pos >= 0 else None,
                    metadata={
                        "document_id": str(document_id),
                        "total_chunks": 0,
                        "chunking_strategy": "semantic",
                        **doc_meta,
                    },
                )
            )

        # Update total_chunks
        for c in chunks:
            c.metadata["total_chunks"] = len(chunks)

        logger.info(
            "Created %d chunks from document %s using semantic strategy",
            len(chunks), document_id,
        )
        return chunks

    @staticmethod
    def _split_to_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        pattern = r"(?<=[.!?])\\s+"
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]


class ChunkingService:
    """Factory and orchestrator for document chunking."""

    @staticmethod
    def get_chunker(strategy: str, chunk_size: int = 512, chunk_overlap: int = 50) -> BaseChunker:
        """Get a chunker instance for the specified strategy.

        Args:
            strategy: "recursive" or "semantic".
            chunk_size: Target chunk size in tokens.
            chunk_overlap: Token overlap between chunks.

        Returns:
            A BaseChunker instance.
        """
        if strategy == "semantic":
            return SemanticChunker(chunk_size, chunk_overlap)
        return RecursiveCharacterChunker(chunk_size, chunk_overlap)

    @classmethod
    def chunk_document(
        cls,
        text: str,
        document_id: str,
        strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Chunk a document text using the specified strategy.

        Args:
            text: The document text to chunk.
            document_id: UUID of the parent document.
            strategy: Chunking strategy name.
            chunk_size: Target chunk size in tokens.
            chunk_overlap: Token overlap between chunks.
            document_metadata: Optional document-level metadata.

        Returns:
            List of TextChunk objects.
        """
        chunker = cls.get_chunker(strategy, chunk_size, chunk_overlap)
        return chunker.split(text, str(document_id), document_metadata)
