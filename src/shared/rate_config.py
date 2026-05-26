from __future__ import annotations

import json
from pathlib import Path

from src.shared.constants import DEFAULT_RPM_LIMIT  # noqa: F401 — re-exported

_RATE_LIMITS_PATH = Path(__file__).resolve().parents[2] / "config" / "rate_limits.json"
_PRICING_PATH     = Path(__file__).resolve().parents[2] / "config" / "pricing.json"


def load_limits(provider: str) -> dict:
    try:
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        return data.get(provider, data.get("default", {}))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_pricing(provider: str, model: str) -> tuple[float, float]:
    """Return (input_per_1m, output_per_1m) USD for provider+model."""
    try:
        data  = json.loads(_PRICING_PATH.read_text())
        pdata = data.get(provider, data.get("default", {}))
        rates = pdata.get(model, pdata.get("default", data.get("default", {})))
        if isinstance(rates, dict):
            return float(rates.get("input_per_1m", 0.10)), float(rates.get("output_per_1m", 0.10))
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        pass
    return 0.10, 0.10
