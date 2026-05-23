import json
from pathlib import Path


class DebateExporter:
    """Exports debate transcripts to various formats."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

    def export_to_markdown(
        self, topic: str, history: list[dict[str, str]], verdict: str,
        filename: str = "debate_transcript.md", model_info: dict | None = None
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
        return file_path

    def export_to_json(
        self, topic: str, history: list[dict[str, str]], verdict: str,
        filename: str = "debate.json", model_info: dict | None = None
    ):
        """Saves the debate as a JSON file."""
        data = {
            "topic": topic,
            "history": history,
            "verdict": verdict,
            "model_info": model_info or {},
        }
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return file_path
