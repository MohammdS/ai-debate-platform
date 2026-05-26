"""Tests for src/skills/skill_registry.py — build_skill_pool."""
import logging

from src.skills.skill_registry import SKILL_REGISTRY, build_skill_pool


class TestBuildSkillPool:
    def test_known_names_return_instances(self):
        pool = build_skill_pool(["RebuttalSkill", "EvidenceSkill"])
        assert len(pool) == 2
        names = {s.name for s in pool}
        assert "rebuttal" in names
        assert "evidence" in names

    def test_all_registered_skills_instantiate(self):
        """Every entry in SKILL_REGISTRY can be resolved without error."""
        pool = build_skill_pool(list(SKILL_REGISTRY.keys()))
        assert len(pool) == len(SKILL_REGISTRY)

    def test_unknown_name_is_skipped_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="src.skills.skill_registry"):
            pool = build_skill_pool(["RebuttalSkill", "NonExistentSkillXYZ"])
        assert len(pool) == 1
        assert any("NonExistentSkillXYZ" in r.message for r in caplog.records)

    def test_empty_list_returns_empty_pool_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="src.skills.skill_registry"):
            pool = build_skill_pool([])
        assert pool == []
        assert any("empty" in r.message for r in caplog.records)

    def test_all_unknown_names_returns_empty_pool_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="src.skills.skill_registry"):
            pool = build_skill_pool(["FakeSkillA", "FakeSkillB"])
        assert pool == []
        # Should warn once per unknown skill + once for empty pool
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) >= 3

    def test_order_is_preserved(self):
        names = ["CitationSkill", "RebuttalSkill", "ProgressionSkill"]
        pool = build_skill_pool(names)
        assert [s.name for s in pool] == ["citation", "rebuttal", "progression"]

    def test_duplicate_names_produce_duplicate_instances(self):
        """Each entry creates a fresh instance — no singleton caching."""
        pool = build_skill_pool(["RebuttalSkill", "RebuttalSkill"])
        assert len(pool) == 2
        assert pool[0] is not pool[1]
