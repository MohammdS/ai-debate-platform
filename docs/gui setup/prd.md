# GUI Product Requirements

## Objective
Add a browser-based interface for the AI Debate Platform while preserving the existing Python backend and debate orchestration.

## User Experience
- Show the debate topic as the page headline.
- Show a readable chat-style transcript that builds live as each debater responds.
- Keep the judge verdict panel in a waiting state until the full debate is complete.
- Analyze only after the chat ends, then declare the winner in the verdict panel.
- Allow a user to start a debate from the browser with topic, stance, and provider fields.
- Support mock, OpenAI, Gemini, and Groq providers from the browser.

## Backend Integration
- Reuse the existing `Debater`, `Judge`, `DebateOrchestrator`, `AIClientFactory`, and `DebateExporter`.
- Keep CLI behavior unchanged.
- Serve the frontend and streaming API through a Python stdlib HTTP server to avoid new dependency risk.
- Use configured provider model IDs from `config/setup.json`.

## Guideline Alignment
- Keep implementation modular and Python-centered.
- Keep code files under 150 lines.
- Add focused tests for new backend-facing GUI logic.
- Continue using `uv`, `pytest`, and Ruff-compatible Python style.
