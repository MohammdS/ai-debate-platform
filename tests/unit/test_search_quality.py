"""Tests for search_quality — domain scoring and query building."""

from src.tools.search_quality import build_queries, is_blocked, score_domain


class TestDomainScoring:
    def test_edu_domain_scores_tier3(self):
        assert score_domain("https://www.mit.edu/research/ai") == 3

    def test_gov_domain_scores_tier3(self):
        assert score_domain("https://www.who.int/report") == 3

    def test_pubmed_scores_tier3(self):
        assert score_domain("https://pubmed.ncbi.nlm.nih.gov/12345") == 3

    def test_reuters_scores_tier2(self):
        assert score_domain("https://www.reuters.com/tech/ai") == 2

    def test_arxiv_scores_tier2(self):
        assert score_domain("https://arxiv.org/abs/2401.00001") == 2

    def test_unknown_site_scores_tier1(self):
        assert score_domain("https://www.randomsite123.com/article") == 1

    def test_reddit_is_blocked(self):
        assert score_domain("https://www.reddit.com/r/science") == 0

    def test_quora_is_blocked(self):
        assert score_domain("https://www.quora.com/What-is-AI") == 0

    def test_youtube_is_blocked(self):
        assert score_domain("https://www.youtube.com/watch?v=abc") == 0

    def test_is_blocked_convenience(self):
        assert is_blocked("https://www.reddit.com/r/anything") is True
        assert is_blocked("https://www.bbc.com/news") is False


class TestQueryBuilding:
    def test_always_returns_at_least_one_query(self):
        queries = build_queries("AI in education", "AI helps students", round_num=1)
        assert len(queries) >= 1

    def test_early_round_includes_statistics_query(self):
        queries = build_queries("climate change", "renewables work", round_num=1)
        assert any("statistics" in q or "data" in q for q in queries)

    def test_mid_round_includes_limitations_query(self):
        queries = build_queries("nuclear energy", "nuclear is safe", round_num=4)
        assert any("limitations" in q or "criticism" in q for q in queries)

    def test_late_round_includes_consensus_query(self):
        queries = build_queries("vaccine efficacy", "vaccines save lives", round_num=7)
        assert any("consensus" in q or "systematic" in q for q in queries)

    def test_long_topic_truncated(self):
        long_topic = "A" * 200
        queries = build_queries(long_topic, "some stance", round_num=2)
        # Queries should not be absurdly long
        assert all(len(q) < 300 for q in queries)

    def test_query_contains_topic_and_stance(self):
        queries = build_queries("AI in schools", "AI is beneficial", round_num=1)
        combined = " ".join(queries).lower()
        assert "ai in schools" in combined
        assert "ai is beneficial" in combined
