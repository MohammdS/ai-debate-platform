# TODO — AI Debate Platform

## Status
- [x] Done
- [/] In Progress
- [ ] Pending

---

## Core Infrastructure
- [x] Project structure + `uv` + `pyproject.toml`
- [x] `config/setup.json` — all parameters configurable
- [x] `.env-example`, `.gitignore` (API keys excluded)
- [x] `src/shared/config.py` — ConfigManager
- [x] `src/shared/gatekeeper.py` — rate limiting + retry
- [x] `src/shared/logger.py` — console + file logging

## SDK Layer
- [x] `src/sdk/base_client.py` — abstract BaseAIClient
- [x] `src/sdk/openai_client.py`
- [x] `src/sdk/gemini_client.py`
- [x] `src/sdk/groq_client.py`
- [x] `src/sdk/mock_client.py`
- [x] `src/sdk/factory.py` — AIClientFactory

## IPC Layer
- [x] `src/ipc/message.py` — DebateMessage + MessageType enum
- [x] `src/ipc/channel.py` — IpcChannel (asyncio.Queue + timeout)
- [x] `src/ipc/__init__.py`

## Service Layer
- [x] `src/services/debater.py` — Debater with run() IPC loop + get_argument() SDK
- [x] `src/services/judge.py` — Judge with run() mediator loop + evaluate() SDK
- [x] `src/services/orchestrator.py` — wire channels + asyncio.gather
- [x] `src/services/exporter.py` — Markdown + JSON export

## Testing
- [x] `tests/unit/test_ipc_message.py`
- [x] `tests/unit/test_ipc_channel.py`
- [x] `tests/unit/test_debater.py`
- [x] `tests/unit/test_judge.py`
- [x] `tests/unit/test_orchestrator.py`
- [x] `tests/unit/test_config.py`
- [x] `tests/unit/test_gatekeeper.py`
- [x] `tests/unit/test_logger.py`
- [x] Coverage ≥ 85% (current: 92.86%)

## Pending
- [ ] `src/shared/watchdog.py` — timeout + restart for autonomous runs
- [ ] `src/shared/logger.py` — FIFO rotating handler (20 files × 500 lines)
- [ ] `src/tools/web_search.py` — DuckDuckGo search tool for debaters
- [ ] `src/main.py` — interactive terminal menu
- [ ] `README.md` — screenshots, prompts, full session log
