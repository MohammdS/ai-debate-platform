"""Tests for the RAG pipeline: loading, splitting, indexing, retrieval, skills."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.models import RAGConfig, RetrievedChunk
from src.rag.rag_service import RAGService
from src.rag.retriever import RAGRetriever
from src.rag.splitter import split_documents
from src.skills.models import SkillContext
from src.skills.retriever_skill import RetrieverSkill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_doc(content: str, source: str = "test.md"):
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = {"source": source}
    return doc


# ---------------------------------------------------------------------------
# RAGConfig
# ---------------------------------------------------------------------------

def test_rag_config_defaults():
    cfg = RAGConfig()
    assert cfg.knowledge_dir == "knowledge"
    assert cfg.top_k == 3
    assert "MiniLM" in cfg.embedding_model


def test_rag_config_custom():
    cfg = RAGConfig(knowledge_dir="docs", top_k=5, chunk_size=300)
    assert cfg.knowledge_dir == "docs"
    assert cfg.top_k == 5
    assert cfg.chunk_size == 300


# ---------------------------------------------------------------------------
# document_loader  (no longer uses TextLoader — uses plain file I/O)
# ---------------------------------------------------------------------------

def test_load_documents_missing_dir(tmp_path):
    from src.rag.document_loader import load_documents
    result = load_documents(str(tmp_path / "nonexistent"))
    assert result == []


def test_load_documents_returns_docs(tmp_path):
    (tmp_path / "test.md").write_text("# Hello\nSome content here.")
    from src.rag.document_loader import load_documents
    result = load_documents(str(tmp_path))
    assert len(result) == 1
    assert "Hello" in result[0].page_content
    assert result[0].metadata["source"] == "test.md"


def test_load_documents_skips_unsupported(tmp_path):
    (tmp_path / "data.csv").write_text("a,b,c")
    from src.rag.document_loader import load_documents
    result = load_documents(str(tmp_path))
    assert result == []


def test_load_documents_handles_read_error(tmp_path):
    (tmp_path / "broken.txt").write_text("ok")
    with patch("src.rag.document_loader.Path.read_text", side_effect=OSError("perm")):
        from src.rag.document_loader import load_documents
        result = load_documents(str(tmp_path))
    assert result == []


def test_load_documents_loads_txt_and_md(tmp_path):
    (tmp_path / "a.txt").write_text("text file")
    (tmp_path / "b.md").write_text("# md file")
    from src.rag.document_loader import load_documents
    docs = load_documents(str(tmp_path))
    sources = {d.metadata["source"] for d in docs}
    assert "a.txt" in sources
    assert "b.md" in sources


# ---------------------------------------------------------------------------
# splitter
# ---------------------------------------------------------------------------

def test_split_empty_list():
    assert split_documents([]) == []


def test_split_documents_produces_chunks():
    doc = _fake_doc("word " * 300, "big.md")
    doc.metadata = {"source": "big.md"}
    with patch("src.rag.splitter.RecursiveCharacterTextSplitter") as mock_split:
        chunk = _fake_doc("word " * 100, "big.md")
        mock_split.return_value.split_documents.return_value = [chunk, chunk, chunk]
        chunks = split_documents([doc], chunk_size=200, chunk_overlap=20)
    assert len(chunks) == 3


# ---------------------------------------------------------------------------
# vector_store
# ---------------------------------------------------------------------------

def test_load_index_returns_none_when_dir_absent(tmp_path):
    from src.rag.vector_store import load_index
    result = load_index(persist_dir=str(tmp_path / "no_db"))
    assert result is None


def test_build_index_calls_chroma(tmp_path):
    mock_store = MagicMock()
    doc = _fake_doc("some content")
    with (
        patch("src.rag.vector_store._get_embeddings", return_value=MagicMock()),
        patch("src.rag.vector_store.Chroma") as mock_chroma,
    ):
        mock_chroma.from_documents.return_value = mock_store
        from src.rag.vector_store import build_index
        result = build_index([doc], persist_dir=str(tmp_path / "db"))
    assert result is mock_store


def test_build_index_uses_cosine_collection_metadata(tmp_path):
    """build_index must pass hnsw:space=cosine to avoid negative scores."""
    mock_store = MagicMock()
    doc = _fake_doc("content")
    with (
        patch("src.rag.vector_store._get_embeddings", return_value=MagicMock()),
        patch("src.rag.vector_store.Chroma") as mock_chroma,
    ):
        mock_chroma.from_documents.return_value = mock_store
        from src.rag.vector_store import build_index
        build_index([doc], persist_dir=str(tmp_path / "db"))
    call_kwargs = mock_chroma.from_documents.call_args[1]
    assert call_kwargs.get("collection_metadata", {}).get("hnsw:space") == "cosine"


def _good_store(score: float = 0.75) -> MagicMock:
    """Helper: mock store with non-empty collection and positive probe score."""
    store = MagicMock()
    store._collection.count.return_value = 5
    fake_doc = MagicMock()
    fake_doc.page_content = "text"
    fake_doc.metadata = {"source": "test.md"}
    store.similarity_search_with_relevance_scores.return_value = [(fake_doc, score)]
    return store


def test_load_index_returns_store_when_dir_exists(tmp_path):
    db_path = tmp_path / "db"
    db_path.mkdir()
    mock_store = _good_store(score=0.75)
    with (
        patch("src.rag.vector_store._get_embeddings", return_value=MagicMock()),
        patch("src.rag.vector_store.Chroma", return_value=mock_store),
    ):
        from src.rag.vector_store import load_index
        result = load_index(persist_dir=str(db_path))
    assert result is mock_store


def test_load_index_returns_none_when_index_is_empty(tmp_path):
    """An existing but empty Chroma DB should return None so it gets rebuilt."""
    db_path = tmp_path / "db"
    db_path.mkdir()
    mock_store = MagicMock()
    mock_store._collection.count.return_value = 0   # empty
    with (
        patch("src.rag.vector_store._get_embeddings", return_value=MagicMock()),
        patch("src.rag.vector_store.Chroma", return_value=mock_store),
    ):
        from src.rag.vector_store import load_index
        result = load_index(persist_dir=str(db_path))
    assert result is None


def test_load_index_returns_none_for_stale_l2_index(tmp_path):
    """An index with negative probe score (L2 distance) must trigger a rebuild."""
    db_path = tmp_path / "db"
    db_path.mkdir()
    mock_store = _good_store(score=-0.26)   # negative → old L2 index
    with (
        patch("src.rag.vector_store._get_embeddings", return_value=MagicMock()),
        patch("src.rag.vector_store.Chroma", return_value=mock_store),
    ):
        from src.rag.vector_store import load_index
        result = load_index(persist_dir=str(db_path))
    assert result is None


# ---------------------------------------------------------------------------
# RAGRetriever
# ---------------------------------------------------------------------------

def test_retriever_returns_chunks():
    mock_store = MagicMock()
    doc = _fake_doc("AI is powerful", "ai.md")
    mock_store.similarity_search_with_relevance_scores.return_value = [(doc, 0.85)]
    retriever = RAGRetriever(mock_store, top_k=3)
    results = retriever.retrieve("AI risks")
    assert len(results) == 1
    assert results[0].source == "ai.md"
    assert results[0].score == pytest.approx(0.85)


def test_retriever_returns_empty_on_store_error():
    mock_store = MagicMock()
    mock_store.similarity_search_with_relevance_scores.side_effect = RuntimeError("db error")
    retriever = RAGRetriever(mock_store, top_k=3)
    results = retriever.retrieve("query")
    assert results == []


def test_retriever_respects_top_k():
    mock_store = MagicMock()
    docs = [(_fake_doc(f"text {i}", f"doc{i}.md"), 0.9 - i * 0.1) for i in range(5)]
    mock_store.similarity_search_with_relevance_scores.return_value = docs[:2]
    retriever = RAGRetriever(mock_store, top_k=2)
    retriever.retrieve("query")
    mock_store.similarity_search_with_relevance_scores.assert_called_once_with("query", k=2)


def test_retriever_filters_low_score_chunks():
    """Chunks below min_score must be discarded."""
    mock_store = MagicMock()
    doc_high = _fake_doc("relevant content", "good.md")
    doc_low  = _fake_doc("irrelevant noise", "bad.md")
    mock_store.similarity_search_with_relevance_scores.return_value = [
        (doc_high, 0.75),
        (doc_low,  0.10),   # below default 0.30 threshold
    ]
    retriever = RAGRetriever(mock_store, top_k=3)
    results = retriever.retrieve("query")
    assert len(results) == 1
    assert results[0].source == "good.md"


def test_retriever_custom_min_score():
    """A custom min_score threshold should be respected."""
    mock_store = MagicMock()
    doc = _fake_doc("content", "doc.md")
    mock_store.similarity_search_with_relevance_scores.return_value = [(doc, 0.45)]
    # Default threshold 0.30 → included
    r1 = RAGRetriever(mock_store, top_k=1).retrieve("q")
    assert len(r1) == 1
    # Raised threshold 0.50 → excluded
    r2 = RAGRetriever(mock_store, top_k=1, min_score=0.50).retrieve("q")
    assert len(r2) == 0


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------

def test_rag_service_not_ready_initially():
    svc = RAGService()
    assert not svc.is_ready()


def test_rag_service_build_query():
    svc = RAGService()
    q = svc.build_query("AI safety", "AI is risky", "But AI also helps", "summary")
    assert "AI safety" in q
    assert "AI is risky" in q
    assert "But AI also helps" in q


def test_rag_service_build_query_minimal():
    svc = RAGService()
    q = svc.build_query("climate", "it is real")
    assert "climate" in q
    assert " | " in q


def test_rag_service_retrieve_returns_empty_when_not_ready():
    svc = RAGService()
    assert svc.retrieve("anything") == []


def test_rag_service_initialise_false_when_no_docs():
    svc = RAGService(RAGConfig(knowledge_dir="/nonexistent/path"))
    with (
        patch("src.rag.rag_service.load_documents", return_value=[]),
        patch("src.rag.rag_service.load_index", return_value=None),
    ):
        result = svc.initialise()
    assert result is False
    assert not svc.is_ready()


def test_rag_service_initialise_true_with_docs():
    mock_store = MagicMock()
    fake_doc = _fake_doc("knowledge text")
    svc = RAGService(RAGConfig(knowledge_dir="knowledge"))
    with (
        patch("src.rag.rag_service.load_index", return_value=None),
        patch("src.rag.rag_service.load_documents", return_value=[fake_doc]),
        patch("src.rag.rag_service.split_documents", return_value=[fake_doc]),
        patch("src.rag.rag_service.build_index", return_value=mock_store),
    ):
        result = svc.initialise()
    assert result is True
    assert svc.is_ready()


def test_rag_service_initialise_loads_existing_index():
    mock_store = MagicMock()
    svc = RAGService()
    with patch("src.rag.rag_service.load_index", return_value=mock_store):
        result = svc.initialise(rebuild=False)
    assert result is True
    assert svc.is_ready()


def test_rag_service_rebuild_ignores_existing_index():
    mock_store = MagicMock()
    fake_doc = _fake_doc("text")
    svc = RAGService()
    with (
        patch("src.rag.rag_service.load_index") as mock_load,
        patch("src.rag.rag_service.load_documents", return_value=[fake_doc]),
        patch("src.rag.rag_service.split_documents", return_value=[fake_doc]),
        patch("src.rag.rag_service.build_index", return_value=mock_store),
    ):
        result = svc.initialise(rebuild=True)
    mock_load.assert_not_called()
    assert result is True


# ---------------------------------------------------------------------------
# RetrieverSkill
# ---------------------------------------------------------------------------

def _ctx(**kwargs) -> SkillContext:
    defaults = {
        "topic": "AI", "stance": "pro", "opponent_last_message": "",
        "round_num": 1, "skill_type": "evidence_based", "transcript": [],
    }
    defaults.update(kwargs)
    return SkillContext(**defaults)


def test_retriever_skill_not_ready_when_rag_not_ready():
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = False
    skill = RetrieverSkill(mock_rag)
    assert not skill.can_handle(_ctx())


def test_retriever_skill_ready_when_rag_ready():
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    skill = RetrieverSkill(mock_rag)
    assert skill.can_handle(_ctx())


def test_retriever_skill_returns_not_selected_on_empty():
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    mock_rag.build_query.return_value = "query"
    mock_rag.retrieve.return_value = []
    skill = RetrieverSkill(mock_rag)
    result = skill.run(_ctx())
    assert not result.selected
    assert result.content == ""


def test_retriever_skill_injects_evidence_block():
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    mock_rag.build_query.return_value = "query"
    mock_rag.retrieve.return_value = [
        RetrievedChunk(content="AI safety is critical.", source="ai_ethics.md", score=0.9),
        RetrievedChunk(content="97% scientists agree.", source="climate_change.md", score=0.8),
    ]
    skill = RetrieverSkill(mock_rag)
    result = skill.run(_ctx(opponent_last_message="AI is safe"))
    assert result.selected
    assert "[source: ai_ethics.md]" in result.content
    assert "[source: climate_change.md]" in result.content
    assert "cite" in result.content.lower()


def test_retriever_skill_uses_transcript_summary():
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    mock_rag.build_query.return_value = "q"
    mock_rag.retrieve.return_value = [
        RetrievedChunk(content="evidence", source="doc.md", score=0.7)
    ]
    transcript = [{"role": "user", "content": f"message {i}"} for i in range(6)]
    skill = RetrieverSkill(mock_rag)
    skill.run(_ctx(transcript=transcript))
    call_args = mock_rag.build_query.call_args
    assert call_args is not None
    summary_arg = call_args[0][3] if len(call_args[0]) > 3 else call_args[1].get("summary", "")
    assert len(summary_arg) > 0


# ---------------------------------------------------------------------------
# SkillSelector — selected flag is respected, not overridden
# ---------------------------------------------------------------------------

def test_skill_selector_respects_not_selected_from_run():
    """If a skill's run() returns selected=False, the selector must not override it."""
    from src.skills.skill_selector import SkillSelector

    class AlwaysHandlesNeverSelects(RetrieverSkill):
        def can_handle(self, ctx):
            return True
        def run(self, ctx):
            from src.skills.models import SkillResult
            return SkillResult("test_skill", False, "nothing useful", "")

    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    skill = AlwaysHandlesNeverSelects(mock_rag)
    selector = SkillSelector([skill])
    results = selector.select(_ctx())
    assert results[0].selected is False


