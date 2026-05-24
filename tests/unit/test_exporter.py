"""Tests for DebateExporter — markdown/JSON output and token usage section."""
import json
from pathlib import Path

import pytest

from src.services.exporter import DebateExporter

HISTORY = [
    {"name": "Debater_A", "content": "First argument."},
    {"name": "Debater_B", "content": "Counter argument."},
]
VERDICT = "WINNER: Pro"
STATS = {
    "total_tokens_in":    1000,
    "total_tokens_out":   500,
    "estimated_cost_usd": 0.000075,
}


@pytest.fixture()
def exporter(tmp_path):
    return DebateExporter(results_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def test_markdown_contains_topic(exporter, tmp_path):
    exporter.export_to_markdown("AI debate", HISTORY, VERDICT)
    md = (tmp_path / "debate_transcript.md").read_text()
    assert "AI debate" in md


def test_markdown_contains_verdict(exporter, tmp_path):
    exporter.export_to_markdown("topic", HISTORY, VERDICT)
    md = (tmp_path / "debate_transcript.md").read_text()
    assert VERDICT in md


def test_markdown_contains_messages(exporter, tmp_path):
    exporter.export_to_markdown("topic", HISTORY, VERDICT)
    md = (tmp_path / "debate_transcript.md").read_text()
    assert "First argument." in md
    assert "Counter argument." in md


def test_markdown_without_stats_has_no_token_section(exporter, tmp_path):
    exporter.export_to_markdown("topic", HISTORY, VERDICT)
    md = (tmp_path / "debate_transcript.md").read_text()
    assert "TOKEN USAGE" not in md


def test_markdown_with_stats_includes_token_section(exporter, tmp_path):
    exporter.export_to_markdown("topic", HISTORY, VERDICT, token_stats=STATS)
    md = (tmp_path / "debate_transcript.md").read_text()
    assert "TOKEN USAGE" in md
    assert "1,000" in md          # tokens_in formatted
    assert "500" in md            # tokens_out
    assert "0.000075" in md       # cost


def test_markdown_token_total_is_sum(exporter, tmp_path):
    exporter.export_to_markdown("topic", HISTORY, VERDICT, token_stats=STATS)
    md = (tmp_path / "debate_transcript.md").read_text()
    # total = 1000 + 500 = 1500
    assert "1,500" in md


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def test_json_contains_topic(exporter, tmp_path):
    exporter.export_to_json("AI ethics", HISTORY, VERDICT)
    data = json.loads((tmp_path / "debate.json").read_text())
    assert data["topic"] == "AI ethics"


def test_json_contains_history(exporter, tmp_path):
    exporter.export_to_json("topic", HISTORY, VERDICT)
    data = json.loads((tmp_path / "debate.json").read_text())
    assert len(data["history"]) == 2


def test_json_without_stats_has_no_token_key(exporter, tmp_path):
    exporter.export_to_json("topic", HISTORY, VERDICT)
    data = json.loads((tmp_path / "debate.json").read_text())
    assert "token_stats" not in data


def test_json_with_stats_includes_token_key(exporter, tmp_path):
    exporter.export_to_json("topic", HISTORY, VERDICT, token_stats=STATS)
    data = json.loads((tmp_path / "debate.json").read_text())
    assert "token_stats" in data
    assert data["token_stats"]["total_tokens_in"]  == 1000
    assert data["token_stats"]["total_tokens_out"] == 500
    assert abs(data["token_stats"]["estimated_cost_usd"] - 0.000075) < 1e-9


# ---------------------------------------------------------------------------
# format_token_summary
# ---------------------------------------------------------------------------

def test_format_token_summary_contains_all_fields():
    summary = DebateExporter.format_token_summary(STATS)
    assert "1,000" in summary
    assert "500" in summary
    assert "1,500" in summary
    assert "0.000075" in summary


def test_format_token_summary_zero_cost():
    summary = DebateExporter.format_token_summary(
        {"total_tokens_in": 0, "total_tokens_out": 0, "estimated_cost_usd": 0.0}
    )
    assert "$0.000000" in summary


# ---------------------------------------------------------------------------
# Custom filename
# ---------------------------------------------------------------------------

def test_custom_markdown_filename(exporter, tmp_path):
    path = exporter.export_to_markdown("t", HISTORY, "v", filename="custom.md")
    assert path == tmp_path / "custom.md"
    assert (tmp_path / "custom.md").exists()


def test_custom_json_filename(exporter, tmp_path):
    path = exporter.export_to_json("t", HISTORY, "v", filename="custom.json")
    assert path == tmp_path / "custom.json"
    assert (tmp_path / "custom.json").exists()
