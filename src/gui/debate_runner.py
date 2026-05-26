import asyncio
import logging
import uuid

from src.models.debate import DebateSession, Message
from src.sdk.llm_service import LLMService
from src.services.base_agent import DebaterSkill
from src.services.debater import Debater
from src.services.exporter import DebateExporter
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.watchdog_agent import WatchdogAgent
from src.shared.config import ConfigManager

logger = logging.getLogger(__name__)
_cfg = ConfigManager()


def _merge_stats(*gks) -> dict:
    """Aggregate token/cost stats across multiple ApiGatekeeper instances."""
    return {
        "total_tokens_in":    sum(g.get_stats()["total_tokens_in"]    for g in gks),
        "total_tokens_out":   sum(g.get_stats()["total_tokens_out"]   for g in gks),
        "estimated_cost_usd": round(sum(g.get_stats()["estimated_cost_usd"] for g in gks), 6),
    }


def _export(exporter: DebateExporter, topic: str, history: list, verdict: str, stats: dict) -> None:
    exporter.export_to_markdown(topic, history, verdict, stats)
    exporter.export_to_json(topic, history, verdict, stats)


def _model_label(provider: str, model: str) -> str:
    provider_names = {
        "zai": "Z.ai",
        "groq": "Groq",
        "gemini": "Gemini",
        "openai": "OpenAI",
        "mock": "Mock",
    }
    return f"{provider_names.get(provider, provider)} {model}"


def _model_info(service: LLMService) -> dict:
    return {
        "debater_a": {
            "label": "Debater A",
            "provider": service.provider_for("debater_a"),
            "model": service.model_for("debater_a"),
        },
        "debater_b": {
            "label": "Debater B",
            "provider": service.provider_for("debater_b"),
            "model": service.model_for("debater_b"),
        },
        "judge": {
            "label": "Judge",
            "provider": service.provider_for("judge"),
            "model": service.model_for("judge"),
        },
    }


def _with_display_names(model_info: dict) -> dict:
    for item in model_info.values():
        item["display"] = _model_label(item["provider"], item["model"])
    return model_info


def build_debate_services(payload: dict):
    """Create debate services from a browser payload using LLMService routing."""
    topic    = payload.get("topic")    or "Is AI a threat?"
    stance_a = payload.get("stance_a") or "AI is a significant threat"
    stance_b = payload.get("stance_b") or "AI is not a threat"
    default_provider = payload.get("provider")
    provider_a = payload.get("provider_a") or default_provider or "zai"
    provider_b = payload.get("provider_b") or default_provider or "groq"
    judge_provider = payload.get("judge_provider") or (
        default_provider if default_provider == "mock" else "groq"
    )

    service = LLMService(role_overrides={
        "debater_a": provider_a,
        "debater_b": provider_b,
        "judge": judge_provider,
    })
    model_info = _with_display_names(_model_info(service))

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
    judge     = Judge(service.get_client("judge"),
                      service.get_gatekeeper("judge"))
    rounds    = max(1, min(10, int(payload.get("rounds", 10))))
    return topic, debater_a, debater_b, judge, rounds, model_info


async def run_debate_from_payload(payload: dict) -> dict:
    """Run a full debate via the IPC orchestrator (watchdog-monitored) and return the result."""
    session_id = uuid.uuid4().hex[:8]
    topic, debater_a, debater_b, judge, rounds, model_info = build_debate_services(payload)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)

    watchdog = WatchdogAgent()
    verdict_box: list[str] = []

    async def _run_and_capture():
        verdict_box.append(await orchestrator.run_debate())

    watchdog.register("debate", _run_and_capture, timeout=_cfg.watchdog_timeout)
    await watchdog.start()

    verdict = verdict_box[0] if verdict_box else "Debate did not complete."
    stats = _merge_stats(debater_a.gatekeeper, debater_b.gatekeeper, judge.gatekeeper)

    def _export(results_dir: str) -> None:
        exp = DebateExporter(results_dir=results_dir)
        exp.export_to_markdown(topic, orchestrator.history, verdict,
                               model_info=model_info, token_stats=stats)
        exp.export_to_json(topic, orchestrator.history, verdict,
                           model_info=model_info, token_stats=stats)
        exp.export_skill_log(
            topic,
            debater_a.skill_log, f"Pro ({debater_a.stance})",
            debater_b.skill_log, f"Contra ({debater_b.stance})",
        )

    _export(f"results/{session_id}")   # session-specific (for concurrent access)
    _export("results")                 # legacy path (most recent debate)
    return {"session_id": session_id, "topic": topic, "history": orchestrator.history,
            "verdict": verdict, "model_info": model_info, "token_stats": stats}


async def stream_debate_from_payload(payload: dict):
    """
    Stream live debate events via an event queue wired into the judge.

    The IPC orchestrator runs as a background task; the judge emits events
    onto event_queue as each argument is relayed. Yields NDJSON-compatible
    event dicts that the GUI reads via fetch + ReadableStream.
    """
    session_id = uuid.uuid4().hex[:8]
    topic, debater_a, debater_b, judge, rounds, model_info = build_debate_services(payload)

    event_queue: asyncio.Queue = asyncio.Queue()
    judge.event_queue = event_queue

    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)
    yield {"type": "start", "session_id": session_id, "topic": topic, "model_info": model_info}

    debate_task = asyncio.create_task(orchestrator.run_debate())
    stream_timeout = _cfg.stream_event_timeout
    while True:
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=stream_timeout)
        except TimeoutError:
            break
        if event.get("type") == "_done":
            break
        yield event

    verdict = await debate_task
    stats = _merge_stats(debater_a.gatekeeper, debater_b.gatekeeper, judge.gatekeeper)

    def _export(results_dir: str) -> None:
        exp = DebateExporter(results_dir=results_dir)
        exp.export_to_markdown(topic, orchestrator.history, verdict,
                               model_info=model_info, token_stats=stats)
        exp.export_to_json(topic, orchestrator.history, verdict,
                           model_info=model_info, token_stats=stats)
        exp.export_skill_log(
            topic,
            debater_a.skill_log, f"Pro ({debater_a.stance})",
            debater_b.skill_log, f"Contra ({debater_b.stance})",
        )

    _export(f"results/{session_id}")
    _export("results")
    yield {
        "type": "verdict",
        "session_id": session_id,
        "topic": topic,
        "history": orchestrator.history,
        "verdict": verdict,
        "model_info": model_info,
        "token_stats": stats,
    }
