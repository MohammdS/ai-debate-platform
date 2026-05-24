from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel


class Message(BaseModel):
    """Represents a single message in the debate."""
    role: str
    content: str


class DebateSession(BaseModel):
    """Represents the entire state of a debate."""
    topic: str
    stance_a: str
    stance_b: str
    history: list[Message] = []
    winner: str = ""
    scores: dict = {}


@dataclass
class DebateMessage:
    sender: str
    content: str
    round_num: int


@dataclass
class DebateRound:
    round_num: int
    pro_message: DebateMessage
    con_message: DebateMessage


@dataclass
class DebateResult:
    topic: str
    rounds: list[DebateRound] = field(default_factory=list)
    winner: str = ""      # "Pro" or "Contra" — never empty
    reasoning: str = ""


@dataclass
class AgentDecision:
    agent_name: str
    decision: str
    confidence: float     # 0.0–1.0
    reasoning: str
