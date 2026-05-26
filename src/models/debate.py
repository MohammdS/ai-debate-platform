"""Domain models for debate sessions and messages."""
from __future__ import annotations

from pydantic import BaseModel


class Message(BaseModel):
    """A single turn in the debate transcript."""
    role: str
    content: str


class DebateSession(BaseModel):
    """Full state of one debate: topic, stances, history, and outcome."""
    topic: str
    stance_a: str
    stance_b: str
    history: list[Message] = []
    winner: str = ""
    scores: dict = {}
