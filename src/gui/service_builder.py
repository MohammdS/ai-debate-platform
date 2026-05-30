from __future__ import annotations

from src.sdk.llm_service import LLMService
from src.services.base_agent import DebaterSkill
from src.services.debater import Debater
from src.services.judge import Judge
from src.shared.config import ConfigManager

_cfg = ConfigManager()
_REQUIRED_BROWSER_FIELDS = {
    "topic": "Topic",
    "stance_a": "Debater A stance",
    "stance_b": "Debater B stance",
    "rounds": "Rounds",
    "provider_a": "Debater A provider",
    "provider_b": "Debater B provider",
    "judge_provider": "Judge provider",
}


def _model_label(provider: str, model: str) -> str:
    return f"{_cfg.provider_labels.get(provider, provider)} {model}"


def _model_info(service: LLMService) -> dict:
    info = {
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
    for item in info.values():
        item["display"] = _model_label(item["provider"], item["model"])
    return info


def _rounds_from_payload(payload: dict) -> int:
    try:
        rounds = int(payload.get("rounds", _cfg.total_rounds))
    except (TypeError, ValueError):
        rounds = _cfg.total_rounds
    return max(_cfg.min_rounds, min(_cfg.max_rounds, rounds))


def reject_blank_browser_fields(payload: dict) -> None:
    """Reject fields the browser submitted but left empty."""
    missing = [
        label for name, label in _REQUIRED_BROWSER_FIELDS.items()
        if name in payload and not str(payload.get(name) or "").strip()
    ]
    if missing:
        raise ValueError(f"Fill in {', '.join(missing)} before starting.")


def build_debate_services(payload: dict):
    """Create debate services from a browser payload using LLMService routing."""
    topic = payload.get("topic") or _cfg.default_topic
    stance_a = payload.get("stance_a") or _cfg.default_stance_a
    stance_b = payload.get("stance_b") or _cfg.default_stance_b
    default_provider = payload.get("provider")
    provider_a = payload.get("provider_a") or default_provider or _cfg.default_provider_a
    provider_b = payload.get("provider_b") or default_provider or _cfg.default_provider_b
    # When the GUI's one-provider shortcut selects mock, keep the judge local too.
    judge_provider = payload.get("judge_provider") or (
        default_provider if default_provider == "mock" else _cfg.default_judge_provider
    )

    service = LLMService(role_overrides={
        "debater_a": provider_a,
        "debater_b": provider_b,
        "judge": judge_provider,
    })
    model_info = _model_info(service)
    debater_a = Debater(
        "Pro", stance_a, topic,
        service.get_client("debater_a"), service.get_gatekeeper("debater_a"),
        skill=DebaterSkill.EVIDENCE_BASED, opponent_stance=stance_b,
    )
    debater_b = Debater(
        "Contra", stance_b, topic,
        service.get_client("debater_b"), service.get_gatekeeper("debater_b"),
        skill=DebaterSkill.SOCRATIC, opponent_stance=stance_a,
    )
    judge = Judge(service.get_client("judge"), service.get_gatekeeper("judge"))
    rounds = _rounds_from_payload(payload)
    return topic, debater_a, debater_b, judge, rounds, model_info
