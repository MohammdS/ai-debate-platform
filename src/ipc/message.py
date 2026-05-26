import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    ARGUMENT = "ARGUMENT"   # debater sends an argument to judge
    RELAY    = "RELAY"      # judge forwards argument to the other debater
    VERDICT  = "VERDICT"    # judge issues final verdict to orchestrator
    SHUTDOWN = "SHUTDOWN"   # orchestrator/judge signals end of debate


@dataclass
class DebateMessage:
    """JSON-serializable envelope for all inter-agent IPC messages."""

    msg_type:  MessageType
    sender:    str           # "debater_a" | "debater_b" | "judge" | "orchestrator"
    receiver:  str
    payload:   str           # the actual text content
    round_num: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "msg_type":  self.msg_type.value,
            "sender":    self.sender,
            "receiver":  self.receiver,
            "payload":   self.payload,
            "round_num": self.round_num,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DebateMessage":
        return cls(
            msg_type=MessageType(data["msg_type"]),
            sender=data["sender"],
            receiver=data["receiver"],
            payload=data["payload"],
            round_num=data["round_num"],
            timestamp=data.get("timestamp", time.time()),
        )
