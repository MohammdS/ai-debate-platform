# Testing Guide

The test suite is designed for offline, deterministic grading. Unit and integration tests use mocks or `MockAIClient`, so no API keys are required.

## Current Verified Result

Last verified on 2026-05-30:

```text
uv run pytest -q
419 passed

uv run pytest --cov=src --cov-report=term-missing
Total coverage: 91.76%
Required test coverage of 85.0% reached.

uv run ruff check src tests
All checks passed!
```

## Test Layout

```text
tests/
|-- integration/
|   `-- test_debate_flow.py      # End-to-end debate with MockAIClient
`-- unit/
    |-- test_base_agent.py       # BaseAgent abstraction
    |-- test_base_client.py      # BaseAIClient and API-key behavior
    |-- test_config.py           # Config loading and env template checks
    |-- test_debater.py          # Debater generation, cleanup, memory, web-search policy
    |-- test_exporter.py         # Markdown/JSON export and token summary
    |-- test_factory.py          # Provider factory
    |-- test_gatekeeper.py       # Rate limits, retries, token/cost accounting
    |-- test_gui_runner.py       # GUI payload-to-service runner
    |-- test_ipc_*.py            # IPC messages, channel, protocol
    |-- test_judge.py            # Relay and final verdict behavior
    |-- test_llm_service.py      # Role-based provider/model routing
    |-- test_quality.py          # Debate structure, roles, repetition, safety
    |-- test_search_quality.py   # Search ranking and filtering
    |-- test_server.py           # GUI server safety behavior
    |-- test_skills.py           # Skill classes and selector
    |-- test_submission_readiness.py # Line cap, env template, GUI provider options
    |-- test_watchdog_agent.py   # Heartbeat, timeout, recovery
    `-- test_*_client.py         # Provider-specific SDK clients
```

## Required Commands

```bash
# Run every test
uv run pytest -q

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run the linter
uv run ruff check src tests

# Run submission-readiness checks only
uv run pytest tests/unit/test_submission_readiness.py -q
```

## Coverage Policy

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
omit = ["src/main.py", "src/gui/server.py", "*/tests/*"]

[tool.coverage.report]
fail_under = 85
show_missing = true
```

Entry points are excluded because process-level server/CLI behavior is covered through focused tests and integration paths.

## Main Scenarios Covered

- Debate produces the expected Pro/Contra turn structure and a judge verdict.
- Roles and stances remain stable across all turns.
- `SkillSelector` selects and logs skills.
- `RepetitionGuardSkill` detects recycled arguments.
- `ApiGatekeeper` handles rate limits, timeouts, retries, and token/cost accounting.
- `LLMService` routes roles to provider clients correctly.
- Mock-mode debates complete without API keys or network calls.
- IPC channels send, receive, serialize, and time out typed messages.
- GUI payloads build safe debate services, clamp rounds, and include supported providers.
- The repository stays submission-ready: source files remain <=150 lines and `.env.example` matches supported providers.

## CI-Friendly Command Set

```bash
uv run ruff check src tests
uv run pytest --cov=src --cov-report=xml
```
