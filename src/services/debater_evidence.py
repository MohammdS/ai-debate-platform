from __future__ import annotations


async def add_web_evidence(
    *,
    topic: str,
    stance: str,
    round_num: int,
    client,
    search_tool,
    memory,
    logger,
    debater_name: str,
    history: list[dict],
) -> tuple[list[dict], bool, list[dict[str, str]]]:
    """Prepend web evidence to the active turn when the provider supports it."""
    enriched_history = list(history)
    if round_num <= 0 or not client.supports_web_search:
        return enriched_history, False, []

    try:
        results = await search_tool.search(
            f"{topic} {stance} evidence",
            topic=topic,
            stance=stance,
            round_num=round_num,
            seen_urls=memory.used_urls,
        )
        sources = [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]
        if results:
            memory.register_urls([r.url for r in results])
        citation_text = search_tool.format_for_prompt(results)
        if citation_text:
            enriched_history = [{"role": "user", "content": citation_text}] + enriched_history
            return enriched_history, True, sources
        return enriched_history, False, sources
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] web search failed (round %d): %s", debater_name, round_num, exc)
        return enriched_history, False, []
