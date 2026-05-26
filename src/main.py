from __future__ import annotations

import argparse
import asyncio
import sys

from src.cli.menu import interactive_menu
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
from src.shared.version import VERSION

logger = setup_logger("main")
_cfg = ConfigManager()


async def run_debate(topic: str, stance_a: str, stance_b: str,
                     provider_a: str | None = None,
                     provider_b: str | None = None) -> None:
    provider_a = provider_a or _cfg.default_provider_a
    provider_b = provider_b or _cfg.default_provider_b
    judge_provider = _cfg.default_judge_provider

    service = LLMService(role_overrides={
        "debater_a": provider_a,
        "debater_b": provider_b,
        "judge": judge_provider,
    })

    gk_a = service.get_gatekeeper("debater_a")
    gk_b = service.get_gatekeeper("debater_b")
    gk_j = service.get_gatekeeper("judge")

    debater_a = Debater("Pro", stance_a, topic,
                        service.get_client("debater_a"), gk_a,
                        skill=DebaterSkill(_cfg.skill_type_a),
                        opponent_stance=stance_b)
    debater_b = Debater("Contra", stance_b, topic,
                        service.get_client("debater_b"), gk_b,
                        skill=DebaterSkill(_cfg.skill_type_b),
                        opponent_stance=stance_a)
    judge = Judge(service.get_client("judge"), gk_j)

    print("\n[INFO] Starting debate...\n")
    watchdog = WatchdogAgent(
        max_failures=_cfg.watchdog_max_failures,
        poll_interval=_cfg.watchdog_poll_interval,
    )
    orchestrator = DebateOrchestrator(
        debater_a, debater_b, judge,
        beat_fn=lambda: watchdog.beat("debate"),
    )
    verdict_box: list[str] = []

    async def _run_and_capture():
        verdict_box.append(await orchestrator.run_debate())

    watchdog.register("debate", _run_and_capture, timeout=_cfg.watchdog_timeout)
    await watchdog.start()

    if not verdict_box:
        logger.error("Debate terminated without producing a verdict.")
        print("\n[ERROR] The debate did not complete. Check the logs for details.")
        sys.exit(1)

    verdict = verdict_box[0]
    token_stats = _merge_stats(gk_a, gk_b, gk_j)

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict, token_stats)
    exporter.export_to_json(topic, orchestrator.history, verdict, token_stats)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print(verdict)
    print("\n" + "-" * 60)
    print("TOKEN USAGE")
    print("-" * 60)
    print(DebateExporter.format_token_summary(token_stats))
    print("\n[SUCCESS] Transcript saved to results/")


def _merge_stats(*gks: ApiGatekeeper) -> dict:
    return {
        "total_tokens_in":  sum(g.get_stats()["total_tokens_in"]    for g in gks),
        "total_tokens_out": sum(g.get_stats()["total_tokens_out"]   for g in gks),
        "estimated_cost_usd": round(sum(g.get_stats()["estimated_cost_usd"] for g in gks), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Debate Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to launch the interactive menu.",
    )
    parser.add_argument("--version", action="version", version=f"ai-debate-platform {VERSION}")
    parser.add_argument("--topic",      default=None)
    parser.add_argument("--stance-a",   default=None, dest="stance_a")
    parser.add_argument("--stance-b",   default=None, dest="stance_b")
    parser.add_argument("--provider-a", default=None, dest="provider_a",
                        help="groq | gemini | openai | zai | mock  (default from config)")
    parser.add_argument("--provider-b", default=None, dest="provider_b",
                        help="groq | gemini | openai | zai | mock  (default from config)")
    args = parser.parse_args()

    params = interactive_menu() if not (args.topic and args.stance_a and args.stance_b) else {
        "topic": args.topic, "stance_a": args.stance_a, "stance_b": args.stance_b,
        "provider_a": args.provider_a, "provider_b": args.provider_b,
    }
    asyncio.run(run_debate(**params))


if __name__ == "__main__":
    main()
