from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    ARGUMENT  = "ARGUMENT"   # debater → judge: argument text
    RELAY     = "RELAY"      # judge  → debater: forwarded opponent argument
    VERDICT   = "VERDICT"    # judge  → orchestrator: final verdict
    SHUTDOWN  = "SHUTDOWN"   # any    → agent: end of debate signal
    HEARTBEAT = "HEARTBEAT"  # any    → any: liveness ping
    ERROR     = "ERROR"      # any    → judge/orchestrator: error report


@dataclass
class DebateMessage:
    """JSON-serialisable envelope for all inter-agent IPC messages."""

    msg_type:  MessageType
    sender:    str           # e.g. "debater_a" | "judge" | "orchestrator"
    receiver:  str
    payload:   str           # text content (empty for HEARTBEAT/SHUTDOWN)
    round_num: int
    timestamp: float = field(default_factory=time.time)
    metadata:  dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "msg_type":  self.msg_type.value,
            "sender":    self.sender,
            "receiver":  self.receiver,
            "payload":   self.payload,
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "metadata":  self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebateMessage:
        return cls(
            msg_type=MessageType(data["msg_type"]),
            sender=data["sender"],
            receiver=data["receiver"],
            payload=data["payload"],
            round_num=data["round_num"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    @classmethod
    def heartbeat(cls, sender: str, receiver: str, round_num: int = 0) -> DebateMessage:
        return cls(MessageType.HEARTBEAT, sender, receiver, "", round_num)

    @classmethod
    def error(cls, sender: str, receiver: str, description: str,
              round_num: int = 0) -> DebateMessage:
        return cls(MessageType.ERROR, sender, receiver, description, round_num)

    def is_heartbeat(self) -> bool:
        return self.msg_type == MessageType.HEARTBEAT

    def is_error(self) -> bool:
        return self.msg_type == MessageType.ERROR
