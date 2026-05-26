import asyncio
import logging

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


def build_debate_services(payload: dict):
    """Create debate services from a browser payload using LLMService routing."""
    topic    = payload.get("topic")    or "Is AI a threat?"
    stance_a = payload.get("stance_a") or "AI is a significant threat"
    stance_b = payload.get("stance_b") or "AI is not a threat"
    provider = payload.get("provider")
    provider_a     = payload.get("provider_a")     or provider or _cfg.default_provider_a
    provider_b     = payload.get("provider_b")     or provider or _cfg.default_provider_b
    judge_provider = payload.get("judge_provider") or provider or _cfg.default_judge_provider

    service = LLMService(role_overrides={"debater_a": provider_a, "debater_b": provider_b,
                                         "judge": judge_provider})
    gk_a = service.get_gatekeeper("debater_a")
    gk_b = service.get_gatekeeper("debater_b")
    gk_j = service.get_gatekeeper("judge")

    debater_a = Debater("Pro", stance_a, topic, service.get_client("debater_a"), gk_a,
                        skill=DebaterSkill.EVIDENCE_BASED, opponent_stance=stance_b)
    debater_b = Debater("Contra", stance_b, topic, service.get_client("debater_b"), gk_b,
                        skill=DebaterSkill.SOCRATIC, opponent_stance=stance_a)
    judge = Judge(service.get_client("judge"), gk_j)

    max_rounds = _cfg.total_rounds
    try:
        rounds = max(1, min(max_rounds, int(payload.get("rounds", max_rounds))))
    except (ValueError, TypeError):
        rounds = max_rounds
    return topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j


async def run_debate_from_payload(payload: dict) -> DebateSession:
    """Run a full debate via the IPC orchestrator (watchdog-monitored) and return the result."""
    topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j = build_debate_services(payload)
    stance_a = payload.get("stance_a") or "Yes, strongly agree"
    stance_b = payload.get("stance_b") or "No, strongly disagree"

    watchdog = WatchdogAgent(max_failures=_cfg.watchdog_max_failures,
                             poll_interval=_cfg.watchdog_poll_interval)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds,
                                      beat_fn=lambda: watchdog.beat("debate"))
    verdict_box: list[str] = []

    async def _run_and_capture():
        verdict_box.append(await orchestrator.run_debate())

    watchdog.register("debate", _run_and_capture, timeout=_cfg.watchdog_timeout)
    await watchdog.start()

    verdict     = verdict_box[0] if verdict_box else "Debate did not complete."
    token_stats = _merge_stats(gk_a, gk_b, gk_j)
    _export(DebateExporter(), topic, orchestrator.history, verdict, token_stats)

    messages = [Message(role=e.get("role", "user"), content=e.get("content", ""))
                for e in orchestrator.history]
    return DebateSession(topic=topic, stance_a=stance_a, stance_b=stance_b,
                         history=messages, winner=verdict, scores=token_stats)


async def stream_debate_from_payload(payload: dict):
    """
    Stream live debate events via an event queue wired into the judge.

    The IPC orchestrator runs as a background task; the judge emits events
    onto event_queue as each argument is relayed. Yields NDJSON-compatible
    event dicts that the GUI reads via fetch + ReadableStream.
    """
    topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j = build_debate_services(payload)

    event_queue: asyncio.Queue = asyncio.Queue()
    judge.event_queue = event_queue

    watchdog = WatchdogAgent(max_failures=_cfg.watchdog_max_failures,
                             poll_interval=_cfg.watchdog_poll_interval)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds,
                                      beat_fn=lambda: watchdog.beat("debate"))
    yield {"type": "start", "topic": topic}

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

    verdict     = await debate_task
    token_stats = _merge_stats(gk_a, gk_b, gk_j)
    _export(DebateExporter(), topic, orchestrator.history, verdict, token_stats)
    yield {"type": "verdict", "topic": topic, "history": orchestrator.history,
           "verdict": verdict, "token_stats": token_stats}
