"""CLI debate runner — wires up services and executes a single debate."""
from __future__ import annotations

import sys

from src.sdk.llm_service import LLMService
from src.services.base_agent import DebaterSkill
from src.services.debater import Debater
from src.services.exporter import DebateExporter
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.watchdog_agent import WatchdogAgent
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper
from src.shared.logger import setup_logger

logger = setup_logger("runner")
_cfg = ConfigManager()


def _merge_stats(*gks: ApiGatekeeper) -> dict:
    return {
        "total_tokens_in":    sum(g.get_stats()["total_tokens_in"]    for g in gks),
        "total_tokens_out":   sum(g.get_stats()["total_tokens_out"]   for g in gks),
        "estimated_cost_usd": round(sum(g.get_stats()["estimated_cost_usd"] for g in gks), 6),
    }


async def run_debate(
    topic: str,
    stance_a: str,
    stance_b: str,
    provider_a: str | None = None,
    provider_b: str | None = None,
    judge_provider: str | None = None,
) -> None:
    provider_a = provider_a or _cfg.default_provider_a
    provider_b = provider_b or _cfg.default_provider_b
    judge_provider = judge_provider or _cfg.default_judge_provider
    print("\n[INFO] Starting debate...\n")

    # live_run stores objects from the most recent watchdog attempt so restarts
    # always produce a complete, fresh set of agents rather than a stale one.
    live_run: list = []
    verdict_box: list[str] = []

    watchdog = WatchdogAgent(
        max_failures=_cfg.watchdog_max_failures,
        poll_interval=_cfg.watchdog_poll_interval,
    )

    def _fresh_factory():
        """Build completely fresh services for each watchdog attempt."""
        _service = LLMService(role_overrides={
            "debater_a": provider_a,
            "debater_b": provider_b,
            "judge":     judge_provider,
        })
        _da = Debater(
            "Pro", stance_a, topic,
            _service.get_client("debater_a"), _service.get_gatekeeper("debater_a"),
            skill=DebaterSkill(_cfg.skill_type_a),
            opponent_stance=stance_b,
        )
        _db = Debater(
            "Contra", stance_b, topic,
            _service.get_client("debater_b"), _service.get_gatekeeper("debater_b"),
            skill=DebaterSkill(_cfg.skill_type_b),
            opponent_stance=stance_a,
        )
        _j = Judge(_service.get_client("judge"), _service.get_gatekeeper("judge"))
        _orch = DebateOrchestrator(_da, _db, _j, beat_fn=lambda: watchdog.beat("debate"))

        async def _run() -> None:
            verdict_box.append(await _orch.run_debate())
            live_run.clear()
            live_run.extend([_da, _db, _j, _orch])

        return _run()

    watchdog.register("debate", _fresh_factory, timeout=_cfg.watchdog_timeout)
    await watchdog.start()

    if not verdict_box:
        logger.error("Debate terminated without producing a verdict.")
        print("\n[ERROR] The debate did not complete. Check the logs for details.")
        sys.exit(1)

    verdict = verdict_box[-1]
    debater_a, debater_b, judge, orchestrator = live_run
    token_stats = _merge_stats(debater_a.gatekeeper, debater_b.gatekeeper, judge.gatekeeper)

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict, token_stats=token_stats)
    exporter.export_to_json(topic, orchestrator.history, verdict, token_stats=token_stats)
    exporter.export_skill_log(
        topic,
        debater_a.skill_log, f"Pro ({debater_a.stance})",
        debater_b.skill_log, f"Contra ({debater_b.stance})",
    )

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print(verdict)
    print("\n" + "-" * 60)
    print("TOKEN USAGE")
    print("-" * 60)
    print(DebateExporter.format_token_summary(token_stats))
    print("\n[SUCCESS] Transcript saved to results/")
