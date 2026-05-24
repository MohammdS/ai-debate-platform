from __future__ import annotations

import logging

from langchain_chroma import Chroma

from src.rag.models import RetrievedChunk

logger = logging.getLogger(__name__)

_DEFAULT_MIN_SCORE = 0.30   # discard chunks below this cosine-similarity threshold


class RAGRetriever:
    """Wraps a Chroma store and returns typed RetrievedChunk objects."""

    def __init__(self, store: Chroma, top_k: int = 3,
                 min_score: float = _DEFAULT_MIN_SCORE) -> None:
        self._store     = store
        self.top_k      = top_k
        self.min_score  = min_score

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Return up to *top_k* passages most relevant to *query*.

        Chunks whose relevance score is below *min_score* are discarded so
        that off-topic passages are never injected into the debater prompt.
        """
        try:
            results = self._store.similarity_search_with_relevance_scores(
                query, k=self.top_k
            )
        except Exception as exc:
            logger.warning("Retrieval failed for query '%.60s': %s", query, exc)
            return []

        chunks: list[RetrievedChunk] = []
        for doc, score in results:
            if score < self.min_score:
                logger.debug("Discarding low-score chunk (%.3f < %.3f): %.40s…",
                             score, self.min_score, doc.page_content)
                continue
            source = doc.metadata.get("source", "unknown")
            chunks.append(
                RetrievedChunk(
                    content=doc.page_content,
                    source=source,
                    score=float(score),
                    metadata=dict(doc.metadata),
                )
            )
        logger.debug("Retrieved %d/%d chunk(s) above threshold for: %.60s…",
                     len(chunks), len(results), query)
        return chunks
