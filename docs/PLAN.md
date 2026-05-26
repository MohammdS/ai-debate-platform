# Architecture & Implementation Plan — AI Debate Platform

## 1. System Architecture

```
┌─────────────────────────────────────────────┐
│  Entry Points                               │
│  CLI: src/main.py   GUI: src/gui/server.py  │
└────────────────┬────────────────────────────┘
                 │
        DebateOrchestrator
          ├── _wire_channels()     — creates 5 IpcChannel objects
          ├── _seed_first_turn()   — bootstrap RELAY to debater_a
          └── asyncio.gather(
                  Debater_A.run(),   ← IPC process coroutine
                  Debater_B.run(),   ← IPC process coroutine
                  Judge.run()        ← IPC mediator + event emitter
              )
```

## 2. Layer Map

| Layer | Path | Responsibility |
|---|---|---|
| GUI frontend | `gui/` | `index.html`, `styles.css`, `app.js` — runs in browser |
| GUI backend | `src/gui/` | HTTP server (port 8000), debate runner, streaming |
| IPC | `src/ipc/` | Message envelope, typed queue channels |
| SDK | `src/sdk/` | Abstract `BaseAIClient`, provider implementations, factory |
| Services | `src/services/` | Debater, Judge, Orchestrator |
| Shared | `src/shared/` | Config, Gatekeeper, Logger |
| Models | `src/models/` | Pydantic data models |

## 3. GUI Architecture

```
Browser (gui/app.js)
    │  POST /api/debates/stream   (NDJSON streaming)
    ▼
src/gui/server.py  (ThreadingHTTPServer :8000)
    │  asyncio.run(_write_stream)
    ▼
src/gui/debate_runner.py  stream_debate_from_payload()
    ├── creates asyncio.Queue  event_queue
    ├── wires event_queue → judge.event_queue
    ├── asyncio.create_task(orchestrator.run_debate())  ← full IPC debate
    └── yields events as judge emits them:
            {"type": "start"}
            {"type": "message", "message": {...}, "count": N}  ← per argument
            {"type": "judging"}
            {"type": "verdict", "history": [...], "verdict": "..."}
```

**Live event flow:** Judge emits to `event_queue` after relaying each message. Streaming generator reads the queue and yields JSON lines to the browser in real time.

## 3. IPC Channel Topology

```
Debater_A ──[a_to_judge]──► Judge ──[judge_to_b]──► Debater_B
Debater_A ◄─[judge_to_a]── Judge ◄─[b_to_judge]── Debater_B
                                └──[verdict_ch]──► Orchestrator
```

## 4. Message Flow (one round)
1. Orchestrator seeds synthetic `RELAY` → `judge_to_a` → Debater A inbox
2. Debater A generates argument → sends `ARGUMENT` → `a_to_judge` → Judge inbox_a
3. Judge logs, prints, relays → `judge_to_b` → Debater B inbox
4. Debater B generates counter → sends `ARGUMENT` → `b_to_judge` → Judge inbox_b
5. Judge logs, prints, relays → `judge_to_a` → Debater A inbox
6. Repeat for N rounds
7. Judge calls `evaluate()`, sends `VERDICT` → `verdict_ch` → Orchestrator
8. Judge sends `SHUTDOWN` to both debaters

## 5. Key Design Decisions
- **JSON on wire:** Messages serialized to JSON strings on the queue, not Python objects — makes IPC boundary explicit.
- **Separate judge inboxes:** `inbox_a` and `inbox_b` enforce turn order.
- **Bootstrap seed:** Orchestrator sends one synthetic RELAY to debater_a before `gather` to avoid deadlock.
- **Backward-compatible APIs:** `get_argument()` and `evaluate()` preserved for direct SDK use and tests.

## 6. Technology Stack
- `asyncio.Queue` — IPC transport
- `httpx` — async HTTP for LLM API calls
- `pydantic` — data models
- `python-dotenv` — env var loading
- `uv` — dependency management
- `ruff` — linting
- `pytest` / `pytest-asyncio` / `pytest-cov` — testing
