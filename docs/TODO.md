# TODO - AI Debate Platform

This document is the full project tracker for the AI Debate Platform. It is written as the task list we should have maintained from the start of the project, covering planning, implementation, verification, documentation, submission polish, and future work.

Current state: the main submission scope is complete. Open items at the bottom are optional future improvements, not blockers for the current handoff.

Last documented verification: 2026-05-30.

## Definition Of Done

- [x] The platform runs a structured debate between two AI debaters and one AI judge.
- [x] Debater A and Debater B argue opposing stances across configurable rounds.
- [x] The judge relays messages, evaluates the transcript, scores both sides, and declares a winner.
- [x] Agents communicate through typed IPC queue channels instead of direct calls.
- [x] Provider access is routed through an SDK layer and guarded by rate-limit/retry logic.
- [x] CLI and browser GUI workflows both exist.
- [x] Mock mode works without API keys or network calls.
- [x] Debate output can be exported as Markdown, JSON, and skill logs.
- [x] Runtime settings are loaded from config files.
- [x] Tests run deterministically offline.
- [x] Coverage stays above the required 85% threshold.
- [x] Ruff linting passes.
- [x] Production source files under `src/` stay at or below 150 physical lines.
- [x] Secrets are not committed.
- [x] Documentation is complete enough for a grader to install, run, inspect, and verify the project.

## Phase 0 - Project Understanding And Requirements

- [x] Define the project goal: a multi-agent AI debate platform, not a single prompt script.
- [x] Identify required actors: Pro debater, Contra debater, Judge, and User/Evaluator.
- [x] Define the debate lifecycle: setup, turn-taking, judge relay, final verdict, and export.
- [x] Define default debate size as 10 rounds, producing 20 debater turns.
- [x] Decide that the judge controls message relay and final scoring.
- [x] Decide that debaters should not call each other directly.
- [x] Require a deterministic mock path so the project can be graded without paid API access.
- [x] Require real provider support for OpenAI, Gemini, Groq, ZAI, and OpenRouter.
- [x] Require CLI and GUI entry points.
- [x] Require exported artifacts for transcript, verdict, usage, and skill logs.
- [x] Require professional software checks: `uv`, Ruff, pytest, coverage, config-driven settings, and no committed secrets.
- [x] Capture product requirements in `docs/PRD.md`.
- [x] Capture architecture and implementation planning in `docs/PLAN.md`.
- [x] Capture requirement-to-code mapping in `docs/REQUIREMENTS_TRACEABILITY.md`.

## Phase 1 - Repository And Tooling Setup

- [x] Create the Python project structure.
- [x] Add `pyproject.toml` with project metadata and dependencies.
- [x] Set Python version support to Python 3.12+.
- [x] Add `.python-version`.
- [x] Use `uv` for dependency management.
- [x] Commit `uv.lock` so dependency resolution is reproducible.
- [x] Add Ruff configuration.
- [x] Add pytest configuration.
- [x] Add coverage configuration with `fail_under = 85`.
- [x] Add `pytest-asyncio` support for async services and IPC tests.
- [x] Add `.gitignore` rules for local env files, caches, logs, and generated outputs.
- [x] Add `.env.example` as the safe public environment template.
- [x] Ensure `.env` remains ignored.
- [x] Add a `Makefile` with common development commands.
- [x] Add `.pre-commit-config.yaml` for repository quality checks.
- [x] Add `.secrets.baseline` for secret scanning support.

## Phase 2 - Project Layout

