# PRD — IPC Layer

## Problem
Original implementation used direct async function calls in a single process with a shared history list. Agents were not truly independent — no message-passing boundary existed between them.

## Requirement
The professor's lecture states: *"The agent IS a process. Two agents = two processes running in parallel. Communication between agents is exactly IPC — Signals, FIFO, Queues, Sockets."*

All inter-agent communication must cross an explicit IPC boundary. The debate must flow: child → father → child (no direct debater-to-debater contact).

## Solution

### Message Protocol (`src/ipc/message.py`)
`DebateMessage` dataclass — the wire envelope:

| Field | Type | Description |
|---|---|---|
| `msg_type` | `MessageType` | ARGUMENT / RELAY / VERDICT / SHUTDOWN |
| `sender` | `str` | Originating agent name |
| `receiver` | `str` | Target agent name |
| `payload` | `str` | Text content |
| `round_num` | `int` | Current debate round |
| `timestamp` | `float` | Unix timestamp (auto-set) |

Messages are serialized to **JSON strings** on the queue (not Python objects) to make the IPC boundary explicit.

### Channel (`src/ipc/channel.py`)
`IpcChannel` wraps `asyncio.Queue[str]`:
- `send(msg)` — serialize to JSON, put on queue
- `receive()` — `asyncio.wait_for(queue.get(), timeout)` — raises `TimeoutError` on timeout
- Named for logging clarity (`"a_to_judge"`, `"judge_to_b"`, etc.)

### Channel Topology
```
a_to_judge : debater_a.outbox  → judge.inbox_a
b_to_judge : debater_b.outbox  → judge.inbox_b
judge_to_a : judge.outbox_a    → debater_a.inbox
judge_to_b : judge.outbox_b    → debater_b.inbox
verdict_ch : judge.verdict_ch  → orchestrator
```

### Bootstrap
Both debater_a and judge block waiting for the first message. Orchestrator sends a synthetic `RELAY` to debater_a before `asyncio.gather` starts.

## Files Changed
- `src/ipc/__init__.py` — new
- `src/ipc/message.py` — new
- `src/ipc/channel.py` — new
- `src/services/debater.py` — added `inbox`, `outbox`, `run()`
- `src/services/judge.py` — added channel attrs, `run(total_rounds)`
- `src/services/orchestrator.py` — replaced sequential loop with `_wire_channels()` + `asyncio.gather`

## Tests
- `tests/unit/test_ipc_message.py` — round-trip, enum behaviour, timestamp
- `tests/unit/test_ipc_channel.py` — send/receive, timeout, ordering
- `tests/unit/test_debater.py` — run() loop with mock channels
- `tests/unit/test_judge.py` — run() mediator with mock channels
- `tests/unit/test_orchestrator.py` — full end-to-end with mock client
