# Testing Guide

## Test Architecture

```
tests/
├── unit/                        # Isolated unit tests with mocks
│   ├── test_debater.py          # Debater argument generation, skill use
│   ├── test_judge.py            # Judge evaluation, verdict format, IPC relay
│   ├── test_orchestrator.py     # Full debate flow coordination
│   ├── test_skills.py           # All skill classes (can_handle, run, selector)
│   ├── test_gatekeeper.py       # Rate limiting, retry, queue backpressure
│   ├── test_llm_service.py      # Provider routing, client selection
│   ├── test_factory.py          # Client factory creation for all providers
│   ├── test_quality.py          # Debate quality: 20 turns, roles, repetition
│   ├── test_watchdog_agent.py   # Watchdog heartbeat, timeout, recovery
│   ├── test_ipc_channel.py      # asyncio.Queue channel send/receive
│   ├── test_ipc_message.py      # IPCMessage serialisation, fields
│   ├── test_ipc_protocol.py     # Message-type enum, protocol rules
│   ├── test_config.py           # Config loading, validation, defaults
│   ├── test_web_search.py       # Web search tool, failure handling
│   ├── test_base_agent.py       # BaseAgent abstract interface
│   ├── test_base_client.py      # BaseAIClient abstract interface
│   ├── test_exporter.py         # DebateExporter markdown + JSON output
│   ├── test_logger.py           # Structured logger, log rotation
│   ├── test_models.py           # Pydantic model validation
│   ├── test_main_cli.py         # CLI argument parsing, --help, --version
│   ├── test_server.py           # GUI server routes, path safety, semaphore
│   ├── test_gui_runner.py       # GUI async debate runner
│   ├── test_openrouter_client.py# OpenRouter API client
│   ├── test_zai_client.py       # ZAI API client
│   ├── test_groq_client.py      # Groq API client
│   ├── test_gemini_client.py    # Gemini API client
│   ├── test_openai_client.py    # OpenAI API client
│   └── test_exceptions.py      # Custom exception classes
└── integration/
    └── test_debate_flow.py      # End-to-end debate with MockAIClient
```

---

## Test Categories

### Category 1: Debate Structure Tests

Verify the debate produces exactly 20 debater turns (10 rounds × 2 debaters) plus a judge verdict.

```bash
uv run pytest tests/unit/test_quality.py -v -k "turns"
```

### Category 2: Role and Stance Integrity

Verify Pro always defends stance A and Contra always defends stance B — roles never swap.

```bash
uv run pytest tests/unit/test_quality.py -v -k "role"
```

### Category 3: Skill Selection

Verify `SkillSelector` fires skills per turn and logs the selected skill names.

```bash
uv run pytest tests/unit/test_skills.py -v
```

### Category 4: Repetition Detection

Verify `RepetitionGuardSkill` detects and flags recycled arguments from previous turns.

```bash
uv run pytest tests/unit/test_skills.py -v -k "repetition"
```

### Category 5: Judge Verdict Format

Verify the judge returns a structured JSON verdict with scores, reasoning, and a winner declaration.

```bash
uv run pytest tests/unit/test_judge.py -v
```

### Category 6: Provider Routing

Verify each role (debater A, debater B, judge) routes calls to its configured provider via `LLMService` and `ClientFactory`.

```bash
uv run pytest tests/unit/test_llm_service.py tests/unit/test_factory.py -v
```

### Category 7: Mock Provider Demo

Verify a complete debate runs end-to-end with `MockAIClient` — no API keys, no network, deterministic output.

```bash
uv run pytest tests/integration/test_debate_flow.py -v
```

### Category 8: Robustness

Verify provider failures, timeouts, and malformed responses are handled gracefully by the Gatekeeper and Orchestrator.

```bash
uv run pytest tests/unit/test_gatekeeper.py tests/unit/test_quality.py -v -k "fail or timeout or malformed"
```

