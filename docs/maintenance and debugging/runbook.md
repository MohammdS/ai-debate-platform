# Runbook

## Start GUI Server
```powershell
uv run python -m src.gui.server
```

Open:
```text
http://127.0.0.1:8000
```

## Stop GUI Server
```powershell
netstat -ano | Select-String ':8000'
Stop-Process -Id <PID>
```

## Local Environment
`.env` is ignored by Git. Put real keys there only:
```env
GEMINI_API_KEY=your_real_gemini_key
GROQ_API_KEY=your_real_groq_key
```

## Fast Real-Provider Smoke Test
- Provider: `Groq` or `Gemini`
- Rounds: `1`
- Topic: short, low-token prompt

If the smoke test passes, increase rounds gradually.

## Verification Commands
```powershell
uv run python -m pytest
uv run ruff check .
uv run python -m pytest --cov=src
```
