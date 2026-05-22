# AI Debate Platform

A professional Python-based platform for structured, competitive AI debates.

## Features
- **Three AI Model Architecture:** Two competitive debaters and one impartial judge.
- **Structured Debates:** 20-message alternating turns (10 each).
- **Competitive AI:** Custom prompts designed for high-intensity argumentation and persistence.
- **Detailed Scoring:** Automated judging with scores and a declared winner.
- **Compliance:** Built following the highest professional software standards (<150 lines per file, TDD, modular SDK).

## Installation

This project uses `uv` for package management.

```bash
# Install uv if you haven't (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

## Configuration

1. Copy `.env-example` to `.env`.
2. Add your API keys (OpenAI/Gemini/Groq as needed).
3. Configure models in `config/setup.json`.

Free-tier testing options:
- Gemini: create a key at <https://aistudio.google.com/app/apikey>, set `GEMINI_API_KEY`, use provider `gemini`.
- Groq: create a key at <https://console.groq.com/keys>, set `GROQ_API_KEY`, use provider `groq`.

## Usage

```bash
uv run python -m src.main --topic "Artificial General Intelligence" --stance-a "AGI is a risk" --stance-b "AGI is a benefit"
```

Run with specific providers per debater:

```bash
uv run python -m src.main --topic "AI in schools" --stance-a "AI should be allowed" --stance-b "AI should be restricted" --provider-a groq --provider-b zai
```

Run the GUI:

```bash
uv run python -m src.gui.server
# then open http://127.0.0.1:8000
```

## Testing

```bash
# Run tests with coverage
uv run python -m pytest --cov=src
```

## Documentation
- [PRD](docs/PRD.md)
- [Plan](docs/PLAN.md)
- [Task List](docs/TODO.md)
- [IPC Design](docs/PRD_ipc.md)
- [Gatekeeper Design](docs/PRD_gatekeeper.md)
- [Watchdog Design](docs/PRD_watchdog.md)

## License
MIT
