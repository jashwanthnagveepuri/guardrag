"""Retrieval service for GuardRAG."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sentence_transformers import CrossEncoder

from guardrag.core.config import get_settings
from guardrag.infra.chroma_store import ChromaStore
from guardrag.infra.embedding import EmbeddingService

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RetrieverService:
    """Service for retrieving and re-ranking document chunks."""

    def __init__(
        self,
        chroma_store: ChromaStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._chroma = chroma_store or ChromaStore()
        self._embedder = embedding_service or EmbeddingService()
        self._reranker: CrossEncoder | None = None

    def _get_reranker(self) -> CrossEncoder:
        """Lazy-load the cross-encoder re-ranker model."""
        if self._reranker is None:
            logger.info("Loading cross-encoder re-ranker model: %s", RERANKER_MODEL)
            self._reranker = CrossEncoder(RERANKER_MODEL)
        return self._reranker

    async def retrieve(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant chunks using MMR + cross-encoder re-ranking.

        Pipeline:
        1. Embed the query
        2. MMR search (fetch_k=20, lambda=0.5)
        3. Cross-encoder re-ranking
        4. Return top_k with relevance scores

        Args:
            query: The user query string.
            document_ids: Optional list of document UUIDs to scope search.
            top_k: Number of final results to return.

        Returns:
            List of chunk dicts with document, metadata, and scores.
        """
        settings = get_settings()

        # Step 1: Embed query
        query_embedding = self._embedder.embed_query(query)

        # Step 2: MMR search
        mmr_results = self._chroma.search_mmr(
            query_embedding=query_embedding,
            fetch_k=settings.retrieval_mmr_fetch_k,
            lambda_mult=settings.retrieval_mmr_lambda,
            top_k=settings.retrieval_mmr_fetch_k,  # Get fetch_k for re-ranking
            document_ids=document_ids,
        )

        if not mmr_results:
            logger.warning("No results from MMR search for query: %s", query[:50])
            return []

        # Step 3: Cross-encoder re-ranking
        reranked = self._rerank(query, mmr_results)

        # Step 4: Return top_k
        final_top_k = min(top_k, len(reranked))
        return reranked[:final_top_k]

    async def retrieve_basic(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Simple similarity search without re-ranking (fallback).

        Args:
            query: The user query string.
            top_k: Number of results to return.
            document_ids: Optional list of document UUIDs to scope search.

        Returns:
            List of chunk dicts with document, metadata, and scores.
        """
        query_embedding = self._embedder.embed_query(query)

        results = self._chroma.search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids,
        )

        chunks: list[dict[str, Any]] = []
        if results and results.get("ids"):
            ids = results["ids"][0] if results["ids"] else []
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            dists = results["distances"][0] if results.get("distances") else []

            for i, cid in enumerate(ids):
                similarity = 1.0 - (dists[i] if i < len(dists) else 0.0)
                chunks.append({
                    "id": cid,
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "similarity_score": max(0.0, min(1.0, similarity)),
                    "rerank_score": None,
                })

        return chunks

    def _rerank(
        self,
        query: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-rank chunks using cross-encoder.

        Args:
            query: The original query.
            chunks: List of chunk dicts from MMR search.

        Returns:
            List of chunk dicts sorted by re-rank score.
        """
        if not chunks:
            return []

        reranker = self._get_reranker()

        pairs = [[query, chunk.get("document", "")] for chunk in chunks]
        scores = reranker.predict(pairs)

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i]) if i < len(scores) else 0.0
            # Normalize to 0-1 if scores are logits
            if chunk["rerank_score"] > 1.0 or chunk["rerank_score"] < 0.0:
                chunk["rerank_score"] = 1.0 / (1.0 + np.exp(-chunk["rerank_score"]))

        chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return chunks