- [x] Create `src/` as the production package root.
- [x] Create `src/sdk/` for provider clients, provider factory, and LLM routing.
- [x] Create `src/services/` for debaters, judge, orchestrator, watchdog, exporter, memory, prompt helpers, and cleanup.
- [x] Create `src/ipc/` for message models, protocol enums, heartbeat support, and queue channels.
- [x] Create `src/skills/` for skill contracts, skill implementations, registry, and selector.
- [x] Create `src/shared/` for config loading, logging, constants, version, rate config, and gatekeeper.
- [x] Create `src/gui/` for the GUI server, runner, service builder, path handling, and responses.
- [x] Create `src/cli/` for command-line and interactive menu workflows.
- [x] Create `src/tools/` for web search and search quality helpers.
- [x] Create `src/models/` for debate-related data models.
- [x] Create `tests/unit/` and `tests/integration/`.
- [x] Create `config/` for runtime configuration.
- [x] Create `docs/` for project documentation and sample outputs.
- [x] Create `gui/` for browser assets.
- [x] Keep production modules small enough to satisfy the 150-line source cap.

## Phase 3 - Configuration System

- [x] Add `config/setup.json` for debate defaults, server settings, watchdog settings, provider defaults, and skill defaults.
- [x] Add `config/models.json` for provider and role model choices.
- [x] Add `config/rate_limits.json` for provider RPM, retry, timeout, and retry-after settings.
- [x] Add `config/pricing.json` for estimated token costs.
- [x] Add `config/skills.json` for skill enablement and priority weights.
- [x] Add `config/skills_prompts.json` for reusable skill prompt fragments.
- [x] Implement config loading in `src/shared/config.py`.
- [x] Implement rate-limit config loading in `src/shared/rate_config.py`.
- [x] Load debate round limits from config instead of hardcoding them.
- [x] Load provider options and labels from config.
- [x] Load watchdog timing from config.
- [x] Load logging settings from config.
- [x] Remove unsupported Anthropic config/template entries.
- [x] Add tests for config loading, default values, provider lists, env template correctness, and rate-limit parsing.

## Phase 4 - Provider SDK

- [x] Define `BaseAIClient` as the shared provider contract.
- [x] Define common request and response handling expectations for provider clients.
- [x] Add SDK-specific exceptions.
- [x] Implement `OpenAIClient`.
- [x] Implement `GeminiClient`.
- [x] Implement `GroqClient`.
- [x] Implement `ZaiClient`.
- [x] Implement `OpenRouterClient`.
- [x] Implement `MockAIClient`.
- [x] Ensure real providers read API keys from environment variables only.
- [x] Ensure mock provider does not require an API key.
- [x] Add `AIClientFactory` for consistent provider creation.
- [x] Add `LLMService` for role-based provider and model routing.
- [x] Support separate providers for Debater A, Debater B, and Judge.
- [x] Add provider-specific tests.
- [x] Add factory tests.
- [x] Add LLM service routing tests.
- [x] Add API-key behavior tests.

## Phase 5 - API Gatekeeper And Reliability

- [x] Design `ApiGatekeeper` as the only path around outbound model calls.
- [x] Add per-provider throttling.
- [x] Add provider locks to serialize calls where needed.
- [x] Add retry handling.
- [x] Add timeout handling.
- [x] Add retry-after support.
- [x] Add backpressure behavior for provider rate limits.
- [x] Add usage tracking.
- [x] Add token accounting.
- [x] Add estimated cost tracking from `config/pricing.json`.
- [x] Add safe error redaction.
- [x] Ensure GUI/API errors do not leak local secrets.
- [x] Add gatekeeper unit tests for success, retry, timeout, rate pressure, usage, and cost behavior.

## Phase 6 - IPC Layer

- [x] Define message types for relay, argument, verdict, heartbeat, error, and shutdown flows.
- [x] Implement typed IPC message models.
- [x] Include role, payload, metadata, and timestamp information in messages.
- [x] Implement message serialization and deserialization.
- [x] Implement async queue-backed `IpcChannel`.
- [x] Add send and receive behavior with timeout support.
- [x] Add heartbeat support for supervision.
- [x] Add protocol validation for legal message flow.
- [x] Use explicit IPC channels between orchestrator, debaters, and judge.
- [x] Add IPC message tests.
- [x] Add IPC channel tests.
- [x] Add IPC protocol tests.

