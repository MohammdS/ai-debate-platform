# PRD - IPC Layer

## Problem

Direct function calls between agents hide the communication boundary and make the debate look like one shared procedure rather than independent agents exchanging messages.

## Requirement

All inter-agent communication must cross an explicit IPC boundary. The debate flow must be:

```text
Debater A -> Judge -> Debater B
Debater B -> Judge -> Debater A
Judge -> Orchestrator for final verdict
```

Debaters must never call each other directly.

## Solution

`src/ipc/` implements typed queue-based IPC:

- `MessageType`: `ARGUMENT`, `RELAY`, `VERDICT`, `SHUTDOWN`, `HEARTBEAT`
- `DebateMessage`: message envelope with sender, receiver, payload, round, and timestamp
- `IpcChannel`: named `asyncio.Queue[str]` wrapper that serializes messages to JSON

## Channel Topology

```text
Debater A outbox -> a_to_judge -> Judge inbox A
Judge outbox B  -> judge_to_b -> Debater B inbox
Debater B outbox -> b_to_judge -> Judge inbox B
Judge outbox A  -> judge_to_a -> Debater A inbox
Judge verdict   -> verdict_ch -> Orchestrator
```

## Bootstrap

The orchestrator sends one synthetic `RELAY` to Debater A before `asyncio.gather` starts. This avoids startup deadlock while preserving the judge-mediated flow.

## Files

- `src/ipc/message.py`
- `src/ipc/channel.py`
- `src/ipc/protocol.py`
- `src/ipc/heartbeat.py`
- `src/services/debater_ipc.py`
- `src/services/judge.py`
- `src/services/orchestrator.py`

## Tests

- `tests/unit/test_ipc_message.py`
- `tests/unit/test_ipc_channel.py`
- `tests/unit/test_ipc_protocol.py`
- `tests/unit/test_debater.py`
- `tests/unit/test_judge.py`
- `tests/unit/test_orchestrator.py`
