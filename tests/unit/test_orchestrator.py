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
