# TODO — AI Debate Platform

## Status
- [x] Done
- [/] In Progress
- [ ] Pending

This tracker now reflects the completed submission scope for the current branch.

---

## Foundation
- [x] Project scaffold created with `uv`, `pyproject.toml`, and tracked dependency lockfile
- [x] Runtime configuration centralized under `config/`
- [x] `.env-example` provided and secrets excluded via `.gitignore`
- [x] Shared configuration loader implemented in `src/shared/config.py`
- [x] Structured logging and rotating file logs implemented in `src/shared/logger.py`
- [x] Source tree organized into `sdk`, `services`, `skills`, `shared`, `ipc`, `gui`, `cli`, and `tools`

## Provider SDK
- [x] `BaseAIClient` abstraction implemented
- [x] OpenAI client implemented
- [x] Gemini client implemented
- [x] Groq client implemented
- [x] Z.ai client implemented
- [x] OpenRouter client implemented
- [x] Mock provider implemented for deterministic demos and tests
- [x] Central provider factory implemented in `src/sdk/factory.py`
- [x] Role-based provider routing implemented in `src/sdk/llm_service.py`

## Rate Limiting And Reliability
- [x] `ApiGatekeeper` implemented with per-provider throttling, timeout, retry, and usage tracking
- [x] Provider limits loaded from `config/rate_limits.json`
- [x] Pricing lookup and token-cost estimation implemented
- [x] Watchdog agent implemented with timeout, heartbeat, cancellation, and restart handling
- [x] Fresh-factory restart flow added for CLI and GUI debate runs
- [x] Safe error redaction added for GUI/API responses

## Debate Engine
- [x] IPC message model implemented
- [x] IPC channel abstraction implemented with timeout handling
- [x] Protocol validation helpers implemented
- [x] Heartbeat support implemented for liveness monitoring
- [x] Debater agent implemented for IPC and direct SDK use
- [x] Judge agent implemented for relay and final verdict generation
- [x] Orchestrator implemented to wire channels and run the debate lifecycle
- [x] Debate memory implemented to track prior claims and URLs
- [x] Context compression implemented for debater prompt history
- [x] Judge transcript truncation applied before final evaluation

## Skills And Prompting
- [x] Skill base types and result models implemented
- [x] Skill registry implemented
- [x] Skill selector implemented
- [x] Rebuttal skill implemented
- [x] Evidence skill implemented
- [x] Citation skill implemented
- [x] Progression skill implemented
- [x] Socratic skill implemented
- [x] Repetition guard skill implemented
- [x] Summarization skill implemented
- [x] Tone moderation skill implemented
- [x] Judge evaluation skill implemented
- [x] Fact safety filter implemented
- [x] Source challenge limiter implemented
- [x] Debater prompt cleanup and rewrite passes implemented

## Search And Evidence
- [x] DuckDuckGo-backed web search tool implemented
- [x] Search quality ranking implemented
- [x] Concurrent query fan-out implemented for evidence gathering
- [x] Search deduplication added across both current-run results and prior-turn URLs
- [x] Mock-provider path kept network-free for repeatable tests

## Interfaces And Output
- [x] CLI entry point implemented in `src/main.py`
- [x] Interactive CLI menu implemented
- [x] GUI HTTP server implemented
- [x] NDJSON streaming debate endpoint implemented
- [x] Static-file path hardening added for the GUI
- [x] Browser payload-to-service builder implemented
- [x] Debate export to Markdown implemented
- [x] Debate export to JSON implemented
- [x] Skill log export implemented
- [x] Session-specific GUI results export implemented

## Testing
- [x] Unit tests added for SDK clients
- [x] Unit tests added for provider routing and factory behavior
- [x] Unit tests added for gatekeeper behavior
- [x] Unit tests added for IPC messages, channels, and protocol rules
- [x] Unit tests added for debater, judge, and orchestrator behavior
- [x] Unit tests added for skills, search, rate config, logging, exporter, and config loading
- [x] Unit tests added for GUI runner and server safety behavior
- [x] Integration debate-flow test added with `MockAIClient`
- [x] Full suite passing: `401` tests
- [x] Coverage target exceeded: `92.20%`
- [x] Ruff lint checks passing

## Documentation
- [x] `README.md` updated with install, usage, architecture, configuration, and testing guidance
- [x] `docs/PRD.md` updated to match implemented provider and agent scope
- [x] `docs/PLAN.md` included for architecture overview
- [x] `docs/PRD_ipc.md` included for IPC design
- [x] `docs/PRD_gatekeeper.md` updated to match actual gatekeeper behavior
- [x] `docs/PRD_watchdog.md` included for watchdog design
- [x] `docs/TESTING.md` updated with current commands and examples
- [x] `docs/LIMITATIONS.md` updated to match current runtime behavior
- [x] `docs/REQUIREMENTS_TRACEABILITY.md` updated to match implementation reality
- [x] Latest debate transcript moved into tracked docs as `docs/debate_transcript.md`
- [x] Latest skill usage log moved into tracked docs as `docs/skill_log.md`

## Submission Readiness
- [x] Production Python files in `src/` verified under 150 physical lines
- [x] Hardcoded runtime defaults moved into `config/setup.json`
- [x] Stale SDK and server wording removed from docs
- [x] Old ignored generated Markdown artifacts moved into tracked documentation
- [x] Removed obsolete `docs/DEMO_TRANSCRIPT.md`
- [x] Removed obsolete `scripts/` helper file
- [x] Removed unused `knowledge/` directory
- [x] GUI screenshot item explicitly closed for the current submission set
