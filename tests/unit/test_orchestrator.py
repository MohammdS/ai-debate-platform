import pytest

from src.sdk.mock_client import MockAIClient
from src.services.debater import Debater
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_orchestrator_run_debate(monkeypatch):
    # Mock rounds to 1 for speed
    # Note: I'll just let it run if it's fast enough with Mock client

    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper(rpm_limit=1000)

    debater_a = Debater("A", "Pro", "Topic", client, gatekeeper)
    debater_b = Debater("B", "Con", "Topic", client, gatekeeper)
    judge = Judge(client, gatekeeper)

    orchestrator = DebateOrchestrator(debater_a, debater_b, judge)

    # Patch loop to run 1 round instead of 10 for test speed
    # We can't easily patch the range in the method without editing code
    # But I can modify the orchestrator code to take rounds as param or just run it.
    # 20 messages * minimal sleep should be okay.

    verdict = await orchestrator.run_debate()
    assert "winner" in verdict.lower()
    assert len(orchestrator.history) == 20