## Phase 7 - Debate Domain Models And Memory

- [x] Add debate data models for turns, arguments, verdicts, and run results.
- [x] Track debate topic, stances, roles, providers, and round numbers.
- [x] Implement debate memory for prior claims.
- [x] Track repeated ideas across turns.
- [x] Track previously referenced URLs.
- [x] Add context compression for long transcript history.
- [x] Add judge transcript bounds using `judge_max_transcript_entries`.
- [x] Add word-limit enforcement for debater and judge outputs.
- [x] Add tests for debate models, memory, context compression, and output limits.

## Phase 8 - Agent Services

- [x] Implement `BaseAgent`.
- [x] Implement Debater A / Pro behavior.
- [x] Implement Debater B / Contra behavior.
- [x] Implement Judge behavior.
- [x] Implement Debate Orchestrator lifecycle.
- [x] Seed the debate by sending the opening relay to Debater A.
- [x] Alternate turns through judge relay.
- [x] Preserve each side's stance across all turns.
- [x] Record the transcript as the debate progresses.
- [x] Ask the judge to evaluate the final transcript.
- [x] Send verdict output back to the orchestrator.
- [x] Send shutdown messages at the end of the debate.
- [x] Add debater prompt construction.
- [x] Add judge prompt construction.
- [x] Add response cleanup helpers.
- [x] Add rewrite passes for repeated or poorly structured responses.
- [x] Split large service responsibilities into smaller modules to satisfy the source line cap.
- [x] Add unit tests for base agent, debater, judge, orchestrator, prompts, relay logic, and cleanup.

## Phase 9 - Debate Skills

- [x] Define `BaseSkill`.
- [x] Define skill result models.
- [x] Build skill registry.
- [x] Build skill selector.
- [x] Load skill settings from config.
- [x] Implement `RebuttalSkill`.
- [x] Implement `EvidenceSkill`.
- [x] Implement `CitationSkill`.
- [x] Implement `ProgressionSkill`.
- [x] Implement `SocraticSkill`.
- [x] Implement `RepetitionGuardSkill`.
- [x] Implement `SummarizationSkill`.
- [x] Implement `ToneModerationSkill`.
- [x] Implement `JudgeEvaluationSkill`.
- [x] Implement `FactSafetyFilter`.
- [x] Implement `SourceChallengeLimiter`.
- [x] Inject selected skill guidance into debater prompts.
- [x] Record selected skills per turn.
- [x] Export skill logs after debate runs.
- [x] Add tests for skill behavior, registry behavior, selector behavior, prompt integration, repetition detection, and skill logs.

## Phase 10 - Web Search And Evidence

- [x] Add a web search tool abstraction.
- [x] Use `ddgs` for DuckDuckGo-backed search.
- [x] Add graceful fallback when search returns no results or fails.
- [x] Disable web search for mock-mode runs to keep tests deterministic.
- [x] Add search quality helpers for filtering, scoring, and ranking results.
- [x] Integrate evidence enrichment into debater behavior.
- [x] Keep search and evidence logic outside the core debater file to maintain the line cap.
- [x] Add tests for web search behavior.
- [x] Add tests for search quality ranking.
- [x] Add tests for debater evidence policy.

## Phase 11 - Watchdog

- [x] Design watchdog supervision for long-running debate tasks.
- [x] Implement heartbeat tracking.
- [x] Implement timeout detection.
- [x] Implement cancellation handling.
- [x] Implement restart behavior within configured limits.
- [x] Load watchdog timeout, poll interval, and max failures from config.
- [x] Add watchdog helper functions.
- [x] Add tests for heartbeat, timeout, cancellation, and restart behavior.
- [x] Document watchdog design in `docs/PRD_watchdog.md`.

## Phase 12 - CLI Workflow

