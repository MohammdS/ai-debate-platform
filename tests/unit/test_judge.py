import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType
from src.sdk.mock_client import MockAIClient
from src.services.judge import _MAX_TRANSCRIPT_ENTRIES, _MAX_WORDS, Judge
from src.services.judge_prompts import parse_structured_verdict
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_judge_evaluate_direct():
    """evaluate() direct SDK call still works (backward compat)."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper()
    judge = Judge(client, gatekeeper)

    verdict = await judge.evaluate([{"role": "user", "content": "Argument"}])
    assert "winner" in verdict.lower()


@pytest.mark.asyncio
async def test_judge_run_mediates_one_round():
    """run() relays A→B and B→A for one round then emits VERDICT + SHUTDOWN."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    judge = Judge(client, gatekeeper)

    inbox_a   = IpcChannel("inbox_a",   timeout=5.0)
    inbox_b   = IpcChannel("inbox_b",   timeout=5.0)
    outbox_a  = IpcChannel("outbox_a",  timeout=5.0)
    outbox_b  = IpcChannel("outbox_b",  timeout=5.0)
    verdict_ch = IpcChannel("verdict",  timeout=5.0)

    judge.inbox_a        = inbox_a
    judge.inbox_b        = inbox_b
    judge.outbox_a       = outbox_a
    judge.outbox_b       = outbox_b
    judge.verdict_channel = verdict_ch

    # Pre-fill debater inboxes (simulating debaters responding)
    await inbox_a.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_a", receiver="judge",
        payload="AI is dangerous.", round_num=1,
    ))
    await inbox_b.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_b", receiver="judge",
        payload="AI is beneficial.", round_num=1,
    ))

    await judge.run(total_rounds=1)

    # Judge should have relayed A's msg to outbox_b
    relay_to_b = await outbox_b.receive()
    assert relay_to_b.msg_type == MessageType.RELAY
    assert relay_to_b.payload == "AI is dangerous."

    # And B's msg to outbox_a
    relay_to_a = await outbox_a.receive()
    assert relay_to_a.msg_type == MessageType.RELAY
    assert relay_to_a.payload == "AI is beneficial."

    # Verdict should be on verdict_channel
    verdict = await verdict_ch.receive()
    assert verdict.msg_type == MessageType.VERDICT
    assert "winner" in verdict.payload.lower()

    # SHUTDOWN sent to both debaters
    sd_a = await outbox_a.receive()
    sd_b = await outbox_b.receive()
    assert sd_a.msg_type == MessageType.SHUTDOWN
    assert sd_b.msg_type == MessageType.SHUTDOWN


@pytest.mark.asyncio
async def test_judge_verdict_within_word_limit():
    """evaluate() output never exceeds judge_max_words words."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    judge = Judge(client, gatekeeper)

    verdict = await judge.evaluate([
        {"name": "Debater_A", "role": "user", "content": "AI is dangerous."},
        {"name": "Debater_B", "role": "user", "content": "AI is beneficial."},
    ])
    word_count = len(verdict.split())
    # Allow one extra for the appended "..." token if truncation occurred
    assert word_count <= _MAX_WORDS + 1


@pytest.mark.asyncio
async def test_judge_beat_fn_called_once_per_round():
    """beat_fn is called exactly once per completed relay round."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    beat_calls: list[None] = []
    judge = Judge(client, gatekeeper, beat_fn=lambda: beat_calls.append(None))

    inbox_a    = IpcChannel("inbox_a",    timeout=5.0)
    inbox_b    = IpcChannel("inbox_b",    timeout=5.0)
    outbox_a   = IpcChannel("outbox_a",   timeout=5.0)
    outbox_b   = IpcChannel("outbox_b",   timeout=5.0)
    verdict_ch = IpcChannel("verdict",    timeout=5.0)

    judge.inbox_a         = inbox_a
    judge.inbox_b         = inbox_b
    judge.outbox_a        = outbox_a
    judge.outbox_b        = outbox_b
    judge.verdict_channel = verdict_ch

    await inbox_a.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_a", receiver="judge",
        payload="Arg A round 1.", round_num=1,
    ))
    await inbox_b.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_b", receiver="judge",
        payload="Arg B round 1.", round_num=1,
    ))
    await inbox_a.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_a", receiver="judge",
        payload="Arg A round 2.", round_num=2,
    ))
    await inbox_b.send(DebateMessage(
        msg_type=MessageType.ARGUMENT, sender="debater_b", receiver="judge",
        payload="Arg B round 2.", round_num=2,
    ))

    await judge.run(total_rounds=2)

    # beat_fn must be called once per round
    assert len(beat_calls) == 2


