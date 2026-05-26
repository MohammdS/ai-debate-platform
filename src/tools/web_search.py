from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from ddgs import DDGS


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

    def __str__(self) -> str:
        return f"[{self.title}] {self.snippet} ({self.url})"


class WebSearchTool:
    """
    Async web search via DuckDuckGo — no API key required.
    Used by debaters to find real citations during argument generation.
    """

    def __init__(self, max_results: int = 3, timeout: float = 10.0):
        self.max_results = max_results
        self.timeout = timeout
        self._logger = logging.getLogger("web_search")

    async def search(self, query: str) -> list[SearchResult]:
        """
        Run a DuckDuckGo text search and return up to max_results results.
        Runs the blocking DDGS call in a thread pool to stay async-safe.
        Returns [] on any error so the debater can still proceed without citations.
        """
        self._logger.info("[web_search] query: %s", query)
        try:
            results = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._sync_search, query
                ),
                timeout=self.timeout,
            )
            self._logger.info("[web_search] got %d result(s)", len(results))
            return results
        except TimeoutError:
            self._logger.warning("[web_search] timed out for query: %s", query)
            return []
        except Exception as exc:
            self._logger.warning("[web_search] failed (%s): %s", type(exc).__name__, exc)
            return []

    def _sync_search(self, query: str) -> list[SearchResult]:
        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=self.max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
        return results

    def format_for_prompt(self, results: list[SearchResult]) -> str:
        """Format results as a compact string to inject into the LLM prompt."""
        if not results:
            return ""
        lines = ["[Web sources found:]"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r}")
        return "\n".join(lines)
