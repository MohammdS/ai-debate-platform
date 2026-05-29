
import pytest

from src.sdk.mock_client import MockAIClient
from src.services.debater import Debater
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_orchestrator_run_debate():
    """Full IPC debate with 1 round using mock clients."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)

    debater_a = Debater("A", "Pro", "Topic", client, gatekeeper)
    debater_b = Debater("B", "Con", "Topic", client, gatekeeper)
    judge = Judge(client, gatekeeper)

    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds=1)
    verdict = await orchestrator.run_debate()

    assert "winner" in verdict.lower()
    # transcript has 2 entries per round (one per debater)
    assert len(orchestrator.history) == 2


@pytest.mark.asyncio
async def test_orchestrator_history_matches_transcript():
    """orchestrator.history mirrors judge.transcript after run_debate."""
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)

    debater_a = Debater("A", "Pro", "Topic", client, gatekeeper)
    debater_b = Debater("B", "Con", "Topic", client, gatekeeper)
    judge = Judge(client, gatekeeper)

    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds=1)
    await orchestrator.run_debate()

    assert orchestrator.history is judge.transcript


async def _run_and_count(rounds: int):
    """Helper: run a debate and return (history_len, a_calls, b_calls, judge_calls)."""
    client_a = MockAIClient("test", "key")
    client_b = MockAIClient("test", "key")
    client_j = MockAIClient("test", "key")
    gk = ApiGatekeeper(rpm_limit=10000)

    debater_a = Debater("A", "Pro", "Topic", client_a, gk)
    debater_b = Debater("B", "Con", "Topic", client_b, gk)
    judge = Judge(client_j, gk)

    # Wrap generate_response on each client to count calls
    orig_a = client_a.generate_response
    orig_b = client_b.generate_response
    orig_j = client_j.generate_response
    calls = {"a": 0, "b": 0, "j": 0}

    async def count_a(msgs):
        calls["a"] += 1
        return await orig_a(msgs)

    async def count_b(msgs):
        calls["b"] += 1
        return await orig_b(msgs)

    async def count_j(msgs):
        calls["j"] += 1
        return await orig_j(msgs)

    client_a.generate_response = count_a
    client_b.generate_response = count_b
    client_j.generate_response = count_j

    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds=rounds)
    await orchestrator.run_debate()
    return len(orchestrator.history), calls["a"], calls["b"], calls["j"]


@pytest.mark.asyncio
async def test_orchestrator_exact_call_count_1_round():
    """1 round: A and B each generate exactly once; history has 2 entries."""
    history_len, a_calls, b_calls, j_calls = await _run_and_count(1)
    assert history_len == 2
    assert a_calls == 1
    assert b_calls == 1
    assert j_calls >= 1  # judge evaluation (possibly 2 if clarification needed)


@pytest.mark.asyncio
async def test_orchestrator_exact_call_count_2_rounds():
    """2 rounds: A and B each generate exactly twice; history has 4 entries."""
    history_len, a_calls, b_calls, j_calls = await _run_and_count(2)
    assert history_len == 4
    assert a_calls == 2
    assert b_calls == 2
    assert j_calls >= 1


@pytest.mark.asyncio
async def test_orchestrator_exact_call_count_10_rounds():
    """10 rounds: A and B each generate exactly 10 times; history has 20 entries."""
    history_len, a_calls, b_calls, j_calls = await _run_and_count(10)
    assert history_len == 20
    assert a_calls == 10
    assert b_calls == 10
    assert j_calls >= 1
