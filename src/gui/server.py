import asyncio
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src.gui.debate_runner import run_debate_from_payload, stream_debate_from_payload

# Allows only one debate to run at a time; prevents resource exhaustion when
# multiple browser tabs POST simultaneously.
_debate_semaphore = threading.Semaphore(1)

ROOT = Path(__file__).resolve().parents[2]
GUI_DIR = ROOT / "gui"
RESULT_FILE = ROOT / "results" / "debate.json"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


class DebateGuiHandler(SimpleHTTPRequestHandler):
    """Serves the GUI and JSON API endpoints."""

    def do_GET(self):
        if self.path == "/api/results":
            self._send_result_file()
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
            self._send_json({"error": "A debate is already running. Please wait."}, status=503)
            return
        try:
            payload = self._read_json()
            session = asyncio.run(run_debate_from_payload(payload))
            self._send_json(session.model_dump())
        except Exception as exc:  # pragma: no cover
            self._send_json({"error": self._safe_error(exc)}, status=500)
        finally:
            _debate_semaphore.release()

    def _stream_debate(self):
        if not _debate_semaphore.acquire(blocking=False):
            self._open_stream()
            self._write_line({"type": "error", "error": "A debate is already running. Please wait."})
            return
        try:
            payload = self._read_json()
            self._open_stream()
            asyncio.run(self._write_stream(payload))
        except Exception as exc:  # pragma: no cover
            try:
                if not self.wfile.closed:
                    self._write_line({"type": "error", "error": self._safe_error(exc)})
            except OSError:
                pass  # client already disconnected — nothing to do
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
        # Redact common API key patterns
        msg = re.sub(r"key=[^'\s]+",            "key=REDACTED",    msg)
        msg = re.sub(r"Bearer\s+\S+",           "Bearer REDACTED", msg)
        msg = re.sub(r"(sk|gsk|AIza)-[A-Za-z0-9_\-]+", "REDACTED", msg)
        return msg

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_result_file(self):
        if not RESULT_FILE.exists():
            self._send_json({"topic": "", "history": [], "verdict": ""})
            return
        self._send_bytes(RESULT_FILE.read_bytes(), ".json")

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
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DebateGuiHandler)
    print("AI Debate GUI running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
