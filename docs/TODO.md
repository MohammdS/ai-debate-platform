# TODO - AI Debate Platform

This tracker reflects the completed submission scope for the current branch.

## Foundation

- [x] Project scaffold created with `uv`, `pyproject.toml`, and tracked `uv.lock`
- [x] Runtime configuration centralized under `config/`
- [x] Canonical `.env.example` provided; `.env` ignored
- [x] Unsupported Anthropic template/config entries removed
- [x] Structured logging and rotating file logs implemented
- [x] Source tree organized into `sdk`, `services`, `skills`, `shared`, `ipc`, `gui`, `cli`, and `tools`

## Provider SDK

- [x] `BaseAIClient` abstraction implemented
- [x] OpenAI, Gemini, Groq, ZAI, OpenRouter, and Mock clients implemented
- [x] Central provider factory implemented in `src/sdk/factory.py`
- [x] Role-based provider routing implemented in `src/sdk/llm_service.py`

## Rate Limiting And Reliability

- [x] `ApiGatekeeper` implemented with per-provider throttling, timeouts, retries, usage tracking, and cost estimates
- [x] Provider limits loaded from `config/rate_limits.json`
- [x] Watchdog agent implemented with timeout, heartbeat, cancellation, and restart handling
- [x] Safe error redaction added for GUI/API responses

## Debate Engine

- [x] IPC message model, channel abstraction, protocol validation, and heartbeat support implemented
- [x] Debater, Judge, and Orchestrator implemented
- [x] Debate memory tracks prior claims and URLs
- [x] Context compression and judge transcript truncation implemented
- [x] Web evidence enrichment split from `debater.py` to keep the debater under the source line cap

## Skills And Prompting

- [x] Skill base types, registry, selector, and result models implemented
- [x] Rebuttal, Evidence, Citation, Progression, Socratic, Repetition Guard, Summarization, Tone Moderation, Judge Evaluation, Fact Safety, and Source Challenge Limiter implemented
- [x] Debater prompt cleanup and rewrite passes implemented

## Interfaces And Output

- [x] CLI entry point and interactive menu implemented
- [x] GUI HTTP server and NDJSON streaming endpoint implemented
- [x] GUI provider dropdowns include all supported providers, including OpenRouter for the judge
- [x] GUI rounds input is clamped and falls back safely on invalid payload values
- [x] Static-file path hardening added for the GUI
- [x] Markdown, JSON, and skill-log export implemented

## Testing

- [x] Unit tests cover SDK clients, routing, gatekeeper behavior, IPC, debater, judge, orchestrator, skills, search, config, exporter, logging, GUI runner, and server safety
- [x] Integration debate-flow test uses `MockAIClient`
- [x] Submission-readiness tests verify the source line cap, env template, and GUI provider options
- [x] Full suite passing: `419` tests
- [x] Coverage target exceeded: `91.76%`
- [x] Ruff lint checks passing

## Documentation

- [x] README updated for AI grading with evidence and verification commands
- [x] PRD, PLAN, IPC, Gatekeeper, Watchdog, Testing, Limitations, and Requirements Traceability docs included
- [x] Latest debate transcript and skill usage log tracked under `docs/`

## Submission Readiness

- [x] Production Python files in `src/` verified under 150 physical lines
- [x] Hardcoded runtime values moved into config files
- [x] Duplicate `.env-example` removed in favor of `.env.example`
- [x] Ignored generated artifacts are excluded from the polished repository
