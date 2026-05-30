from __future__ import annotations

import sys

from src.shared.config import ConfigManager

_cfg = ConfigManager()

PROVIDERS = _cfg.available_providers


def _ask(prompt: str, default: str = "") -> str:
    """Prompt the user; return default if they press Enter."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)
    return value if value else default


def choose_provider(label: str, default: str | None = None) -> str:
    default = default or _cfg.default_provider_a
    default_idx = PROVIDERS.index(default) + 1 if default in PROVIDERS else 1
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
    return default


def interactive_menu() -> dict:
    print("\n" + "=" * 60)
    print("          AI DEBATE PLATFORM — Interactive Menu")
    print("=" * 60 + "\n")
    topic = _ask("Debate topic")
    if not topic:
        print("Topic cannot be empty. Aborted.")
        sys.exit(1)

    stance_a = _ask("\nStance for Debater A", _cfg.menu_stance_a)
    stance_b = _ask("Stance for Debater B", _cfg.menu_stance_b)

    provider_a = choose_provider("Debater A", default=_cfg.default_provider_a)
    provider_b = choose_provider("Debater B", default=_cfg.default_provider_b)

    print("\n" + "-" * 60)
    print(f"  Topic    : {topic}")
    print(f"  Debater A: {stance_a}  [{provider_a}]")
    print(f"  Debater B: {stance_b}  [{provider_b}]")
    print(f"  Judge    : {_cfg.default_judge_provider} (fixed)")
    print("-" * 60)

    confirm = _ask("\nStart debate? (y/n)", "y").lower()
    if confirm not in ("y", "yes", ""):
        print("Cancelled.")
        sys.exit(0)

    return {"topic": topic, "stance_a": stance_a, "stance_b": stance_b,
            "provider_a": provider_a, "provider_b": provider_b}
