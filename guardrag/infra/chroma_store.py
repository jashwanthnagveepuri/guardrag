"""ChromaDB vector store wrapper for GuardRAG."""

from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings

from guardrag.core.config import get_settings

logger = logging.getLogger(__name__)

CHROMA_COLLECTION_NAME = "guardrag_chunks"
CHROMA_DISTANCE_METRIC = "cosine"

HNSW_CONFIG: dict[str, Any] = {
    "hnsw:space": "cosine",
    "hnsw:construction_ef": 128,
    "hnsw:search_ef": 128,
    "hnsw:M": 16,
    "hnsw:num_threads": 4,
}


class ChromaStore:
    """Async-aware ChromaDB client wrapper.

    Provides CRUD operations for document chunks with metadata,
    similarity search, and MMR diversity search.
    """

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        settings = get_settings()
        self._host = host or settings.chromadb_host
        self._port = port or settings.chromadb_port
        self._client = chromadb.HttpClient(
            host=self._host,
            port=self._port,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )
        self._collection: chromadb.Collection | None = None

    @property
    def collection(self) -> chromadb.Collection:
        """Lazy-loaded collection with HNSW configuration."""
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata=HNSW_CONFIG,
            )
        return self._collection

    def add_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Batch insert chunks into ChromaDB.

        Args:
            chunk_ids: Unique IDs for each chunk.
            embeddings: Vector embeddings for each chunk.
            documents: The text content of each chunk.
            metadatas: Metadata dictionaries for each chunk.
        """
        if not chunk_ids:
            return
        batch_size = 100
        for i in range(0, len(chunk_ids), batch_size):
            end = i + batch_size
            self.collection.add(
                ids=chunk_ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )
            logger.debug("Added batch of %d chunks to ChromaDB", min(batch_size, len(chunk_ids) - i))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Basic cosine similarity search.

        Args:
            query_embedding: The embedded query vector.
            top_k: Number of results to return.
            document_ids: Optional filter by specific document IDs.

        Returns:
            ChromaDB query result dict with ids, distances, documents, metadatas.
        """
        where_filter: dict[str, Any] | None = None
        if document_ids:
            if len(document_ids) == 1:
                where_filter = {"document_id": document_ids[0]}
            else:
                where_filter = {"document_id": {"$in": document_ids}}

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

    def search_mmr(
        self,
        query_embedding: list[float],
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Max Marginal Relevance search for diverse results.

        Uses the MMR formula:
            score = lambda * sim(query, doc) - (1-lambda) * max_sim(doc, selected)

        Args:
            query_embedding: The embedded query vector.
            fetch_k: Initial pool size for MMR.
            lambda_mult: Relevance-diversity tradeoff (0=diverse, 1=relevant).
            top_k: Final number of results.
            document_ids: Optional filter by specific document IDs.

        Returns:
            List of result dicts with id, document, metadata, distance.
        """
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()
        vectorstore = Chroma(
            client=self._client,
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model,
            ),
        )

        filter_dict: dict[str, Any] | None = None
        if document_ids:
            if len(document_ids) == 1:
                filter_dict = {"document_id": document_ids[0]}
            else:
                filter_dict = {"document_id": {"$in": document_ids}}

        docs = vectorstore.max_marginal_relevance_search_by_vector(
            embedding=query_embedding,
            k=top_k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=filter_dict,
        )

        results: list[dict[str, Any]] = []
        for i, doc in enumerate(docs):
            results.append({
                "id": doc.metadata.get("chunk_id", f"mmr_{i}"),
                "document": doc.page_content,
                "metadata": doc.metadata,
                "distance": 1.0 - (doc.metadata.get("similarity", 0.5)),
            })
        return results

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document.

        Returns:
            Number of chunks deleted.
        """
        results = self.collection.get(where={"document_id": document_id})
        count = len(results["ids"]) if results["ids"] else 0
        if count > 0:
            self.collection.delete(where={"document_id": document_id})
            logger.info("Deleted %d chunks for document %s", count, document_id)
        return count

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dict with count and embedding dimension.
        """
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": CHROMA_COLLECTION_NAME,
            "distance_metric": CHROMA_DISTANCE_METRIC,
        }

    def get_by_document(self, document_id: str) -> dict[str, Any]:
        """Retrieve all chunks for a document."""
        return self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )

    def heartbeat(self) -> bool:
        """Check ChromaDB connectivity."""
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False
