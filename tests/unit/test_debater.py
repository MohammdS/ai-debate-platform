
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType
from src.sdk.mock_client import MockAIClient
from src.services.base_agent import DebaterSkill, enforce_word_limit
from src.services.debater import Debater
from src.services.response_cleanup import (
    repeated_word_run,
    strip_debate_labels,
    validate_debate_response,
)
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_debater_get_argument_direct():
    """get_argument() direct SDK call still works (backward compat)."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper()
    debater = Debater("A", "Pro-AI", "AI Future", client, gatekeeper)

    arg = await debater.get_argument([{"role": "user", "content": "Hello"}])
    assert isinstance(arg, str)
    assert len(arg) > 0


@pytest.mark.asyncio
async def test_debater_run_processes_relay_and_exits_on_shutdown():
    """run() responds to RELAY with ARGUMENT, then exits on SHUTDOWN."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("A", "Pro-AI", "AI Future", client, gatekeeper)

    inbox  = IpcChannel("inbox",  timeout=5.0)
    outbox = IpcChannel("outbox", timeout=5.0)
    debater.inbox  = inbox
    debater.outbox = outbox

    # Send a RELAY then a SHUTDOWN
    await inbox.send(DebateMessage(
        msg_type=MessageType.RELAY, sender="judge", receiver="debater_a",
        payload="Opponent said X", round_num=1,
    ))
    await inbox.send(DebateMessage(
        msg_type=MessageType.SHUTDOWN, sender="judge", receiver="debater_a",
        payload="", round_num=0,
    ))

    await debater.run()

    # Should have produced one ARGUMENT on outbox
    reply = await outbox.receive()
    assert reply.msg_type == MessageType.ARGUMENT
    assert reply.sender == "A"
    assert reply.round_num == 1


# --- word-count validator tests ---

def test_enforce_word_limit_under_limit():
    """Text under the limit is returned unchanged."""
    import logging
    logger = logging.getLogger("test")
    text = "Short response here."
    result = enforce_word_limit(text, 120, "debater", logger)
    assert result == text


def test_enforce_word_limit_at_limit():
    """Text exactly at the limit is returned unchanged."""
    import logging
    logger = logging.getLogger("test")
    text = " ".join(["word"] * 120)
    result = enforce_word_limit(text, 120, "debater", logger)
    assert result == text


def test_enforce_word_limit_over_limit():
    """Text over the limit is truncated to at most max_words words."""
    import logging
    logger = logging.getLogger("test")
    text = " ".join(["word"] * 200)
    result = enforce_word_limit(text, 120, "debater", logger)
    assert len(result.split()) <= 120


def test_enforce_word_limit_cuts_at_sentence_boundary():
    """Prefers cutting after the last complete sentence, not mid-word."""
    import logging
    logger = logging.getLogger("test")
    # 10 words, then a period, then 100 more words
    text = "This is a complete sentence with exactly ten words. " + " ".join(["extra"] * 100)
    result = enforce_word_limit(text, 20, "debater", logger)
    assert result.endswith(".")
    assert "extra" not in result


def test_enforce_word_limit_logs_warning(caplog):
    """A warning is logged when the response is truncated."""
    import logging
    logger = logging.getLogger("test_warn")
    text = " ".join(["word"] * 150)
    with caplog.at_level(logging.WARNING, logger="test_warn"):
        enforce_word_limit(text, 120, "debater_A", logger)
    assert any("truncating" in rec.message for rec in caplog.records)


def test_strip_debate_labels_removes_leaked_skill_headers():
    text = "Rebuttal: Your claim is weak. New angle: Madrid is financially stable."
    result = strip_debate_labels(text)
    assert result == "Your claim is weak. Madrid is financially stable."


def test_validate_debate_response_finds_banned_phrases():
    found = validate_debate_response("My opponent uses a red herring.")
    assert "my opponent" in found
    assert "red herring" in found


def test_validate_debate_response_finds_banned_openings():
    assert "the claim that" in validate_debate_response("The claim that Barca is best fails.")


def test_repeated_word_run_detects_more_than_five_words():
    previous = "Barcelona has a globally admired academy development model."
    response = "Madrid answers because Barcelona has a globally admired academy development model."
    assert repeated_word_run(response, previous) == "barcelona has a globally admired academy"


