from __future__ import annotations

import json
from pathlib import Path


class DebateExporter:
    """Exports debate transcripts to various formats."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

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
        self, topic: str, history: list[dict[str, str]], verdict: str,
        filename: str = "debate_transcript.md", model_info: dict | None = None,
        token_stats: dict | None = None,
    ):
        """Saves the debate history as a Markdown file."""
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Debate Transcript: {topic}\n\n")
            if model_info:
                f.write("## Models\n")
                for role in ("debater_a", "debater_b", "judge"):
                    item = model_info.get(role, {})
                    label = item.get("label", role)
                    display = item.get("display", item.get("model", "Unknown"))
                    f.write(f"- {label}: {display}\n")
                f.write("\n")
            for msg in history:
                name = msg.get("name", msg.get("role", "Unknown"))
                f.write(f"### {name}\n{msg['content']}\n\n---\n\n")

            f.write(f"## JUDGE VERDICT\n{verdict}\n")

            if token_stats:
                f.write("\n\n## TOKEN USAGE\n```\n")
                f.write(self.format_token_summary(token_stats))
                f.write("\n```\n")
        return file_path

    def export_skill_log(
        self, topic: str,
        debater_a_log: list[dict], debater_a_label: str,
        debater_b_log: list[dict], debater_b_label: str,
        filename: str = "skill_log.md",
    ) -> Path:
        """Saves per-round skill selections for both debaters as a Markdown file."""
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Skill Usage Log: {topic}\n\n")
            for label, log in ((debater_a_label, debater_a_log), (debater_b_label, debater_b_log)):
                f.write(f"## {label}\n\n")
                f.write("| Turn | Round | Skills Selected |\n")
                f.write("|------|-------|-----------------|\n")
                for entry in log:
                    skills = ", ".join(entry["skills"]) if entry["skills"] else "*(none)*"
                    f.write(f"| {entry['turn']:>4} | {entry['round']:>5} | {skills} |\n")
                f.write("\n")
        return file_path

    def export_to_json(
        self, topic: str, history: list[dict[str, str]], verdict: str,
        filename: str = "debate.json", model_info: dict | None = None,
        token_stats: dict | None = None,
    ):
        """Saves the debate as a JSON file."""
        data: dict = {
            "topic":   topic,
            "history": history,
            "verdict": verdict,
            "model_info": model_info or {},
        }
        if token_stats:
            data["token_stats"] = token_stats
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return file_path
