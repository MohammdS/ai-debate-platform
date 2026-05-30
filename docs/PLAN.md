# Architecture And Implementation Plan - AI Debate Platform

## 1. System Architecture

```text
CLI / GUI
   |
   v
LLMService -> AIClientFactory -> Provider Client
   |
   v
ApiGatekeeper
   |
   v
Debater A ----\
               -> typed IPC channels -> Judge -> verdict channel -> Orchestrator
Debater B ----/
   |
   v
SkillSelector -> configured skill pool
```

## 2. Layer Map

| Layer | Path | Responsibility |
|---|---|---|
| GUI frontend | `gui/` | Browser form, live transcript, verdict display |
| GUI backend | `src/gui/` | HTTP server, payload validation, NDJSON streaming |
| CLI | `src/cli/`, `src/main.py` | Argument parser and interactive terminal flow |
| IPC | `src/ipc/` | Message envelope, protocol enum, typed queue channels |
| SDK | `src/sdk/` | Provider clients, factory, role-based service routing |
| Services | `src/services/` | Debater, Judge, Orchestrator, Watchdog, exporter, memory |
| Shared | `src/shared/` | Config, logging, constants, gatekeeper, version |
| Skills | `src/skills/` | Debate skill implementations and selector |
| Tools | `src/tools/` | Web search and search quality helpers |

## 3. Debate Flow

1. The user submits topic, stances, providers, and rounds from CLI or GUI.
2. `LLMService` builds provider clients and gatekeepers for each role.
3. `DebateOrchestrator` wires five typed IPC channels.
4. The orchestrator seeds the first `RELAY` to Debater A.
5. Debaters generate arguments, select skills, and send `ARGUMENT` messages to the judge.
6. The judge records each turn and relays it to the opposing debater.
7. After the configured rounds, the judge evaluates the transcript and sends `VERDICT`.
8. Results are exported to Markdown, JSON, and skill-log files.

## 4. GUI Streaming Flow

```text
Browser form
   |
   | POST /api/debates/stream
   v
ThreadingHTTPServer
   |
   v
stream_debate_from_payload()
   |
   v
Judge event queue -> NDJSON events -> browser transcript
```

Events include `start`, `message`, `judging`, `verdict`, and `error`.

## 5. Key Design Decisions

- Use JSON strings on queues so the IPC boundary is explicit.
- Keep debaters independent; they never call each other directly.
- Keep provider differences inside SDK clients.
- Keep external-call reliability inside `ApiGatekeeper`.
- Use `MockAIClient` for deterministic tests and demos.
- Split shared helpers into small modules so source files remain under the assignment line cap.

## 6. Verification

- `uv run ruff check src tests`
- `uv run pytest -q`
- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run pytest tests/unit/test_submission_readiness.py -q`
