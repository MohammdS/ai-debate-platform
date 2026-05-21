# Debugging Log

## Gemini First-Turn Error
- Symptom: Gemini returned `400 Bad Request`.
- Cause: first debater turn had only a system instruction and no user content.
- Fix: Gemini adapter now sends `Begin the debate.` when there is no chat history.

## Real Gemini Smoke Test Timeout
- Symptom: full 10-round Gemini run exceeded terminal timeout.
- Cause: real provider latency and 21 total model calls.
- Fix: GUI/API now accepts `rounds` from 1 to 10 for fast smoke tests.

## Gemini Rate Limit
- Symptom: Gemini returned `429 Too Many Requests`.
- Cause: provider quota or free-tier rate limits.
- Action: retry later, reduce rounds, or test with Groq.

## API Key Exposure Risk
- Symptom: provider error URL contained an API key query parameter.
- Fix: GUI server redacts `key=...` from streamed and JSON error messages.
