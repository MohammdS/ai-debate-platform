from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUI_DIR = ROOT / "gui"
RESULTS_DIR = ROOT / "results"
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{1,64}$")


def result_file(session_id: str | None) -> Path:
    """Return the debate.json path for a session, or the most recent one."""
    if session_id:
        if not _SESSION_ID_RE.match(session_id):
            raise ValueError(f"Invalid session_id: {session_id!r}")
        candidate = (RESULTS_DIR / session_id / "debate.json").resolve()
        if not candidate.is_relative_to(RESULTS_DIR.resolve()):
            raise ValueError(f"Session path escapes results dir: {session_id!r}")
        return candidate
    candidates = sorted(
        RESULTS_DIR.glob("*/debate.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else RESULTS_DIR / "debate.json"


def static_file(route: str) -> Path:
    """Resolve a GUI static path and reject traversal outside GUI_DIR."""
    file_path = (GUI_DIR / (route or "index.html")).resolve()
    if not file_path.is_relative_to(GUI_DIR.resolve()):
        raise PermissionError(route)
    return file_path
