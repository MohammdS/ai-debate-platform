
import pytest

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType
from src.sdk.mock_client import MockAIClient
from src.services.base_agent import enforce_word_limit
from src.services.debater import Debater
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
    """Text over the limit is truncated and ellipsis appended."""
    import logging
    logger = logging.getLogger("test")
    text = " ".join(["word"] * 200)
    result = enforce_word_limit(text, 120, "debater", logger)
    # "..." is appended to the last word (no space), so still 120 tokens
    assert result.endswith("...")
    assert len(result.split()) == 120


def test_enforce_word_limit_logs_warning(caplog):
    """A warning is logged when the response is truncated."""
    import logging
    logger = logging.getLogger("test_warn")
    text = " ".join(["word"] * 150)
    with caplog.at_level(logging.WARNING, logger="test_warn"):
        enforce_word_limit(text, 120, "debater_A", logger)
    assert any("truncating" in rec.message for rec in caplog.records)


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
