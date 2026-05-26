from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from ddgs import DDGS

from src.tools.search_quality import build_queries, is_blocked, score_domain


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    domain_tier: int = field(default=1)

    def __str__(self) -> str:
        tier_label = {3: "★★★", 2: "★★", 1: "★"}.get(self.domain_tier, "")
        return f"{tier_label}[{self.title}] {self.snippet} ({self.url})"


class WebSearchTool:
    """
    Async web search via DuckDuckGo with quality filtering and deduplication.

    Improvements over the naive approach:
      - Multiple targeted queries (evidence / stats / expert, by round)
      - Domain-tier scoring — blocked domains discarded, tier shown in prompt
      - URL deduplication — skip already-used URLs passed in `seen_urls`
      - Results sorted by tier (highest quality first)
    """

    def __init__(self, max_results: int = 4, timeout: float = 12.0):
        self.max_results = max_results
        self.timeout = timeout
        self._logger = logging.getLogger("web_search")

    async def search(
        self,
        query: str,
        *,
        topic: str = "",
        stance: str = "",
        round_num: int = 0,
        seen_urls: set[str] | None = None,
    ) -> list[SearchResult]:
        """Return filtered, deduplicated, quality-sorted results.

        If topic + stance are provided, multiple targeted queries are run and
        results are merged; otherwise only `query` is used.
        """
        seen = seen_urls or set()
        queries = build_queries(topic, stance, round_num) if topic else [query]

        # Run all queries concurrently
        per_query = await asyncio.gather(
            *[self._run_query(q, seen) for q in queries],
            return_exceptions=True,
        )

        merged: list[SearchResult] = []
        seen_in_run: set[str] = set()
        for batch in per_query:
            if isinstance(batch, Exception):
                self._logger.warning("[web_search] query failed: %s", batch)
                continue
            for r in batch:
                if r.url not in seen_in_run:
                    seen_in_run.add(r.url)
                    merged.append(r)

        # Sort by domain tier descending, then trim
        merged.sort(key=lambda r: r.domain_tier, reverse=True)
        result = merged[: self.max_results]
        self._logger.info(
            "[web_search] %d unique result(s), top tier: %s",
            len(result),
            result[0].domain_tier if result else "n/a",
        )
        return result

    async def _run_query(self, query: str, seen_urls: set[str]) -> list[SearchResult]:
        """Execute one DDG query with timeout; return filtered results."""
        self._logger.debug("[web_search] query: %s", query)
        try:
            return await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None, self._sync_search, query, seen_urls
                ),
                timeout=self.timeout,
            )
        except TimeoutError:
            self._logger.warning("[web_search] timed out: %s", query)
            return []
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("[web_search] error (%s): %s", type(exc).__name__, exc)
            return []

    def _sync_search(self, query: str, seen_urls: set[str]) -> list[SearchResult]:
        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=self.max_results + 4):
                url = r.get("href", "")
                if not url or url in seen_urls or is_blocked(url):
                    continue
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=url,
                    snippet=r.get("body", ""),
                    domain_tier=score_domain(url),
                ))
        return results

    def format_for_prompt(self, results: list[SearchResult]) -> str:
        """Format results as a compact LLM-ready string, tier label included."""
        if not results:
            return ""
        lines = ["[Web sources — use these to support your argument:]"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r}")
        return "\n".join(lines)
