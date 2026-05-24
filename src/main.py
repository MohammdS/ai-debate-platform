from __future__ import annotations

import argparse
import asyncio
import sys

from src.rag.models import RAGConfig
from src.rag.rag_service import RAGService
from src.sdk.llm_service import LLMService
from src.services.base_agent import DebaterSkill
from src.services.debater import Debater
from src.services.exporter import DebateExporter
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.watchdog_agent import WatchdogAgent
from src.shared.gatekeeper import ApiGatekeeper
from src.shared.logger import setup_logger

logger = setup_logger("main")

PROVIDERS = ["groq", "gemini", "openai", "zai", "mock"]

# ---------------------------------------------------------------------------
# Menu helpers
# ---------------------------------------------------------------------------

def _ask(prompt: str, default: str = "") -> str:
    """Prompt the user; return default if they press Enter."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)
    return value if value else default


def _choose_debater_provider(label: str, default_idx: int = 1) -> str:
    print(f"\nSelect provider for {label}:")
    for i, p in enumerate(PROVIDERS, 1):
        print(f"  {i}. {p}")
    choice = _ask("Choice", str(default_idx))
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(PROVIDERS):
            return PROVIDERS[idx]
    except ValueError:
        pass
    return PROVIDERS[default_idx - 1]


def _interactive_menu() -> dict:
    print("\n" + "=" * 60)
    print("          AI DEBATE PLATFORM — Interactive Menu")
    print("=" * 60 + "\n")
    topic = _ask("Debate topic")
    if not topic:
        print("Topic cannot be empty. Aborted.")
        sys.exit(1)

    stance_a = _ask("\nStance for Debater A", "Yes, strongly agree")
    stance_b = _ask("Stance for Debater B", "No, strongly disagree")

    provider_a = _choose_debater_provider("Debater A", default_idx=4)  # zai
    provider_b = _choose_debater_provider("Debater B", default_idx=1)  # groq

    print("\n" + "-" * 60)
    print(f"  Topic    : {topic}")
    print(f"  Debater A: {stance_a}  [{provider_a}]")
    print(f"  Debater B: {stance_b}  [{provider_b}]")
    print("  Judge    : groq (fixed)")
    print("-" * 60)

    confirm = _ask("\nStart debate? (y/n)", "y").lower()
    if confirm not in ("y", "yes", ""):
        print("Cancelled.")
        sys.exit(0)

    return {"topic": topic, "stance_a": stance_a, "stance_b": stance_b,
            "provider_a": provider_a, "provider_b": provider_b}


# ---------------------------------------------------------------------------
# Debate runner
# ---------------------------------------------------------------------------

async def run_debate(topic: str, stance_a: str, stance_b: str,
                     provider_a: str = "zai", provider_b: str = "groq",
                     use_rag: bool = False, rebuild_index: bool = False,
                     top_k: int = 3, knowledge_dir: str = "knowledge",
                     vector_db_path: str = ".chroma_db") -> None:
    service = LLMService(role_overrides={
        "debater_a": provider_a,
        "debater_b": provider_b,
        "judge": "groq",
    })

    rag_service: RAGService | None = None
    if use_rag:
        cfg = RAGConfig(knowledge_dir=knowledge_dir, vector_db_path=vector_db_path, top_k=top_k)
        rag_service = RAGService(cfg)
        ok = rag_service.initialise(rebuild=rebuild_index)
        if not ok:
            print(f"[INFO] No local knowledge files — searching web for: {topic}")
            ok = await rag_service.initialise_from_web(topic, rebuild=rebuild_index)
        if not ok:
            print("[WARN] RAG disabled — no documents indexed.")
            rag_service = None

    gk_a = service.get_gatekeeper("debater_a")
    gk_b = service.get_gatekeeper("debater_b")
    gk_j = service.get_gatekeeper("judge")

    debater_a = Debater("Pro", stance_a, topic,
                        service.get_client("debater_a"), gk_a,
                        skill=DebaterSkill.EVIDENCE_BASED,
                        opponent_stance=stance_b,
                        rag_service=rag_service)
    debater_b = Debater("Contra", stance_b, topic,
                        service.get_client("debater_b"), gk_b,
                        skill=DebaterSkill.SOCRATIC,
                        opponent_stance=stance_a,
                        rag_service=rag_service)
    judge = Judge(service.get_client("judge"), gk_j)

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

    # Aggregate token/cost stats across all three agents
    def _merge_stats(*gks: ApiGatekeeper) -> dict:
        t_in = sum(g.get_stats()["total_tokens_in"]    for g in gks)
        t_out = sum(g.get_stats()["total_tokens_out"]   for g in gks)
        cost  = sum(g.get_stats()["estimated_cost_usd"] for g in gks)
        return {"total_tokens_in": t_in, "total_tokens_out": t_out,
                "estimated_cost_usd": round(cost, 6)}

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


# ---------------------------------------------------------------------------
# Entry point — supports both interactive menu and CLI flags
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Debate Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to launch the interactive menu.",
    )
    parser.add_argument("--topic",          default=None)
    parser.add_argument("--stance-a",       default=None,     dest="stance_a")
    parser.add_argument("--stance-b",       default=None,     dest="stance_b")
    parser.add_argument("--provider-a",     default="zai",    dest="provider_a",
                        help="groq | gemini | openai | zai | mock")
    parser.add_argument("--provider-b",     default="groq",   dest="provider_b",
                        help="groq | gemini | openai | zai | mock")
    parser.add_argument("--rag",            action="store_true",
                        help="Enable Retrieval-Augmented Generation")
    parser.add_argument("--rebuild-index",  action="store_true", dest="rebuild_index",
                        help="Force rebuild of the vector index")
    parser.add_argument("--top-k",          default=3,        type=int, dest="top_k",
                        help="Number of passages to retrieve per turn")
    parser.add_argument("--knowledge-dir",  default="knowledge", dest="knowledge_dir",
                        help="Directory containing knowledge documents")
    parser.add_argument("--vector-db-path", default=".chroma_db", dest="vector_db_path",
                        help="Path for the Chroma vector store")
    args = parser.parse_args()

    if not args.topic or not args.stance_a or not args.stance_b:
        params = _interactive_menu()
    else:
        params = {
            "topic": args.topic, "stance_a": args.stance_a, "stance_b": args.stance_b,
            "provider_a": args.provider_a, "provider_b": args.provider_b,
        }

    params.update({
        "use_rag": args.rag, "rebuild_index": args.rebuild_index,
        "top_k": args.top_k, "knowledge_dir": args.knowledge_dir,
        "vector_db_path": args.vector_db_path,
    })
    asyncio.run(run_debate(**params))


if __name__ == "__main__":
    main()
