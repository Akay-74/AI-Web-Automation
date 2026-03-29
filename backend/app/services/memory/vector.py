"""Vector Memory — FAISS-based embedding storage for agent context.

Stores embeddings of visited pages and extracted data.
Enables the agent to recall previously visited content without re-browsing.
"""

import hashlib
from typing import Optional
import numpy as np
from openai import AsyncOpenAI
import structlog

from app.config import get_settings

logger = structlog.get_logger()

# Lazy import — FAISS may not be installed in all environments
_faiss = None


def _get_faiss():
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            logger.warning("FAISS not installed. Vector memory disabled.")
            return None
    return _faiss


class VectorMemory:
    """FAISS-based vector memory for storing and retrieving page embeddings."""

    EMBEDDING_DIM = 1536  # text-embedding-3-small dimension

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.documents: list[dict] = []
        self._seen_hashes: set[str] = set()

        faiss = _get_faiss()
        if faiss:
            self.index = faiss.IndexFlatIP(self.EMBEDDING_DIM)  # Cosine similarity
        else:
            self.index = None

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        self.embedding_model = settings.openai_embedding_model

    def _content_hash(self, content: str) -> str:
        """Generate a hash for deduplication."""
        return hashlib.sha256(content[:2000].encode()).hexdigest()[:16]

    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding from OpenAI API."""
        # Truncate to save tokens
        text = text[:8000]
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return np.array(response.data[0].embedding, dtype="float32")

    async def store(self, content: str, metadata: Optional[dict] = None):
        """Store a page or data snippet in vector memory."""
        if not self.index:
            # Fallback: just store in list
            self.documents.append({"content": content[:5000], "metadata": metadata or {}})
            return

        # Dedup by content hash
        content_hash = self._content_hash(content)
        if content_hash in self._seen_hashes:
            logger.debug("Duplicate content skipped", hash=content_hash)
            return
        self._seen_hashes.add(content_hash)

        embedding = await self._get_embedding(content)
        # Normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        self.index.add(np.array([embedding]))
        self.documents.append({
            "content": content[:5000],
            "metadata": metadata or {},
            "hash": content_hash,
        })
        logger.info("Stored in memory", docs_count=len(self.documents))

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """Retrieve the most relevant stored documents for a query."""
        if not self.index or self.index.ntotal == 0:
            # Fallback: return last N documents
            return self.documents[-top_k:]

        query_emb = await self._get_embedding(query)
        norm = np.linalg.norm(query_emb)
        if norm > 0:
            query_emb = query_emb / norm

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(np.array([query_emb]), k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(scores[0][i])
                results.append(doc)

        return results

    def get_context_summary(self, max_chars: int = 3000) -> str:
        """Create a text summary of all stored memory for replanning context."""
        if not self.documents:
            return "No pages visited yet."

        parts = []
        for i, doc in enumerate(self.documents):
            meta = doc.get("metadata", {})
            url = meta.get("url", "unknown page")
            parts.append(f"Page {i + 1} ({url}): {doc['content'][:500]}")

        return "\n---\n".join(parts)[:max_chars]
