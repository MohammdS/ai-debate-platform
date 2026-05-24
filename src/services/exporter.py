from __future__ import annotations

import json
from pathlib import Path


class DebateExporter:
    """Exports debate transcripts to various formats."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_token_summary(token_stats: dict) -> str:
        """Return a human-readable token/cost summary string."""
        t_in  = token_stats.get("total_tokens_in",    0)
        t_out = token_stats.get("total_tokens_out",   0)
        cost  = token_stats.get("estimated_cost_usd", 0.0)
        return (
            f"Tokens in : {t_in:,}\n"
            f"Tokens out: {t_out:,}\n"
            f"Total     : {t_in + t_out:,}\n"
            f"Est. cost : ${cost:.6f} USD"
        )

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    def export_to_markdown(
        self,
        topic: str,
        history: list[dict[str, str]],
        verdict: str,
        token_stats: dict | None = None,
        filename: str = "debate_transcript.md",
    ):
        """Saves the debate history as a Markdown file."""
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Debate Transcript: {topic}\n\n")
            for msg in history:
                name = msg.get("name", msg.get("role", "Unknown"))
                f.write(f"### {name}\n{msg['content']}\n\n---\n\n")

            f.write(f"## JUDGE VERDICT\n{verdict}\n")

            if token_stats:
                f.write("\n\n## TOKEN USAGE\n```\n")
                f.write(self.format_token_summary(token_stats))
                f.write("\n```\n")
        return file_path

    def export_to_json(
        self,
        topic: str,
        history: list[dict[str, str]],
        verdict: str,
        token_stats: dict | None = None,
        filename: str = "debate.json",
    ):
        """Saves the debate as a JSON file."""
        data: dict = {
            "topic":   topic,
            "history": history,
            "verdict": verdict,
        }
        if token_stats:
            data["token_stats"] = token_stats
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return file_path
