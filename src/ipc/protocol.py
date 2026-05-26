"""
IPC protocol rules: route validation, message schema validation.
Enforces Debater → Judge → Debater; no direct Debater↔Debater.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ProtocolError(ValueError):
    """Raised when a message violates the IPC protocol."""


_DEBATER_TOKENS = frozenset({"debater_a", "debater_b", "pro", "contra", "debater"})
_JUDGE_TOKENS   = frozenset({"judge"})

_MSG_NEEDS_PAYLOAD = frozenset({"ARGUMENT", "RELAY", "VERDICT"})
_VALID_MSG_TYPES   = frozenset({"ARGUMENT", "RELAY", "VERDICT",
                                 "SHUTDOWN", "HEARTBEAT", "ERROR"})
_VALID_SENDERS     = frozenset({
    "debater_a", "debater_b", "pro", "contra",
    "judge", "orchestrator",
})


def _is_debater(name: str) -> bool:
    return name.lower() in _DEBATER_TOKENS or name.lower().startswith("debater")


def validate_route(sender: str, receiver: str) -> None:
    """Raise ProtocolError if the sender→receiver route is forbidden."""
    if _is_debater(sender) and _is_debater(receiver):
        raise ProtocolError(
            f"Direct Debater→Debater communication forbidden: "
            f"'{sender}' → '{receiver}'. All messages must route through the judge."
        )
    logger.debug("route OK: %s → %s", sender, receiver)


def validate_schema(msg_type: str, sender: str, payload: str, round_num: int) -> None:
    """Raise ProtocolError if the message schema is invalid."""
    if msg_type not in _VALID_MSG_TYPES:
        raise ProtocolError(f"Unknown MessageType '{msg_type}'")
    if msg_type in _MSG_NEEDS_PAYLOAD and not payload.strip():
        raise ProtocolError(f"MessageType '{msg_type}' requires non-empty payload")
    if round_num < 0:
        raise ProtocolError(f"round_num must be >= 0, got {round_num}")


def validate_message(msg: object) -> None:
    """Full validation: route + schema. Accepts any object with the right fields."""
    validate_route(msg.sender, msg.receiver)          # type: ignore[attr-defined]
    validate_schema(
        str(msg.msg_type),                             # type: ignore[attr-defined]
        msg.sender,                                    # type: ignore[attr-defined]
        msg.payload,                                   # type: ignore[attr-defined]
        msg.round_num,                                 # type: ignore[attr-defined]
    )
