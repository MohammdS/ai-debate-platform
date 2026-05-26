# Product Requirements Document — AI Debate Platform

## 1. Overview
A Python-based platform for structured, competitive AI debates. Two AI debaters argue opposing stances on a topic; a third AI judge moderates, relays messages, and declares a winner.

## 2. Objectives
- Orchestrate a real debate between two LLM-powered agents.
- Enforce competitive, non-conceding behaviour via system prompts.
- Deliver a scored verdict from a neutral judge.
- Meet professional software engineering standards (<150 lines/file, TDD, OOP, uv, ruff).

## 3. Roles
| Role | Responsibility |
|---|---|
| **Debater A** | Defends stance A; never concedes |
| **Debater B** | Defends stance B; never concedes |
| **Judge** | Relays messages between debaters; evaluates transcript; declares winner |

## 4. Debate Structure
- 10 rounds (10 arguments per debater = 20 total turns).
- All messages flow through the Judge (child → father → child).
- Judge evaluates full transcript at end and scores both debaters (0–100).
- Judge **must** declare a winner — ties forbidden.

## 5. Communication Protocol
- All inter-agent messages are JSON-serialized on `asyncio.Queue` channels (IPC).
- Message types: `ARGUMENT | RELAY | VERDICT | SHUTDOWN`.
- No direct debater-to-debater communication.

## 6. Technical Requirements
- **Language:** Python 3.12+
- **Package manager:** `uv`
- **Linter:** `ruff`
- **Testing:** `pytest` + `pytest-asyncio`, >85% coverage
- **AI providers:** OpenAI, Gemini, Groq, Mock
- **Config:** `config/setup.json` — no hardcoded parameters
- **Secrets:** API keys via `.env` only; `.env` in `.gitignore`

## 7. Success Criteria
- Full 10-round debate runs end-to-end with real or mock LLM.
- Verdict produced with winner and scores.
- All tests pass; coverage ≥ 85%.
- Ruff reports zero lint errors.