- [x] Add `src/main.py` as the module entry point.
- [x] Add CLI arguments for topic, stance A, stance B, provider A, provider B, judge provider, and rounds.
- [x] Add `--version` output.
- [x] Add `--help` coverage.
- [x] Add interactive menu flow in `src/cli/menu.py`.
- [x] Add CLI runner service wiring in `src/cli/runner.py`.
- [x] Ensure CLI can run with mock providers and no API keys.
- [x] Ensure CLI can run with real providers when API keys exist.
- [x] Add tests for CLI parsing, version output, and runner behavior.

## Phase 13 - Browser GUI

- [x] Build `gui/index.html`.
- [x] Build `gui/styles.css`.
- [x] Build `gui/app.js`.
- [x] Add topic, stance, provider, judge provider, and rounds controls.
- [x] Include all supported providers in the GUI provider dropdowns.
- [x] Include OpenRouter in the judge provider dropdown.
- [x] Clamp rounds to configured minimum and maximum values.
- [x] Fall back safely on invalid rounds payloads.
- [x] Implement `src/gui/server.py` using the standard library HTTP server.
- [x] Implement static file serving for the browser assets.
- [x] Harden static file path handling.
- [x] Implement `src/gui/service_builder.py`.
- [x] Implement `src/gui/debate_runner.py`.
- [x] Implement structured GUI responses.
- [x] Implement NDJSON debate streaming.
- [x] Stream start, message, judging, verdict, and error events to the browser.
- [x] Add process-local concurrency control for debate runs.
- [x] Add tests for GUI runner payload handling.
- [x] Add tests for service builder behavior.
- [x] Add tests for server safety and static path protection.
- [x] Add tests that verify GUI provider options stay aligned with supported providers.

## Phase 14 - Exported Outputs

- [x] Implement Markdown transcript export.
- [x] Implement JSON result export.
- [x] Include debate topic, stances, rounds, providers, turns, and verdict in exports.
- [x] Include token usage summaries where available.
- [x] Include estimated provider cost summaries where available.
- [x] Export skill usage logs.
- [x] Add current sample debate transcript at `docs/debate_transcript.md`.
- [x] Add current sample skill log at `docs/skill_log.md`.
- [x] Remove the older demo transcript path and standardize on the current docs output names.
- [x] Add exporter tests.

## Phase 15 - Logging And Error Handling

- [x] Add shared logging utilities.
- [x] Add rotating log behavior.
- [x] Load log directory and retention settings from config.
- [x] Log debate lifecycle events.
- [x] Log provider and gatekeeper failures safely.
- [x] Surface GUI errors as structured responses.
- [x] Avoid leaking API keys in exceptions, logs, or GUI output.
- [x] Add logger tests and error-redaction coverage.

## Phase 16 - Automated Tests

- [x] Add unit tests for SDK base client behavior.
- [x] Add unit tests for each provider client.
- [x] Add unit tests for provider factory.
- [x] Add unit tests for LLM service routing.
- [x] Add unit tests for config loading.
- [x] Add unit tests for rate config loading.
- [x] Add unit tests for gatekeeper behavior.
- [x] Add unit tests for IPC messages, channels, and protocol.
- [x] Add unit tests for debater behavior.
- [x] Add unit tests for judge behavior.
- [x] Add unit tests for orchestrator behavior.
- [x] Add unit tests for watchdog behavior.
- [x] Add unit tests for debate memory.
- [x] Add unit tests for prompt builders.
- [x] Add unit tests for response cleanup.
- [x] Add unit tests for exporter behavior.
- [x] Add unit tests for skills and skill selector.
- [x] Add unit tests for web search and search quality.
- [x] Add unit tests for GUI runner and server.
- [x] Add unit tests for CLI behavior.
- [x] Add integration test for full debate flow with `MockAIClient`.
- [x] Add submission-readiness tests for source line caps.
- [x] Add submission-readiness tests for `.env.example`.
- [x] Add submission-readiness tests for GUI provider options.
- [x] Verify full suite result: `419 passed`.
- [x] Verify coverage result: `91.76%`.
- [x] Verify Ruff result: `All checks passed!`.

