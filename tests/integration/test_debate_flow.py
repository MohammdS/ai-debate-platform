"""
Integration test: full debate flow using mock provider.
Exercises the complete IPC pipeline: Orchestrator → Judge → Debaters → Verdict.
No real API calls — mock provider is used throughout.
"""

import pytest

from src.sdk.llm_service import LLMService
from src.services.debater import Debater
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.watchdog_agent import WatchdogAgent


def _build_services(rounds: int = 2):
    service = LLMService(override_provider="mock")
    debater_a = Debater("Pro", "AI is beneficial", "Is AI good?",
                        service.get_client("debater_a"),
                        service.get_gatekeeper("debater_a"))
    debater_b = Debater("Contra", "AI is harmful", "Is AI good?",
                        service.get_client("debater_b"),
                        service.get_gatekeeper("debater_b"))
    judge = Judge(service.get_client("judge"), service.get_gatekeeper("judge"))
    return debater_a, debater_b, judge, rounds


@pytest.mark.asyncio
async def test_full_debate_produces_verdict():
    debater_a, debater_b, judge, rounds = _build_services(rounds=2)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)
    verdict = await orchestrator.run_debate()
    assert isinstance(verdict, str)
    assert len(verdict) > 0


@pytest.mark.asyncio
async def test_full_debate_transcript_length():
    debater_a, debater_b, judge, rounds = _build_services(rounds=2)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)
    await orchestrator.run_debate()
    # 2 rounds × 2 debaters = 4 transcript entries
    assert len(orchestrator.history) == rounds * 2


@pytest.mark.asyncio
async def test_full_debate_with_watchdog():
    debater_a, debater_b, judge, rounds = _build_services(rounds=1)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)

    verdict_box: list[str] = []

    async def _run():
        v = await orchestrator.run_debate()
        verdict_box.append(v)

    wd = WatchdogAgent(max_failures=3, poll_interval=0.1)
    wd.register("debate", _run, timeout=60.0)
    await wd.start()

    assert len(verdict_box) == 1
    assert isinstance(verdict_box[0], str)
