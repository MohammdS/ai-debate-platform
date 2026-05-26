"""Tests for DebateMemory — compact debate state tracking."""
from src.services.debate_memory import DebateMemory


def test_record_pro_turn_adds_to_pro_claims():
    memory = DebateMemory()
    memory.record_turn("pro", "AI improves education by personalizing learning pathways.")
    assert len(memory.pro_claims) == 1
    assert "AI improves" in memory.pro_claims[0]


def test_record_contra_turn_adds_to_contra_claims():
    memory = DebateMemory()
    memory.record_turn("contra", "AI harms deep learning by providing easy answers.")
    assert len(memory.contra_claims) == 1


def test_repetition_detected_on_same_fingerprint():
    memory = DebateMemory()
    content = "AI improves education by personalizing learning pathways."
    memory.record_turn("pro", content)
    memory.record_turn("pro", content)  # Same content again
    assert memory.repetition_count() == 1


def test_no_repetition_for_different_content():
    memory = DebateMemory()
    memory.record_turn("pro", "AI personalizes learning for every student effectively.")
    memory.record_turn("pro", "Economic growth depends on technological innovation and research.")
    assert memory.repetition_count() == 0


def test_evidence_extraction_captures_percentages():
    memory = DebateMemory()
    memory.record_turn("pro", "Studies show 40% improvement in test scores with AI tutoring tools.")
    assert any("40" in e for e in memory.used_evidence)


def test_memory_block_contains_own_claims():
    memory = DebateMemory()
    memory.record_turn("pro", "AI improves education by personalizing learning.")
    block = memory.get_memory_block("pro")
    assert "YOUR PREVIOUS CLAIMS" in block


def test_memory_block_contains_opponent_claims():
    memory = DebateMemory()
    memory.record_turn("contra", "AI harms student critical thinking skills fundamentally.")
    block = memory.get_memory_block("pro")
    assert "OPPONENT'S CLAIMS" in block


def test_rolling_window_limits_tracked_claims():
    memory = DebateMemory()
    for i in range(10):
        memory.record_turn("pro", f"Unique claim number {i} about artificial intelligence and learning.")
    # Should not exceed _MAX_TRACKED (5) entries
    assert len(memory.pro_claims) <= 5


def test_get_memory_block_empty_at_start():
    memory = DebateMemory()
    block = memory.get_memory_block("pro")
    assert block == ""