## Phase 17 - Documentation

- [x] Write root `README.md`.
- [x] Add installation instructions.
- [x] Add mock-mode quick start command.
- [x] Add real-provider usage example.
- [x] Add GUI launch instructions.
- [x] Add supported provider table.
- [x] Add configuration table.
- [x] Add architecture diagram.
- [x] Add debate flow diagram.
- [x] Add project structure overview.
- [x] Add screenshots of setup, live transcript, and judge verdict.
- [x] Add evaluation evidence table.
- [x] Add key grading artifact links.
- [x] Write `docs/PRD.md`.
- [x] Write `docs/PLAN.md`.
- [x] Write `docs/PRD_ipc.md`.
- [x] Write `docs/PRD_gatekeeper.md`.
- [x] Write `docs/PRD_watchdog.md`.
- [x] Write `docs/TESTING.md`.
- [x] Write `docs/LIMITATIONS.md`.
- [x] Write `docs/REQUIREMENTS_TRACEABILITY.md`.
- [x] Write and revise this project tracker.

## Phase 18 - Submission Polish

- [x] Confirm all production files in `src/` satisfy the 150-line source cap.
- [x] Confirm no hardcoded runtime settings remain where config should be used.
- [x] Confirm `.env.example` contains placeholders only.
- [x] Confirm `.env` is ignored.
- [x] Confirm unsupported provider templates were removed.
- [x] Confirm mock mode works without API keys.
- [x] Confirm README commands are usable.
- [x] Confirm tests are deterministic and offline.
- [x] Confirm generated caches are not part of the polished submission.
- [x] Confirm runtime output directories are ignored where appropriate.
- [x] Confirm docs align with the actual codebase.
- [x] Confirm requirement traceability marks all 33 tracked requirements as done.
- [x] Push completed committed project state to GitHub `master`.

## Current Verified Commands

- [x] `uv sync`
- [x] `uv run pytest -q`
- [x] `uv run pytest --cov=src --cov-report=term-missing`
- [x] `uv run ruff check src tests`
- [x] `uv run pytest tests/unit/test_submission_readiness.py -q`
- [x] `uv run python -m src.main --help`
- [x] `uv run python -m src.main --version`
- [x] `uv run python -m src.gui.server`

## Known Boundaries Documented

- [x] Free-tier and smaller models may hallucinate citations.
- [x] Repetition can still happen because final wording depends on model behavior.
- [x] Word-limit enforcement may truncate overlong responses.
- [x] Free-tier provider rate limits may slow full 10-round debates.
- [x] Provider model IDs can change and may require config updates.
- [x] GUI streams completed debate events, not token-level model output.
- [x] DuckDuckGo-backed search can return empty results or throttle requests.
- [x] The lightweight GUI server is suitable for local demo use, not production multi-user hosting.
- [x] There is no persistent database, account system, or session history service.
- [x] These boundaries are documented in `docs/LIMITATIONS.md`.

## Optional Future Work

- [ ] Add GitHub Actions for automated Ruff, pytest, and coverage checks.
- [ ] Add token-level streaming for providers that support it.
- [ ] Add persistent multi-session storage for GUI debates.
- [ ] Add account/session support if the GUI becomes a hosted app.
- [ ] Add structured academic citation APIs such as Semantic Scholar, CrossRef, or arXiv.
- [ ] Add stronger prompt-injection defenses for retrieved web evidence.
- [ ] Add browser automation tests for the full GUI workflow.
- [ ] Add batch debate runs for provider/model comparison experiments.
- [ ] Add judge confidence scores and rubric explanations.
- [ ] Add release notes or a changelog if the project continues beyond the assignment.