def test_truncate_transcript_short_stays_unchanged():
    """Transcripts within the limit are returned unmodified."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    judge = Judge(client, gatekeeper)

    entries = [{"role": "user", "name": f"D{i}", "content": f"Arg {i}"} for i in range(4)]
    result = judge._truncate_transcript(entries)
    assert result == entries


def test_truncate_transcript_long_clips_middle():
    """Transcripts exceeding _MAX_TRANSCRIPT_ENTRIES have middle entries replaced."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    judge = Judge(client, gatekeeper)

    # Build a transcript that is definitely over the limit
    n = _MAX_TRANSCRIPT_ENTRIES + 6
    entries = [{"role": "user", "name": f"D{i}", "content": f"Arg {i}"} for i in range(n)]
    result = judge._truncate_transcript(entries)

    assert len(result) == _MAX_TRANSCRIPT_ENTRIES + 1  # head + ellipsis + tail
    # First two entries intact
    assert result[0] == entries[0]
    assert result[1] == entries[1]
    assert "omitted" in result[2]["content"]  # middle is ellipsis placeholder
    assert result[-1] == entries[-1]          # last entry intact


# ═══════════════════════════════════════════════════════════════════════════
# Empty-transcript guard
# ═══════════════════════════════════════════════════════════════════════════

class TestJudgeEmptyTranscriptGuard:
    """evaluate() must refuse to call the LLM when the transcript has no usable content."""

    def _make_judge_with_spy(self):
        """Return a Judge whose gatekeeper.execute is a spy that must not be called."""
        client = MagicMock()
        client.generate_response = AsyncMock()
        gk = MagicMock()
        gk.execute = AsyncMock()
        return Judge(client, gk), gk

    @pytest.mark.asyncio
    async def test_evaluate_raises_on_empty_list(self):
        judge, gk = self._make_judge_with_spy()
        with pytest.raises(ValueError, match="no valid entries"):
            await judge.evaluate([])
        gk.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_evaluate_raises_on_blank_content_entries(self):
        """Entries that exist but have only whitespace content are treated as empty."""
        judge, gk = self._make_judge_with_spy()
        with pytest.raises(ValueError, match="no valid entries"):
            await judge.evaluate([
                {"role": "user", "name": "Debater_A", "content": "   "},
                {"role": "user", "name": "Debater_B", "content": "\n\t"},
            ])
        gk.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_evaluate_proceeds_when_one_entry_has_content(self):
        """A single non-blank entry is enough to allow evaluation."""
        client = MockAIClient("test", "key")
        gk = ApiGatekeeper(rpm_limit=1000)
        judge = Judge(client, gk)
        # Should not raise — one valid entry is present
        verdict = await judge.evaluate([
            {"role": "user", "name": "Debater_A", "content": "AI is beneficial."},
        ])
        assert verdict  # some non-empty verdict was produced

    @pytest.mark.asyncio
    async def test_run_emits_debate_failed_when_transcript_empty(self):
        """run() emits 'debate_failed' without calling the LLM when no arguments arrive.

        Simulated by giving inbox_a a very short timeout so it times out immediately,
        leaving judge.transcript empty and triggering the empty-transcript guard.
        """
        client = MagicMock()
        client.generate_response = AsyncMock()
        gk = MagicMock()
        gk.execute = AsyncMock()
        judge = Judge(client, gk)

        # inbox_a times out instantly → loop breaks → transcript stays empty
        inbox_a    = IpcChannel("ia", timeout=0.05)
        inbox_b    = IpcChannel("ib", timeout=5.0)
        outbox_a   = IpcChannel("oa", timeout=5.0)
        outbox_b   = IpcChannel("ob", timeout=5.0)
        verdict_ch = IpcChannel("v",  timeout=5.0)
        judge.inbox_a         = inbox_a
        judge.inbox_b         = inbox_b
        judge.outbox_a        = outbox_a
        judge.outbox_b        = outbox_b
        judge.verdict_channel = verdict_ch

        await judge.run(total_rounds=1)

        verdict_msg = await verdict_ch.receive()
        assert verdict_msg.msg_type == MessageType.VERDICT
        assert "debate_failed" in verdict_msg.payload
        # The LLM must never have been invoked
        gk.execute.assert_not_called()


# ── Structured verdict parser & judge integration tests ──────────────────
# Schema: logic/evidence/rebuttal_quality → 0-20 each; rest → 0-10 each; total → sum
_SCORE = {
    "logic": 16, "evidence": 15, "rebuttal_quality": 17,
    "relevance": 8, "clarity": 9, "citation_quality": 7, "consistency": 8,
    "total": 80,
}
_SCORE_B = {
    "logic": 11, "evidence": 9, "rebuttal_quality": 10,
    "relevance": 7, "clarity": 7, "citation_quality": 5, "consistency": 6,
    "total": 55,
}
_SAMPLE_VERDICT = {
    "scores": {"pro": _SCORE, "contra": _SCORE_B},
    "reasoning": {"pro": "Strong evidence.", "contra": "Lacked citations."},
    "winner": "Pro",
}
_EXPECTED_FIELDS = {"logic", "evidence", "rebuttal_quality", "relevance",
                    "clarity", "citation_quality", "consistency", "total"}


