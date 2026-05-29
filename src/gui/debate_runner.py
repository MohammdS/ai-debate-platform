import asyncio
import logging
import uuid

from src.gui.service_builder import build_debate_services
from src.services.exporter import DebateExporter
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


async def run_debate_from_payload(payload: dict) -> dict:
    """Run a full debate via the IPC orchestrator (watchdog-monitored) and return the result."""
    session_id = uuid.uuid4().hex[:8]
    topic = payload.get("topic") or _cfg.default_topic

    # live_run stores the objects from the most recent watchdog attempt so that
    # stats and history are always from the last (successful) run.
    live_run: list = []
    verdict_box: list[str] = []

    def _fresh_factory():
        """Build completely fresh services for each watchdog attempt."""
        _topic, _da, _db, _j, _rds, _mi = build_debate_services(payload)
        _orch = DebateOrchestrator(_da, _db, _j, _rds)

        async def _run():
            v = await _orch.run_debate()
            verdict_box.append(v)
            live_run.clear()
            live_run.extend([_da, _db, _j, _orch, _mi])

        return _run()

    watchdog = WatchdogAgent()
    watchdog.register("debate", _fresh_factory, timeout=_cfg.watchdog_timeout)
    await watchdog.start()

    verdict = verdict_box[-1] if verdict_box else "Debate did not complete."
    if live_run:
        debater_a, debater_b, judge, orchestrator, model_info = live_run
        stats = _merge_stats(debater_a.gatekeeper, debater_b.gatekeeper, judge.gatekeeper)
    else:
        orchestrator = type("_Empty", (), {"history": []})()
        model_info = {}
        stats = {"total_tokens_in": 0, "total_tokens_out": 0, "estimated_cost_usd": 0.0}
        debater_a = debater_b = None

    def _export(results_dir: str) -> None:
        exp = DebateExporter(results_dir=results_dir)
        exp.export_to_markdown(topic, orchestrator.history, verdict,
                               model_info=model_info, token_stats=stats)
        exp.export_to_json(topic, orchestrator.history, verdict,
                           model_info=model_info, token_stats=stats)
        if debater_a and debater_b:
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
            # Stop waiting for live events; the debate task below still resolves the final result.
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
