from __future__ import annotations

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover
    from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Force cosine similarity so relevance scores are always in [0, 1].
# Without this Chroma defaults to L2 (Euclidean) distance and the
# relevance-score conversion produces negative values.
_COLLECTION_METADATA = {"hnsw:space": "cosine"}


def _get_embeddings(model_name: str = _DEFAULT_MODEL) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


def build_index(
    chunks: list[Document],
    persist_dir: str = ".chroma_db",
    collection_name: str = "debate_knowledge",
    model_name: str = _DEFAULT_MODEL,
) -> Chroma:
    """Embed *chunks* and persist a new Chroma vector store (cosine space)."""
    embeddings = _get_embeddings(model_name)
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name,
        collection_metadata=_COLLECTION_METADATA,
    )
    logger.info("Built Chroma index: %d chunk(s) at '%s'", len(chunks), persist_dir)
    return store


def load_index(
    persist_dir: str = ".chroma_db",
    collection_name: str = "debate_knowledge",
    model_name: str = _DEFAULT_MODEL,
) -> Chroma | None:
    """Load an existing Chroma store; returns None if absent, empty, or stale."""
    if not Path(persist_dir).exists():
        return None
    embeddings = _get_embeddings(model_name)
    store = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=collection_name,
        collection_metadata=_COLLECTION_METADATA,
    )
    # Guard: empty index (leftover from a failed build)
    try:
        count = store._collection.count()
        if count == 0:
            logger.warning("Chroma index at '%s' is empty — will rebuild", persist_dir)
            return None
    except Exception as exc:
        logger.warning("Could not verify index size at '%s': %s", persist_dir, exc)

    # Guard: L2-distance index built before the cosine fix.
    # If scores from a quick probe are all negative the index uses the old
    # L2 metric and must be rebuilt so relevance scores are valid.
    try:
        probe = store.similarity_search_with_relevance_scores("test", k=1)
        if probe and probe[0][1] < 0:
            logger.warning(
                "Chroma index at '%s' uses L2 distance (score=%.3f) — "
                "rebuilding with cosine similarity",
                persist_dir, probe[0][1],
            )
            return None
    except Exception:
        pass

    logger.info("Loaded Chroma index from '%s'", persist_dir)
    return store
