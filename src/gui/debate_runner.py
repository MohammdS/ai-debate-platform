from src.sdk.factory import AIClientFactory
from src.services.debater import Debater
from src.services.exporter import DebateExporter
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper


def build_debate_services(payload: dict):
    """Create debate services from a browser payload."""
    topic = payload.get("topic") or "Is AI a threat?"
    stance_a = payload.get("stance_a") or "AI is a significant threat"
    stance_b = payload.get("stance_b") or "AI is not a threat"
    provider = payload.get("provider") or "mock"

    config = ConfigManager()
    rpm = 1000 if provider == "mock" else config.get_value("api", "rate_limit_rpm", 30)
    gatekeeper = ApiGatekeeper(rpm_limit=rpm)
    api_key = config.get_api_key(provider)
    model = config.get_model(provider)

    client_a = AIClientFactory.create_client(provider, model, api_key)
    client_b = AIClientFactory.create_client(provider, model, api_key)
    client_j = AIClientFactory.create_client(provider, model, api_key)

    debater_a = Debater("A", stance_a, topic, client_a, gatekeeper)
    debater_b = Debater("B", stance_b, topic, client_b, gatekeeper)
    judge = Judge(client_j, gatekeeper)
    rounds = max(1, min(10, int(payload.get("rounds", 10))))
    return topic, debater_a, debater_b, judge, rounds


async def stream_debate_from_payload(payload: dict):
    """Yield live debate events as each debater and the judge responds."""
    topic, debater_a, debater_b, judge, rounds = build_debate_services(payload)
    history: list[dict[str, str]] = []
    yield {"type": "start", "topic": topic}

    for _round_num in range(1, rounds + 1):
        arg_a = await debater_a.get_argument(history)
        msg_a = {"role": "user", "name": "Debater_A", "content": arg_a}
        history.append(msg_a)
        yield {"type": "message", "message": msg_a, "count": len(history)}

        arg_b = await debater_b.get_argument(history)
        msg_b = {"role": "user", "name": "Debater_B", "content": arg_b}
        history.append(msg_b)
        yield {"type": "message", "message": msg_b, "count": len(history)}

    yield {"type": "judging"}
    verdict = await judge.evaluate(history)

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, history, verdict)
    exporter.export_to_json(topic, history, verdict)
    yield {"type": "verdict", "topic": topic, "history": history, "verdict": verdict}


async def run_debate_from_payload(payload: dict) -> dict:
    """Run a debate using the existing backend services."""
    topic, debater_a, debater_b, judge, rounds = build_debate_services(payload)
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge, rounds)
    verdict = await orchestrator.run_debate()

    exporter = DebateExporter()
    exporter.export_to_markdown(topic, orchestrator.history, verdict)
    exporter.export_to_json(topic, orchestrator.history, verdict)

    return {"topic": topic, "history": orchestrator.history, "verdict": verdict}
