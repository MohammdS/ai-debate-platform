from typing import List, Dict
from pathlib import Path
import json

class DebateExporter:
    """Exports debate transcripts to various formats."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

    def export_to_markdown(self, topic: str, history: List[Dict[str, str]], 
                           verdict: str, filename: str = "debate_transcript.md"):
        """Saves the debate history as a Markdown file."""
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Debate Transcript: {topic}\n\n")
            for msg in history:
                name = msg.get("name", msg.get("role", "Unknown"))
                f.write(f"### {name}\n{msg['content']}\n\n---\n\n")
            
            f.write(f"## JUDGE VERDICT\n{verdict}\n")
        return file_path

    def export_to_json(self, topic: str, history: List[Dict[str, str]], 
                        verdict: str, filename: str = "debate.json"):
        """Saves the debate as a JSON file."""
        data = {
            "topic": topic,
            "history": history,
            "verdict": verdict
        }
        file_path = self.results_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return file_path
