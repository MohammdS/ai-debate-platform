import asyncio
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.gui.debate_runner import run_debate_from_payload, stream_debate_from_payload
from src.shared.config import ConfigManager

# Allow up to 3 concurrent debates; prevents resource exhaustion while
# supporting multiple browser tabs / users simultaneously.
_MAX_CONCURRENT = 3
_debate_semaphore = threading.Semaphore(_MAX_CONCURRENT)

ROOT = Path(__file__).resolve().parents[2]
GUI_DIR = ROOT / "gui"
RESULTS_DIR = ROOT / "results"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _result_file(session_id: str | None) -> Path:
    """Return the debate.json path for a given session, or the most recent one."""
    if session_id:
        return RESULTS_DIR / session_id / "debate.json"
    # Fall back to most recently modified debate.json across all session dirs
    candidates = sorted(
        RESULTS_DIR.glob("*/debate.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else RESULTS_DIR / "debate.json"


class DebateGuiHandler(SimpleHTTPRequestHandler):
    """Serves the GUI and JSON API endpoints."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/results":
            qs = parse_qs(parsed.query)
            session_id = qs.get("id", [None])[0]
            self._send_result_file(session_id)
            return
        self._send_static()

    def do_POST(self):
        if self.path == "/api/debates/stream":
            self._stream_debate()
            return
        if self.path == "/api/debates":
            self._run_debate()
            return
        self.send_error(404)

    def _run_debate(self):
        if not _debate_semaphore.acquire(blocking=False):
            self._send_json(
                {"error": f"Server busy — at most {_MAX_CONCURRENT} debates may run concurrently."},
                status=503,
            )
            return
        try:
            payload = self._read_json()
            session = asyncio.run(run_debate_from_payload(payload))
            self._send_json(session)
        except Exception as exc:  # pragma: no cover
            self._send_json({"error": self._safe_error(exc)}, status=500)
        finally:
            _debate_semaphore.release()

    def _stream_debate(self):
        if not _debate_semaphore.acquire(blocking=False):
            self._open_stream()
            try:
                self._write_line({"type": "error", "error": f"Server busy — at most {_MAX_CONCURRENT} debates may run concurrently."})
                self._write_line({"type": "_done"})
            except OSError:
                pass
            return
        try:
            payload = self._read_json()
            self._open_stream()
            asyncio.run(self._write_stream(payload))
        except Exception as exc:  # pragma: no cover
            try:
                if not self.wfile.closed:
                    self._write_line({"type": "error", "error": self._safe_error(exc)})
                    self._write_line({"type": "_done"})
            except OSError:
                pass
        finally:
            _debate_semaphore.release()

    async def _write_stream(self, payload: dict):
        async for event in stream_debate_from_payload(payload):
            self._write_line(event)

    def _open_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _write_line(self, event: dict):
        line = json.dumps(event).encode("utf-8") + b"\n"
        self.wfile.write(line)
        self.wfile.flush()

    def _safe_error(self, exc: Exception) -> str:
        msg = str(exc)
        msg = re.sub(r"key=[^'\s]+",                    "key=REDACTED",    msg)
        msg = re.sub(r"Bearer\s+\S+",                   "Bearer REDACTED", msg)
        msg = re.sub(r"(sk|gsk|AIza)-[A-Za-z0-9_\-]+", "REDACTED",        msg)
        return msg

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_result_file(self, session_id: str | None):
        path = _result_file(session_id)
        if not path.exists():
            self._send_json({"topic": "", "history": [], "verdict": ""})
            return
        self._send_bytes(path.read_bytes(), ".json")

    def _send_static(self):
        route = unquote(self.path.split("?", 1)[0]).lstrip("/")
        file_path = GUI_DIR / (route or "index.html")
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        self._send_bytes(file_path.read_bytes(), file_path.suffix)

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", CONTENT_TYPES[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, suffix: str):
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(suffix, "text/plain"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    cfg    = ConfigManager()
    host   = cfg.server_host
    port   = cfg.server_port
    server = ThreadingHTTPServer((host, port), DebateGuiHandler)
    print(f"AI Debate GUI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
