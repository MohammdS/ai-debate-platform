from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from src.sdk.base_client import BaseAIClient
from src.shared.gatekeeper import ApiGatekeeper
from src.shared.logger import setup_logger

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_PROMPTS_PATH = Path(__file__).resolve().parents[2] / "config" / "skills.json"


def _load_prompts() -> dict:
    try:
        return json.loads(_PROMPTS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_PROMPTS: dict = _load_prompts()


class DebaterSkill(StrEnum):
    EVIDENCE_BASED  = "evidence_based"
    SOCRATIC        = "socratic"
    STORYTELLING    = "storytelling"
    LOGICAL_FALLACY = "logical_fallacy"


def get_agent_prompt(role: str) -> dict:
    return _PROMPTS.get("agents", {}).get(role, {})


def enforce_word_limit(text: str, max_words: int, label: str,
                       logger: logging.Logger) -> str:
    """Truncates text to max_words if exceeded, logging a warning."""
    words = text.split()
    if len(words) <= max_words:
        return text
    logger.warning("%s response exceeded %d words (%d) — truncating",
                   label, max_words, len(words))
    return " ".join(words[:max_words]) + "..."


class BaseAgent(ABC):
    """
    Abstract base for all debate agents (Debater, Judge).

    Provides:
    - Shared client + gatekeeper wiring
    - IPC inbox/outbox slot declarations
    - Abstract generate() and run() contracts every agent must implement
    - Shared _build_messages() and _validate_response() helpers
    """

    def __init__(self, name: str, client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 role: str = "", system_prompt: str = ""):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.client = client
        self.gatekeeper = gatekeeper
        self.logger: logging.Logger = setup_logger()
        self.inbox:  IpcChannel | None = None
        self.outbox: IpcChannel | None = None

    def _build_messages(self, user_content: str) -> list[dict]:
        """Prepend the system prompt to a single user message."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": user_content},
        ]

    def _validate_response(self, response: str) -> str:
        """Raise ValueError if response is empty or blank; else return it."""
        if not response or not response.strip():
            raise ValueError(f"[{self.name}] received empty response from LLM")
        return response

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str:
        """Call the LLM with messages and return the text response."""

    @abstractmethod
    async def run(self) -> None:
        """Start the agent's IPC process loop."""
