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

logger = logging.getLogger(__name__)


def _merge_stats(*gks) -> dict:
    """Aggregate token/cost stats across multiple ApiGatekeeper instances."""
    t_in  = sum(g.get_stats()["total_tokens_in"]    for g in gks)
    t_out = sum(g.get_stats()["total_tokens_out"]   for g in gks)
    cost  = sum(g.get_stats()["estimated_cost_usd"] for g in gks)
    return {
        "total_tokens_in":    t_in,
        "total_tokens_out":   t_out,
        "estimated_cost_usd": round(cost, 6),
    }


def build_debate_services(payload: dict):
    """Create debate services from a browser payload using LLMService routing."""
    topic    = payload.get("topic")    or "Is AI a threat?"
    stance_a = payload.get("stance_a") or "AI is a significant threat"
    stance_b = payload.get("stance_b") or "AI is not a threat"
    provider_a = payload.get("provider_a") or "zai"
    provider_b = payload.get("provider_b") or "groq"

    service = LLMService(role_overrides={
        "debater_a": provider_a,
        "debater_b": provider_b,
        "judge": "groq",
    })

    gk_a = service.get_gatekeeper("debater_a")
    gk_b = service.get_gatekeeper("debater_b")
    gk_j = service.get_gatekeeper("judge")

    debater_a = Debater("Pro", stance_a, topic,
                        service.get_client("debater_a"), gk_a,
                        skill=DebaterSkill.EVIDENCE_BASED,
                        opponent_stance=stance_b)
    debater_b = Debater("Contra", stance_b, topic,
                        service.get_client("debater_b"), gk_b,
                        skill=DebaterSkill.SOCRATIC,
                        opponent_stance=stance_a)
    judge     = Judge(service.get_client("judge"), gk_j)
    try:
        rounds = max(1, min(10, int(payload.get("rounds", 10))))
    except (ValueError, TypeError):
        rounds = 10
    return topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j


async def run_debate_from_payload(payload: dict) -> DebateSession:
    """Run a full debate via the IPC orchestrator (watchdog-monitored) and return the result."""
    topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j = (
        build_debate_services(payload)
    )
    stance_a = payload.get("stance_a") or "Yes, strongly agree"
    stance_b = payload.get("stance_b") or "No, strongly disagree"

    watchdog = WatchdogAgent(max_failures=3, poll_interval=5.0)
    orchestrator = DebateOrchestrator(
        debater_a, debater_b, judge, rounds,
        beat_fn=lambda: watchdog.beat("debate"),
    )
    verdict_box: list[str] = []

    async def _run_and_capture():
        v = await orchestrator.run_debate()
        verdict_box.append(v)

    watchdog.register("debate", _run_and_capture, timeout=600.0)
    await watchdog.start()

    verdict      = verdict_box[0] if verdict_box else "Debate did not complete."
    token_stats  = _merge_stats(gk_a, gk_b, gk_j)

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict, token_stats)
    exporter.export_to_json(topic, orchestrator.history, verdict, token_stats)

    messages = [
        Message(role=entry.get("role", "user"), content=entry.get("content", ""))
        for entry in orchestrator.history
    ]

    return DebateSession(
        topic=topic,
        stance_a=stance_a,
        stance_b=stance_b,
        history=messages,
        winner=verdict,
        scores=token_stats,
    )


async def stream_debate_from_payload(payload: dict):
    """
    Stream live debate events via an event queue wired into the judge.

    The IPC orchestrator runs as a background task; the judge emits events
    onto event_queue as each argument is relayed. Yields NDJSON-compatible
    event dicts that the GUI reads via fetch + ReadableStream.
    """
    topic, debater_a, debater_b, judge, rounds, gk_a, gk_b, gk_j = (
        build_debate_services(payload)
    )

    event_queue: asyncio.Queue = asyncio.Queue()
    judge.event_queue = event_queue

    watchdog = WatchdogAgent(max_failures=3, poll_interval=5.0)
    orchestrator = DebateOrchestrator(
        debater_a, debater_b, judge, rounds,
        beat_fn=lambda: watchdog.beat("debate"),
    )
    yield {"type": "start", "topic": topic}

    debate_task = asyncio.create_task(orchestrator.run_debate())

    while True:
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=120.0)
        except TimeoutError:
            break
        if event.get("type") == "_done":
            break
        yield event

    verdict     = await debate_task
    token_stats = _merge_stats(gk_a, gk_b, gk_j)

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict, token_stats)
    exporter.export_to_json(topic, orchestrator.history, verdict, token_stats)

    yield {
        "type":        "verdict",
        "topic":       topic,
        "history":     orchestrator.history,
        "verdict":     verdict,
        "token_stats": token_stats,
    }
