from __future__ import annotations

import argparse
import asyncio
import sys

from src.sdk.llm_service import LLMService
from src.services.base_agent import DebaterSkill
from src.services.debater import Debater
from src.services.exporter import DebateExporter
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.watchdog_agent import WatchdogAgent
from src.shared.logger import setup_logger

logger = setup_logger("main")

PROVIDERS = ["groq", "gemini", "openai", "zhipu", "mock"]

# ---------------------------------------------------------------------------
# Menu helpers
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    print("\n" + "=" * 60)
    print("          AI DEBATE PLATFORM — Interactive Menu")
    print("=" * 60 + "\n")


def _ask(prompt: str, default: str = "") -> str:
    """Prompt the user; return default if they press Enter."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)
    return value if value else default


def _choose_topic() -> str:
    return _ask("Debate topic")


def _choose_provider() -> str | None:
    print("\nSelect LLM provider (leave blank to use config/models.json):")
    for i, p in enumerate(PROVIDERS, 1):
        print(f"  {i}. {p}")
    print("  6. Use config/models.json (all agents=Gemini)")

    choice = _ask("Choice", "6")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(PROVIDERS):
            return PROVIDERS[idx]
    except ValueError:
        pass
    return None


def _interactive_menu() -> dict:
    _print_banner()

    topic = _choose_topic()
    if not topic:
        print("Topic cannot be empty. Aborted.")
        sys.exit(1)

    stance_a = _ask("\nStance for Debater A", "Yes, strongly agree")
    stance_b = _ask("Stance for Debater B", "No, strongly disagree")
    provider = _choose_provider()

    print("\n" + "-" * 60)
    print(f"  Topic    : {topic}")
    print(f"  Debater A: {stance_a}")
    print(f"  Debater B: {stance_b}")
    print(f"  Provider : {provider or 'config/models.json'}")
    print("-" * 60)

    confirm = _ask("\nStart debate? (y/n)", "y").lower()
    if confirm not in ("y", "yes", ""):
        print("Cancelled.")
        sys.exit(0)

    return {"topic": topic, "stance_a": stance_a, "stance_b": stance_b, "provider": provider}


# ---------------------------------------------------------------------------
# Debate runner
# ---------------------------------------------------------------------------

async def run_debate(topic: str, stance_a: str, stance_b: str,
                     provider: str | None) -> None:
    service = LLMService(override_provider=provider)

    debater_a = Debater("Pro", stance_a, topic,
                        service.get_client("debater_a"),
                        service.get_gatekeeper("debater_a"),
                        skill=DebaterSkill.EVIDENCE_BASED,
                        opponent_stance=stance_b)
    debater_b = Debater("Contra", stance_b, topic,
                        service.get_client("debater_b"),
                        service.get_gatekeeper("debater_b"),
                        skill=DebaterSkill.SOCRATIC,
                        opponent_stance=stance_a)
    judge = Judge(service.get_client("judge"),
                  service.get_gatekeeper("judge"))

    print("\n[INFO] Starting debate...\n")
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge)
    verdict_box: list[str] = []

    async def _run_and_capture():
        v = await orchestrator.run_debate()
        verdict_box.append(v)

    watchdog = WatchdogAgent(max_failures=3, poll_interval=5.0)
    watchdog.register("debate", _run_and_capture, timeout=600.0)
    await watchdog.start()

    verdict = verdict_box[0] if verdict_box else "Debate did not complete."

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict)
    exporter.export_to_json(topic, orchestrator.history, verdict)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print(verdict)
    print("\n[SUCCESS] Transcript saved to results/")


# ---------------------------------------------------------------------------
# Entry point — supports both interactive menu and CLI flags
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Debate Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to launch the interactive menu.",
    )
    parser.add_argument("--topic",    default=None)
    parser.add_argument("--stance-a", default=None, dest="stance_a")
    parser.add_argument("--stance-b", default=None, dest="stance_b")
    parser.add_argument("--provider", default=None,
                        help="groq | gemini | openai | mock")
    args = parser.parse_args()

    # If any required arg is missing, launch interactive menu
    if not args.topic or not args.stance_a or not args.stance_b:
        params = _interactive_menu()
    else:
        params = {
            "topic":    args.topic,
            "stance_a": args.stance_a,
            "stance_b": args.stance_b,
            "provider": args.provider,
        }

    asyncio.run(run_debate(**params))


if __name__ == "__main__":
    main()