def test_parse_structured_verdict_valid_json():
    """parse_structured_verdict extracts dict from valid JSON string."""
    result = parse_structured_verdict(json.dumps(_SAMPLE_VERDICT))
    assert result is not None and result["winner"] == "Pro"
    assert result["scores"]["pro"]["logic"] == 16


def test_parse_structured_verdict_from_code_block():
    """parse_structured_verdict extracts dict from ```json...``` block."""
    result = parse_structured_verdict("Verdict:\n```json\n" + json.dumps(_SAMPLE_VERDICT) + "\n```")
    assert result is not None and result["winner"] == "Pro"


def test_parse_structured_verdict_returns_none_on_garbage():
    """parse_structured_verdict returns None on malformed input."""
    assert parse_structured_verdict("not json") is None
    assert parse_structured_verdict("```json\n{broken\n```") is None
    assert parse_structured_verdict("") is None


def test_verdict_has_all_score_fields():
    """Structured verdict contains all 7 scoring fields + total per debater."""
    result = parse_structured_verdict(json.dumps(_SAMPLE_VERDICT))
    assert result is not None
    for side in ("pro", "contra"):
        assert set(result["scores"][side].keys()) == _EXPECTED_FIELDS


def test_parse_structured_verdict_clamps_out_of_range_scores():
    """Scores above the field maximum are clamped; total is recomputed."""
    bad = {
        "scores": {
            "pro":    {"logic": 150, "evidence": 5, "rebuttal_quality": 5,
                       "relevance": 5, "clarity": 5, "citation_quality": 5,
                       "consistency": 5, "total": 999},
            "contra": {"logic": -5, "evidence": 0, "rebuttal_quality": 0,
                       "relevance": 0, "clarity": 0, "citation_quality": 0,
                       "consistency": 0, "total": 0},
        },
        "reasoning": {"pro": "ok", "contra": "ok"},
        "winner": "Pro",
    }
    result = parse_structured_verdict(json.dumps(bad))
    assert result is not None
    assert result["scores"]["pro"]["logic"] == 20          # clamped to max
    assert result["scores"]["pro"]["total"] == 50          # 20+5+5+5+5+5+5 = 50
    assert result["scores"]["contra"]["logic"] == 0        # clamped to min


def test_parse_structured_verdict_recomputes_wrong_total():
    """Total in JSON is ignored — always recomputed from field values."""
    wrong_total = dict(_SCORE)
    wrong_total["total"] = 999          # intentionally wrong
    verdict = {"scores": {"pro": wrong_total, "contra": _SCORE_B},
               "reasoning": {"pro": "", "contra": ""}, "winner": "Pro"}
    result = parse_structured_verdict(json.dumps(verdict))
    assert result is not None
    assert result["scores"]["pro"]["total"] == 80          # 16+15+17+8+9+7+8


def test_format_verdict_for_display_structure():
    """format_verdict_for_display renders totals and all field lines."""
    from src.services.judge_prompts import format_verdict_for_display
    text = format_verdict_for_display(_SAMPLE_VERDICT)
    assert "80/100" in text
    assert "55/100" in text
    assert "WINNER" in text.upper()
    assert "PRO" in text.upper()
    # All 7 scored fields appear
    for field in ("Logic", "Evidence", "Rebuttal Quality", "Relevance",
                  "Clarity", "Citation Quality", "Consistency"):
        assert field in text


def test_format_verdict_displays_per_field_max():
    """Each field shows its maximum (20 or 10) next to the score."""
    from src.services.judge_prompts import format_verdict_for_display
    text = format_verdict_for_display(_SAMPLE_VERDICT)
    assert "16/20" in text    # logic (max 20)
    assert "8/10" in text     # relevance (max 10)


def test_format_verdict_winner_uppercase():
    """Winner section is rendered in uppercase for visual emphasis."""
    from src.services.judge_prompts import format_verdict_for_display
    text = format_verdict_for_display(_SAMPLE_VERDICT)
    assert "WINNER: PRO" in text


@pytest.mark.asyncio
async def test_judge_stores_structured_verdict():
    """After evaluate(), judge.structured_verdict is None for non-JSON mock (graceful degradation)."""
    judge = Judge(MockAIClient("test", "key"), ApiGatekeeper(rpm_limit=1000))
    assert judge.structured_verdict is None
    await judge.evaluate([{"role": "user", "name": "A", "content": "AI is good."}])
    assert judge.structured_verdict is None


@pytest.mark.asyncio
async def test_judge_verdict_winner_field_is_valid():
    """Structured verdict winner field is 'Pro' or 'Contra' when JSON is returned."""
    result = parse_structured_verdict(json.dumps(_SAMPLE_VERDICT))
    assert result is not None and result["winner"] in ("Pro", "Contra")
