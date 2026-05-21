
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
