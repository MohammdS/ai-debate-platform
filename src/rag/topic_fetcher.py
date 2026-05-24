from __future__ import annotations

import logging

from langchain_core.documents import Document

from src.tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)

_QUERY_TEMPLATES = [
    "{topic}",
    "{topic} facts evidence",
    "{topic} arguments",
    "{topic} statistics data",
]


async def fetch_topic_documents(
    topic: str,
    tool: WebSearchTool,
    num_queries: int = 4,
) -> list[Document]:
    """Search the web for *topic* and return results as LangChain Documents.

    Runs up to *num_queries* distinct DuckDuckGo searches, deduplicates by URL,
    and converts each result into a Document whose page_content is
    ``"{title}\\n\\n{snippet}"`` and whose metadata carries ``source`` (URL)
    and ``title``.  Returns an empty list gracefully on total failure.
    """
    templates = _QUERY_TEMPLATES[:num_queries]
    seen: dict[str, Document] = {}   # keyed on URL for deduplication

    for template in templates:
        query = template.format(topic=topic)
        try:
            results = await tool.search(query)
        except Exception as exc:
            logger.warning("Web search failed for query '%s': %s", query, exc)
            continue

        for result in results:
            url = result.url or ""
            if not url or url in seen:
                continue
            content = f"{result.title}\n\n{result.snippet}"
            seen[url] = Document(
                page_content=content,
                metadata={"source": url, "title": result.title},
            )

    docs = list(seen.values())
    logger.info(
        "fetch_topic_documents: %d unique doc(s) from %d queries for '%s'",
        len(docs), len(templates), topic,
    )
    return docs
