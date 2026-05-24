from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_SUPPORTED = {".txt", ".md"}


def load_documents(knowledge_dir: str = "knowledge") -> list[Document]:
    """Load all .txt/.md files from *knowledge_dir* recursively.

    Uses plain file I/O rather than langchain-community loaders to avoid
    the deprecation warning for that package.
    """
    docs: list[Document] = []
    folder = Path(knowledge_dir)
    if not folder.exists():
        logger.warning("knowledge_dir '%s' does not exist — skipping", knowledge_dir)
        return docs
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in _SUPPORTED or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
            doc = Document(
                page_content=content,
                metadata={"source": path.name},
            )
            docs.append(doc)
            logger.debug("Loaded '%s'", path.name)
        except Exception as exc:
            logger.warning("Failed to load '%s': %s", path.name, exc)
    logger.info("Loaded %d document(s) from '%s'", len(docs), knowledge_dir)
    return docs
