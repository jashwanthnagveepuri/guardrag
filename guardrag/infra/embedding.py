"""Embedding service using LangChain OpenAIEmbeddings."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Any

from langchain_openai import OpenAIEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guardrag.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings with caching and retries."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            chunk_size=100,
        )
        self._model_name = settings.openai_embedding_model

    def _cache_key(self, text: str) -> str:
        """Generate a cache key for a text string."""
        return hashlib.sha256(f"{text}:{self._model_name}".encode()).hexdigest()

    @lru_cache(maxsize=10000)
    def _cached_embed_query(self, text_hash: str, text: str) -> list[float]:
        """Cached single query embedding.

        The text_hash is used as the cache key; text is passed through
        to ensure the embedding is computed for the right content.
        """
        try:
            return self._embeddings.embed_query(text)
        except Exception as exc:
            logger.error("Embedding query failed: %s", exc)
            raise

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents in batches of 100.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                embeddings = self._embeddings.embed_documents(batch)
                results.extend(embeddings)
                logger.debug(
                    "Embedded batch %d-%d of %d",
                    i, min(i + batch_size, len(texts)), len(texts),
                )
            except Exception as exc:
                logger.error("Batch embedding failed for indices %d-%d: %s", i, i + batch_size, exc)
                raise
        return results

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text with LRU caching.

        Args:
            text: The query text to embed.

        Returns:
            Single embedding vector.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty query text")

        key = self._cache_key(text)
        return self._cached_embed_query(key, text)

    @property
    def embedding_dimension(self) -> int:
        """Return the embedding dimension for the configured model."""
        model_dims: dict[str, int] = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return model_dims.get(self._model_name, 3072)