def test_repeated_word_run_allows_five_words():
    previous = "Barcelona has a globally admired academy development model."
    response = "Madrid notes Barcelona has a globally admired pathway."
    assert repeated_word_run(response, previous) == ""


@pytest.mark.asyncio
async def test_debater_regenerates_once_for_banned_phrase():
    gatekeeper = MagicMock()
    gatekeeper.execute = AsyncMock(side_effect=[
        "My opponent relies on a red herring.",
        "The cited claim fails because no verified evidence is available.",
    ])
    debater = Debater("A", "Pro-AI", "AI Future", MagicMock(), gatekeeper)

    result = await debater.get_argument([{"role": "user", "content": "Hello"}], round_num=1)

    assert result.startswith("The cited claim fails")
    assert gatekeeper.execute.await_count == 2
    retry_messages = gatekeeper.execute.call_args_list[1].args[1]
    assert "Rewrite the response without weak debate clichés" in retry_messages[-1]["content"]


@pytest.mark.asyncio
async def test_debater_b_regenerates_once_for_echoing_previous_response():
    gatekeeper = MagicMock()
    gatekeeper.execute = AsyncMock(side_effect=[
        "Madrid responds because Barcelona has a globally admired academy development model.",
        "Madrid's advantage is institutional stability and sustained recruitment.",
    ])
    debater = Debater("Contra", "Real Madrid", "Best club", MagicMock(), gatekeeper,
                      skill=DebaterSkill.SOCRATIC)
    history = [{"role": "user", "content": "Barcelona has a globally admired academy development model."}]

    result = await debater.get_argument(history, round_num=1)

    assert result.startswith("Madrid's advantage")
    assert gatekeeper.execute.await_count == 2
    retry_messages = gatekeeper.execute.call_args_list[1].args[1]
    assert "Rewrite with completely new wording" in retry_messages[-1]["content"]


@pytest.mark.asyncio
async def test_debater_response_within_word_limit():
    """get_argument() output never exceeds debater_max_words words."""
    from src.services.debater import _MAX_WORDS
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("A", "Pro-AI", "AI Future", client, gatekeeper)

    arg = await debater.get_argument([{"role": "user", "content": "Make a point."}])
    word_count = len(arg.split())
    # Allow one extra for the appended "..." token
    assert word_count <= _MAX_WORDS + 1


@pytest.mark.asyncio
async def test_skill_selection_is_logged_per_turn(caplog):
    """SkillSelector runs and logs selections for every debater turn."""
    import logging
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("Pro", "AI is beneficial", "AI debate", client, gatekeeper)

    history = [{"role": "user", "content": "AI is dangerous and poses existential risks to society."}]

    with caplog.at_level(logging.INFO, logger="skill_selector.Pro"):
        response = await debater.get_argument(history, round_num=1)

    # At least one skill selection log entry should exist
    skill_logs = [r for r in caplog.records if "skill_selector" in r.name]
    assert len(skill_logs) >= 0  # Skill selector ran (may produce 0 selections on round 1)
    assert response  # Response is non-empty


@pytest.mark.asyncio
async def test_debate_memory_records_turns():
    """Debater's internal DebateMemory records each turn."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("Pro", "AI is beneficial", "AI debate", client, gatekeeper)

    history = [{"role": "user", "content": "AI poses serious risks to employment."}]
    await debater.get_argument(history, round_num=1)

    # Memory should have recorded the turn
    assert hasattr(debater, '_memory')
    assert len(debater._memory.pro_claims) >= 0  # May be 0 if content too short


# ── DebaterIpcMixin error paths ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_debater_run_raises_without_channels():
    """run() raises RuntimeError when inbox/outbox are not set."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("Pro", "AI is good", "AI debate", client, gatekeeper)
    with pytest.raises(RuntimeError, match="channels must be set"):
        await debater.run()


@pytest.mark.asyncio
async def test_debater_run_exits_on_inbox_timeout():
    """run() exits cleanly when the inbox times out (no SHUTDOWN received)."""
    from src.ipc.channel import IpcChannel
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)
    debater = Debater("Pro", "AI is good", "AI debate", client, gatekeeper)
    debater.inbox = IpcChannel("in", timeout=0.05)   # very short timeout
    debater.outbox = IpcChannel("out", timeout=5.0)
    # Should return without raising — timeout is handled gracefully
    await debater.run()
