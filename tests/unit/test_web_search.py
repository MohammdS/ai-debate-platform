from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.web_search import SearchResult, WebSearchTool

# --- SearchResult ---

def test_search_result_str():
    r = SearchResult(title="Title", url="https://example.com", snippet="Some snippet.")
    assert "Title" in str(r)
    assert "https://example.com" in str(r)
    assert "Some snippet" in str(r)


# --- format_for_prompt ---

def test_format_for_prompt_empty():
    tool = WebSearchTool()
    assert tool.format_for_prompt([]) == ""


def test_format_for_prompt_with_results():
    tool = WebSearchTool()
    results = [
        SearchResult("A", "https://a.com", "snippet a"),
        SearchResult("B", "https://b.com", "snippet b"),
    ]
    text = tool.format_for_prompt(results)
    assert "[Web sources" in text
    assert "https://a.com" in text
    assert "https://b.com" in text


# --- search() happy path ---

@pytest.mark.asyncio
async def test_search_returns_results():
    tool = WebSearchTool(max_results=2)
    with patch.object(tool, "_sync_search", return_value=[
        SearchResult("T1", "https://t1.com", "body1"),
        SearchResult("T2", "https://t2.com", "body2"),
    ]):
        results = await tool.search("AI debate")

    assert len(results) == 2
    assert results[0].title == "T1"


# --- search() timeout — returns empty list ---

@pytest.mark.asyncio
async def test_search_timeout_returns_empty():
    tool = WebSearchTool(timeout=0.001)

    with patch.object(tool, "_sync_search", side_effect=lambda q: __import__("time").sleep(1)):
        results = await tool.search("slow query")

    assert results == []


# --- search() network error — returns empty list ---

@pytest.mark.asyncio
async def test_search_error_returns_empty():
    tool = WebSearchTool()

    with patch.object(tool, "_sync_search", side_effect=RuntimeError("network down")):
        results = await tool.search("any query")

    assert results == []


# --- debater uses search in get_argument ---

@pytest.mark.asyncio
async def test_debater_injects_citations_on_even_rounds():
    from src.services.debater import Debater

    mock_client = MagicMock()
    mock_client.generate_response = AsyncMock(return_value="My argument")

    mock_gk = MagicMock()
    mock_gk.execute = AsyncMock(return_value="My argument")

    mock_search = MagicMock()
    mock_search.search = AsyncMock(return_value=[
        SearchResult("Src", "https://src.com", "evidence here")
    ])
    mock_search.format_for_prompt = MagicMock(return_value="[Web sources found:]\n  1. evidence")

    debater = Debater("A", "AI is good", "AI topic", mock_client, mock_gk, search_tool=mock_search)
    # Use round_num=2 — search runs on even rounds > 0
    result = await debater.get_argument([], round_num=2)

    mock_search.search.assert_called_once()
    core = result.split("\n\n[Skills:")[0]
    assert core == "My argument"


@pytest.mark.asyncio
async def test_debater_searches_on_every_nonzero_round():
    """Search is now run on every round > 0 (not just even rounds)."""
    from src.services.debater import Debater

    mock_client = MagicMock()
    mock_gk = MagicMock()
    mock_gk.execute = AsyncMock(return_value="argument")

    mock_search = MagicMock()
    mock_search.search = AsyncMock(return_value=[])
    mock_search.format_for_prompt = MagicMock(return_value="")

    debater = Debater("B", "AI is bad", "AI topic", mock_client, mock_gk, search_tool=mock_search)
    await debater.get_argument([], round_num=1)

    mock_search.search.assert_called_once()


@pytest.mark.asyncio
async def test_debater_skips_search_on_round_zero():
    """Round 0 = first synthetic message — no search is performed."""
    from src.services.debater import Debater

    mock_client = MagicMock()
    mock_gk = MagicMock()
    mock_gk.execute = AsyncMock(return_value="argument")

    mock_search = MagicMock()
    mock_search.search = AsyncMock(return_value=[])

    debater = Debater("B", "AI is bad", "AI topic", mock_client, mock_gk, search_tool=mock_search)
    await debater.get_argument([], round_num=0)

    mock_search.search.assert_not_called()