# ---------------------------------------------------------------------------
# Normal mode — no RAG — still works
# ---------------------------------------------------------------------------

def test_normal_mode_debater_no_rag():
    """Debater without rag_service must initialise without error."""
    from src.services.debater import Debater
    debater = Debater("Pro", "yes", "AI topic", MagicMock(), MagicMock())
    assert debater._skill_selector is not None


def test_rag_mode_debater_registers_retriever_skill():
    """Debater with rag_service must include RetrieverSkill in the selector."""
    from src.services.debater import Debater
    mock_rag = MagicMock()
    mock_rag.is_ready.return_value = True
    debater = Debater("Pro", "yes", "AI topic", MagicMock(), MagicMock(), rag_service=mock_rag)
    skill_names = [s.name for s in debater._skill_selector._skills]
    assert "retriever" in skill_names


# ---------------------------------------------------------------------------
# topic_fetcher
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_topic_documents_returns_documents():
    from src.tools.web_search import SearchResult
    from src.rag.topic_fetcher import fetch_topic_documents

    mock_tool = MagicMock()
    mock_tool.search = AsyncMock(return_value=[
        SearchResult(title="AI safety overview", url="https://example.com/ai", snippet="AI safety is critical."),
        SearchResult(title="AI risks", url="https://example.com/risk", snippet="Several risks exist."),
    ])
    docs = await fetch_topic_documents("AI safety", mock_tool, num_queries=1)
    assert len(docs) == 2
    assert "AI safety overview" in docs[0].page_content
    assert docs[0].metadata["source"] == "https://example.com/ai"