### Category 9: IPC Message Passing

Verify `DebateChannel` correctly sends, receives, and times out typed `IPCMessage` objects.

```bash
uv run pytest tests/unit/test_ipc_channel.py tests/unit/test_ipc_protocol.py -v
```

### Category 10: Configuration Loading

Verify all config files parse correctly, required keys are present, and defaults apply when keys are absent.

```bash
uv run pytest tests/unit/test_config.py -v
```

---

## Running All Tests

```bash
# Run every test
uv run pytest

# Run with coverage report (requires ≥ 85%)
uv run pytest --cov=src --cov-report=term-missing

# Run with HTML coverage report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run only fast unit tests
uv run pytest tests/unit/ -v

# Run a single test file
uv run pytest tests/unit/test_judge.py -v

# Run tests matching a keyword
uv run pytest -k "verdict" -v

# Run and stop on first failure
uv run pytest -x
```

---

## Coverage Requirements

The project requires at least 85% test coverage on the `src/` package. Configuration in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
omit = ["src/main.py", "src/gui/server.py", "*/tests/*"]

[tool.coverage.report]
fail_under = 85
show_missing = true
```

Entry points (`src/main.py`, `src/gui/server.py`) are excluded from coverage because they are integration surfaces that require a running process to test meaningfully.

---

## Linting

```bash
# Check for linting errors (must be zero)
uv run ruff check src tests

# Auto-fix fixable issues
uv run ruff check src/ --fix

# Format code
uv run ruff format src/
```

Ruff is configured in `pyproject.toml` with rules `E, F, W, I, N, UP, B, C4, SIM` targeting Python 3.12.

---

## Submission Checks

Run these before packaging the project for review:

```bash
# Production source files must stay below the assignment line cap
find src -name '*.py' -exec wc -l {} +

# Verify the tracked transcript and skill log are present
git status --short docs/debate_transcript.md docs/skill_log.md

# Full quality gate
uv run ruff check src tests
uv run pytest --cov=src --cov-report=term-missing
```

Current verified result: `401 passed`, total coverage `92.20%`, and every Python file in `src/` is under 150 physical lines.

---

## Writing New Tests

1. Place unit tests in `tests/unit/test_<module_name>.py`
2. Use `MockAIClient` for all LLM calls — never make real API calls in unit tests
3. Use `pytest-asyncio` with `@pytest.mark.asyncio` for all `async def` test functions
4. Mock external services (`ddgs` web search, HTTP clients) with `unittest.mock.AsyncMock` or `pytest-mock`
5. Every new public function or class must have at least one test covering the happy path
6. Add at least one test for each expected failure mode (invalid input, network error, empty response)
7. Keep each test function focused on a single assertion or behaviour

### Example: Testing a skill

```python
from src.skills.rebuttal_skill import RebuttalSkill
from src.skills.models import SkillContext


def test_rebuttal_skill_scores_round_after_first():
    skill = RebuttalSkill()
    ctx = SkillContext(
        topic="AI",
        stance="AI improves learning",
        opponent_last_message="A 2024 report says AI tutoring lowers outcomes by 30%.",
        round_num=2,
        skill_type="evidence_based",
        transcript=[],
    )
    assert skill.score(ctx) > 0


def test_rebuttal_skill_injects_guidance():
    skill = RebuttalSkill()
    ctx = SkillContext(
        topic="AI",
        stance="AI improves learning",
        opponent_last_message="AI tools always replace teachers.",
        round_num=2,
        skill_type="evidence_based",
        transcript=[],
    )
    result = skill.run(ctx)
    assert "replace teachers" in result.content
```

---

## Continuous Integration

The test suite is designed to run cleanly in CI without any API keys. All provider calls in tests use `MockAIClient`. Set the following in your CI environment if needed:

```bash
# No API keys required — mock mode is used throughout
uv run pytest --cov=src --cov-report=xml
uv run ruff check src/
```
