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
# Install uv if you haven't
npm install -g @astral-sh/uv # or other methods

# Sync dependencies
uv sync
```

## Configuration

1. Copy `.env-example` to `.env`.
2. Add your API keys (OpenAI/Anthropic).
3. Configure models in `config/setup.json`.

## Usage

```bash
uv run python -m src.main --topic "Artificial General Intelligence" --stance-a "AGI is a risk" --stance-b "AGI is a benefit"
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
- [Prompts](docs/PROMPTS.md)

## License
MIT
