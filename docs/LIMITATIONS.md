# Known Limitations

This document provides an honest assessment of the current platform's constraints. Understanding these limitations helps set appropriate expectations and informs future improvement work.

---

## 1. LLM Response Quality

### Hallucinated Citations

Mock and free-tier models (Groq Llama 3.1 8B, ZAI GLM-4.7-Flash) frequently invent paper titles, statistics, and author names. The `FactSafetyFilter` (`src/skills/fact_safety_filter.py`) applies heuristic cleaning — flagging suspiciously round percentages, missing publication years, or implausible author combinations — but it cannot detect all hallucinations. Users should treat all cited statistics from mock/free-tier debates as illustrative rather than factual.

### Repetition Despite Guards

`RepetitionGuardSkill` injects explicit anti-repetition instructions into each debater prompt after detecting fingerprint overlap with previous turns. However, it cannot _force_ the underlying LLM to comply. Some models — particularly smaller ones — repeat arguments with superficial rewording that defeats the fingerprinting algorithm. The `repetition_penalty` in the judge scoring compensates for this at evaluation time.

### Word Limit Compliance

Debaters are instructed to stay under the configured `debate.debater_max_words` limit in `config/setup.json` (currently 130 words). The `enforce_word_limit` function in `src/services/response_cleanup.py` hard-truncates responses that exceed this limit. Truncation can cut arguments mid-sentence, producing awkward endings. Increasing the word limit improves argument quality at the cost of higher token usage and API costs.

---

## 2. Provider Constraints

### Rate Limits on Free Tiers

Free-tier Groq and ZAI accounts have strict RPM (requests-per-minute) limits. A full 10-round debate generates approximately 30 API calls (20 debater turns + 10 judge relays + 1 final evaluation). With Groq's free tier capped at 20 RPM, the `ApiGatekeeper`'s backpressure queue will introduce deliberate delays between calls. Expect a full debate to take 3–5 minutes on free-tier providers.

### Model Availability

Provider model names change frequently. If a configured model is deprecated or renamed, all calls to that provider will fail with a `ModelNotFoundError`. To fix: update `config/models.json` and the corresponding entry in `config/setup.json` with the current model ID from your provider's documentation.

### No Token Streaming Support

Provider calls use single-shot completions (`generate_response()`), so partial model tokens are not streamed as they are generated. The GUI does stream debate events over NDJSON after each completed argument. True token-level streaming would require changes to `BaseAIClient`, all provider clients, the IPC channel types, and the GUI event protocol.

---

## 3. Web Search

### DuckDuckGo Rate Limits

The `web_search` tool (`src/tools/web_search.py`) uses the `ddgs` library, which queries DuckDuckGo's unofficial API. This API can return empty result sets or temporarily block requests under heavy use without any warning. The tool returns an empty list gracefully in this case, and `EvidenceSkill` falls back to LLM-only argument generation.

### Citation Quality

Evidence retrieved via web search is summarised as plain text, not formally cited with DOI, volume, page numbers, or publisher. This limits the academic rigour of citations produced by `CitationSkill`. For production use, replacing `ddgs` with a proper academic search API (Semantic Scholar, CrossRef, or arXiv) would significantly improve citation quality.

### Search Disabled for Mock Provider

Web search is intentionally disabled when using `MockAIClient` to keep tests fast, deterministic, and network-free. When `MockAIClient` is the active client, `web_search` returns a fixed empty list regardless of the query.

---

## 4. Judge Scoring

### Subjectivity

Even with structured scoring criteria and a detailed rubric, judge scores reflect the biases and capability level of the judge model. Smaller models (Llama 3.1 8B via Groq) produce less nuanced verdicts than larger models (GPT-4, Gemini 2.5 Flash). Using a higher-capability model as judge produces more defensible verdicts, though at higher API cost.

### Transcript Length Truncation

Very long debates or debates with verbose arguments may exceed the judge model's context window. `JudgeRelayMixin` truncates the transcript to `debate.judge_max_transcript_entries` entries before final evaluation, while `ContextCompressor` compresses each debater's prompt history during the debate. This means the judge may not evaluate early-round arguments in a long debate, potentially favouring the debater who made their best points later.

---

## 5. GUI

### Limited Concurrent Sessions

The GUI server (`src/gui/server.py` — `http.server` plus NDJSON streaming) allows a small number of concurrent debates, controlled by `server.max_concurrent_debates` in `config/setup.json`. This is process-local throttling, not a distributed queue, so multiple server processes would not coordinate capacity.

### No Persistence Between Restarts

Debate history, previous transcripts, and configuration changes made through the GUI are held in memory and lost when the server process exits. Results are written to the `results/` directory by `DebateExporter`, which provides file-level persistence, but there is no database or session store.

---

## 6. Performance

### Sequential Debate Execution

Despite using `asyncio` for concurrency _within_ a single debate (agents communicate via `asyncio.Queue` and run as concurrent coroutines), the orchestrator runs one complete debate at a time. There is no batch mode for running multiple debates in parallel.

### Token Costs for Premium Providers

A full 10-round debate with GPT-4 (OpenAI) costs approximately $0.50–$2.00 USD depending on argument verbosity and the judge's evaluation length. Use `config/pricing.json` estimates to understand costs before running debates with paid providers.

---

## 7. Testing

### Async Test Isolation

Some async tests rely on `pytest-asyncio`'s auto-generated event loop. In rare cases, if tests are collected in an unexpected order or a previous test does not clean up a queue, residual messages can leak between tests. If you observe flaky failures in IPC-related tests, run them in isolation with `uv run pytest tests/unit/test_ipc_channel.py -v` to confirm isolation.

### Integration Tests Do Not Cover Real API Behaviour

All integration tests (`tests/integration/`) use `MockAIClient`. Real provider behaviours — token limits, content-filtering rejections, model drift between versions, and network timeouts — are not automatically tested. Before deploying with a new provider or model, run a manual end-to-end debate to confirm compatibility.

---

## 8. Future Improvements

The following limitations are known and planned for future sprints:

- Streaming output support across all providers
- Multi-session GUI with persistent session storage
- Formal academic citation via Semantic Scholar API
- Parallel debate execution for batch topic comparison
- Judge confidence score and uncertainty quantification
- Adversarial prompt injection detection in debater arguments
