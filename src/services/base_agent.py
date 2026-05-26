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


def get_skill_instruction(skill: DebaterSkill) -> str:
    return _PROMPTS.get("skills", {}).get(skill, {}).get("instruction", str(skill))


def get_agent_prompt(role: str) -> dict:
    return _PROMPTS.get("agents", {}).get(role, {})


def enforce_word_limit(text: str, max_words: int, label: str,
                       logger: logging.Logger) -> str:
    """
    Truncates text to max_words if exceeded, logging a warning.
    Truncation is on word boundary with ellipsis appended.
    """
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
    - Abstract run() contract every agent must implement
    """

    def __init__(self, name: str, client: BaseAIClient, gatekeeper: ApiGatekeeper):
        self.name = name
        self.client = client
        self.gatekeeper = gatekeeper
        self.logger: logging.Logger = setup_logger()
        self.inbox:  IpcChannel | None = None
        self.outbox: IpcChannel | None = None

    @abstractmethod
    async def run(self) -> None:
        """Start the agent's IPC process loop."""