@pytest.mark.asyncio
async def test_fetch_topic_documents_deduplicates_urls():
    from src.tools.web_search import SearchResult
    from src.rag.topic_fetcher import fetch_topic_documents

    same_result = SearchResult(title="Same", url="https://dup.com", snippet="dup")
    mock_tool = MagicMock()
    mock_tool.search = AsyncMock(return_value=[same_result])
    # 2 queries → same URL returned both times → only 1 document
    docs = await fetch_topic_documents("topic", mock_tool, num_queries=2)
    assert len(docs) == 1


@pytest.mark.asyncio
async def test_fetch_topic_documents_graceful_on_empty_search():
    from src.rag.topic_fetcher import fetch_topic_documents

    mock_tool = MagicMock()
    mock_tool.search = AsyncMock(return_value=[])
    docs = await fetch_topic_documents("unknown topic", mock_tool)
    assert docs == []


@pytest.mark.asyncio
async def test_rag_service_initialise_from_web_uses_fetched_docs():
    from langchain_core.documents import Document as LCDoc
    from src.rag.rag_service import RAGService

    fake_doc = LCDoc(page_content="web content", metadata={"source": "https://x.com"})
    mock_store = MagicMock()
    mock_store._collection.count.return_value = 1
    fake_probe = MagicMock()
    fake_probe.page_content = "web content"
    fake_probe.metadata = {"source": "https://x.com"}
    mock_store.similarity_search_with_relevance_scores.return_value = [(fake_probe, 0.8)]

    svc = RAGService()
    with (
        patch("src.rag.rag_service.load_index", return_value=None),
        patch("src.rag.topic_fetcher.fetch_topic_documents", new=AsyncMock(return_value=[fake_doc])),
        patch("src.rag.rag_service.split_documents", return_value=[fake_doc]),
        patch("src.rag.rag_service.build_index", return_value=mock_store),
    ):
        ok = await svc.initialise_from_web("AI safety", rebuild=True)
    assert ok is True
    assert svc.is_ready()


@pytest.mark.asyncio
async def test_rag_service_initialise_from_web_returns_false_on_no_results():
    from src.rag.rag_service import RAGService

    svc = RAGService()
    with (
        patch("src.rag.rag_service.load_index", return_value=None),
        patch("src.rag.topic_fetcher.fetch_topic_documents", new=AsyncMock(return_value=[])),
    ):
        ok = await svc.initialise_from_web("obscure topic", rebuild=True)
    assert ok is False
    assert not svc.is_ready()
