from __future__ import annotations

import logging

from src.rag.document_loader import load_documents
from src.rag.models import RAGConfig, RetrievedChunk
from src.rag.retriever import RAGRetriever
from src.rag.splitter import split_documents
from src.rag.vector_store import build_index, load_index

logger = logging.getLogger(__name__)


class RAGService:
    """Facade: initialise once per debate session, query per argument turn."""

    def __init__(self, config: RAGConfig | None = None) -> None:
        self._config = config or RAGConfig()
        self._retriever: RAGRetriever | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True after a successful initialise()."""
        return self._retriever is not None

    def initialise(self, rebuild: bool = False) -> bool:
        """Build or load the vector index.  Returns False if no docs found."""
        cfg = self._config
        store = None if rebuild else load_index(
            cfg.vector_db_path, cfg.collection_name, cfg.embedding_model
        )
        if store is None:
            docs = load_documents(cfg.knowledge_dir)
            if not docs:
                logger.warning("RAG: no documents found in '%s' — disabling", cfg.knowledge_dir)
                return False
            chunks = split_documents(docs, cfg.chunk_size, cfg.chunk_overlap)
            store = build_index(
                chunks, cfg.vector_db_path, cfg.collection_name, cfg.embedding_model
            )
        self._retriever = RAGRetriever(store, cfg.top_k)
        logger.info("RAGService ready (top_k=%d)", cfg.top_k)
        return True

    def build_query(
        self,
        topic: str,
        stance: str,
        opponent_claim: str = "",
        summary: str = "",
    ) -> str:
        """Combine debate context into a single retrieval query string."""
        parts = [topic, stance]
        if opponent_claim:
            parts.append(opponent_claim[:200])
        if summary:
            parts.append(summary[:200])
        return " | ".join(parts)

    async def initialise_from_web(self, topic: str, rebuild: bool = False) -> bool:
        """Fallback: fetch knowledge via web search and build a topic-specific index.

        Uses four DuckDuckGo queries to gather facts, evidence, arguments, and
        statistics about *topic*.  The vector store is persisted at a slug-based
        path so different topics never overwrite each other's index.

        Returns True on success, False if no web results were found.
        """
        import re

        from src.rag.topic_fetcher import fetch_topic_documents
        from src.tools.web_search import WebSearchTool

        cfg  = self._config
        slug = re.sub(r"[^\w\-]", "_", topic.lower())[:50]
        web_db_path = f"{cfg.vector_db_path}_{slug}"

        store = None if rebuild else load_index(
            web_db_path, cfg.collection_name, cfg.embedding_model
        )
        if store is None:
            docs = await fetch_topic_documents(topic, WebSearchTool())
            if not docs:
                logger.warning("RAG web fallback: no results found for '%s'", topic)
                return False
            chunks = split_documents(docs, cfg.chunk_size, cfg.chunk_overlap)
            store  = build_index(chunks, web_db_path, cfg.collection_name, cfg.embedding_model)

        self._retriever = RAGRetriever(store, cfg.top_k)
        logger.info("RAGService ready via web fallback (top_k=%d)", cfg.top_k)
        return True

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Return relevant chunks, or [] if not ready."""
        if self._retriever is None:
            return []
        return self._retriever.retrieve(query)
