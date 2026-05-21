# GUI Prompt History

This file records prompts given by the university student/project author to the AI assistant while creating and refining the browser GUI.

## Prompt 1: Build A GUI
The student asked to build a user interface while keeping the Python backend unchanged.

Key requirements:
- Show the chat between debaters.
- Show the debate headline in a visually polished way.
- Connect the frontend to the Python backend.
- Add GUI documentation in `docs/gui setup/`.
- Align with `software_submission_guidelines-V3.pdf`.

Implementation response:
- Added a static browser frontend in `gui/`.
- Added a Python stdlib HTTP server in `src/gui/server.py`.
- Added `src/gui/debate_runner.py` to reuse existing backend services.
- Added `prd.md`, `plan.md`, and `todo.md` under `docs/gui setup/`.

## Prompt 2: Live Debate Chat
The student asked for the UI to show the chat building live, one debater message at a time, with the judge waiting until the end.

Key requirements:
- Debater A and Debater B messages appear as each turn completes.
- Judge verdict panel waits during the debate.
- Judge analyzes only after the full chat ends.

Implementation response:
- Added `POST /api/debates/stream`.
- Stream events: `start`, `message`, `judging`, `verdict`, and `error`.
- Updated `gui/app.js` to consume newline-delimited JSON and append cards live.

## Prompt 3: Free Provider Support
The student asked for free API options for school testing.

Key requirements:
- Add Gemini support.
- Add Groq support.
- Document how to configure keys and models.

Implementation response:
- Added `GeminiClient`.
- Added `GroqClient`.
- Updated `AIClientFactory`.
- Added `GEMINI_API_KEY` and `GROQ_API_KEY` to `.env-example`.
- Added `gemini_model` and `groq_model` to `config/setup.json`.
- Updated README and GUI docs.

## Prompt 4: Real Provider Smoke Testing
The student asked to run a Gemini live test.

Findings:
- Gemini rejected an empty first-turn content list.
- Full real-provider tests can exceed terminal timeouts.
- Gemini can return `429 Too Many Requests` on free-tier quota limits.

Implementation response:
- Gemini now seeds the first turn with `Begin the debate.` when history is empty.
- Added bounded `rounds` support from 1 to 10.
- Added a `Rounds` input to the GUI.
- Added provider error redaction for API key query parameters.

## Prompt 5: Maintenance Docs
The student asked to create a maintenance and debugging documentation folder.

Implementation response:
- Added `docs/maintenance and debugging/`.
- Added runbook, debugging log, maintenance TODO, and folder README.
