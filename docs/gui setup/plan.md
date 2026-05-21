# GUI Implementation Plan

## Architecture
- `gui/` contains static browser assets.
- `src/gui/debate_runner.py` adapts HTTP payloads to the existing debate backend.
- `src/gui/server.py` serves static files and exposes JSON plus live stream endpoints.

## API
- `GET /api/results` loads the latest exported `results/debate.json`.
- `POST /api/debates` runs a debate and returns `{ topic, history, verdict }`.
- `POST /api/debates/stream` streams newline-delimited JSON events while the debate runs.

## Providers
- `mock` uses the local deterministic test client.
- `gemini` uses `GEMINI_API_KEY` and `api.gemini_model`.
- `groq` uses `GROQ_API_KEY` and `api.groq_model`.
- `openai` uses `OPENAI_API_KEY` and `api.openai_model`.

## UI
- First viewport emphasizes the debate headline and run controls.
- Transcript cards appear one by one as Debater A and Debater B respond.
- Verdict remains visible, waits during debate, switches to analysis, then shows the winner.

## Verification
- Run unit tests with `python -m pytest`.
- Check Python line counts stay under 150 lines.
- Start the GUI with `python -m src.gui.server` and open `http://127.0.0.1:8000`.
