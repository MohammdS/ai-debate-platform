# Product Requirements Document - AI Debate Platform

## 1. Overview

The AI Debate Platform runs structured competitive debates between two LLM-powered debaters and a third LLM-powered judge. Debaters argue opposing stances, the judge relays messages, and the system exports a final verdict plus transcript evidence.

## 2. Objectives

- Orchestrate a real debate between two autonomous AI agents.
- Keep communication explicit through typed IPC queue channels.
- Enforce clear roles: Pro, Contra, and Judge.
- Select debate skills per turn and inject skill guidance into prompts.
- Provide deterministic mock mode for tests and demos without API keys.
- Meet professional software standards: Python 3.12+, `uv`, ruff, >=85% coverage, config-driven runtime behavior, and source files under 150 lines.

## 3. User Roles

| Role | Responsibility |
|---|---|
| Debater A / Pro | Defends stance A and sends arguments through the judge |
| Debater B / Contra | Defends stance B and sends counterarguments through the judge |
| Judge | Relays turns, evaluates the transcript, scores both sides, and declares a winner |
| User / Evaluator | Chooses topic, stances, providers, and reviews transcript/verdict output |

## 4. Functional Requirements

- Run a default 10-round debate, producing 20 debater turns total.
- Support CLI and browser GUI workflows.
- Support OpenAI, Gemini, Groq, ZAI, OpenRouter, and Mock providers.
- Route all provider calls through `LLMService`, provider clients, and `ApiGatekeeper`.
- Export Markdown and JSON debate results.
- Export per-turn skill usage logs.
- Keep all API keys in environment variables only.

## 5. Non-Functional Requirements

- Tests must run offline with mock clients.
- Coverage must stay above 85%.
- Ruff must report zero lint errors.
- Runtime parameters must be configurable under `config/`.
- Production files under `src/` must stay at or below 150 physical lines.
- Failures must be logged and surfaced safely without leaking secrets.

## 6. Success Criteria

- `uv run pytest -q` passes.
- `uv run pytest --cov=src --cov-report=term-missing` exceeds the coverage threshold.
- `uv run ruff check src tests` passes.
- Mock debate runs end to end without API keys.
- GUI and CLI both produce a judge verdict and exported results.
