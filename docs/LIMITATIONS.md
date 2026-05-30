# Known Limitations

This document records practical constraints in the current version. They are not hidden defects; they are boundaries for a university submission and future production work.

## LLM Response Quality

### Hallucinated Citations

Free-tier and smaller models can invent paper titles, statistics, author names, or exact percentages. `FactSafetyFilter` reduces risky claims with heuristics, but it cannot verify every factual statement. Treat mock/free-tier citations as illustrative unless independently checked.

### Repetition Despite Guards

`RepetitionGuardSkill` injects anti-repetition guidance and `DebateMemory` tracks prior claims, but the final wording still depends on the selected model. The judge scoring includes repetition penalties to reduce the advantage of repeated claims.

### Word Limit Compliance

Debaters are instructed to stay under `debate.debater_max_words` from `config/setup.json`. `enforce_word_limit` truncates overlong output, which can occasionally cut an argument awkwardly.

## Provider Constraints

### Free-Tier Rate Limits

A full 10-round debate can generate roughly 30 LLM calls. Free tiers such as Groq may require deliberate backpressure. `ApiGatekeeper` spaces calls instead of letting the debate crash on provider limits.

### Model Availability

Provider model IDs can change. If a provider deprecates a model, update `config/setup.json` and `config/models.json`.

### No Token-Level Streaming

Provider clients use single-shot completions. The GUI streams completed debate events over NDJSON, but it does not stream partial model tokens.

## Web Search

### DuckDuckGo Availability

`WebSearchTool` uses the `ddgs` package. DuckDuckGo may return empty results or throttle requests. The tool fails gracefully and the debater falls back to LLM-only reasoning.

### Citation Quality

Search snippets are not formal academic citations. A production academic version should use Semantic Scholar, CrossRef, arXiv, or another structured source API.

### Mock Provider

Web search is disabled for `MockAIClient` so tests remain deterministic and network-free.

## Judge Scoring

Judge scores depend on the judge model. Smaller models can be less nuanced than larger paid models. The rubric improves consistency, but it does not remove model bias.

Long transcripts may be compressed or truncated before final evaluation to stay within context limits.

## GUI

The GUI server is intentionally lightweight: `http.server`, process-local concurrency control, and NDJSON streaming. It is suitable for a local demo, not for multi-user production deployment.

Results are written to files under `results/` during runtime, but there is no persistent database or account/session system.

## Future Improvements

- Token-level streaming across providers
- Persistent multi-session GUI
- Academic citation API integration
- Batch debate runs for parameter experiments
- Judge confidence score
- Stronger prompt-injection defenses for retrieved evidence
