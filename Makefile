.PHONY: demo test lint coverage clean install format gui check

# ── One-command mock demo — no API keys required ─────────────────────────────
demo:
	uv run python -m src.main \
		--topic "Artificial Intelligence in Higher Education" \
		--stance-a "AI tools improve student learning outcomes" \
		--stance-b "AI tools harm deep learning and academic integrity" \
		--provider-a mock \
		--provider-b mock

# ── Run all tests ─────────────────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

# ── Run tests with coverage report (requires ≥85%) ───────────────────────────
coverage:
	uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=85

# ── Lint: zero ruff errors required ──────────────────────────────────────────
lint:
	uv run ruff check src/ tests/

# ── Auto-format code ──────────────────────────────────────────────────────────
format:
	uv run ruff format src/ tests/

# ── Install / sync dependencies ───────────────────────────────────────────────
install:
	uv sync

# ── Launch GUI server ─────────────────────────────────────────────────────────
gui:
	uv run python -m src.gui.server

# ── Run lint + coverage in one shot ──────────────────────────────────────────
check: lint coverage

# ── Clean generated artefacts ────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ 2>/dev/null || true
