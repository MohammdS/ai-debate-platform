import pytest

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType
from src.sdk.mock_client import MockAIClient
from src.services.judge import _MAX_WORDS, Judge
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
