import asyncio
import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src.gui.debate_runner import run_debate_from_payload, stream_debate_from_payload

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
        try:
            payload = self._read_json()
            data = asyncio.run(run_debate_from_payload(payload))
            self._send_json(data)
        except Exception as exc:  # pragma: no cover
            self._send_json({"error": self._safe_error(exc)}, status=500)

    def _stream_debate(self):
        try:
            payload = self._read_json()
            self._open_stream()
            asyncio.run(self._write_stream(payload))
        except Exception as exc:  # pragma: no cover
            if not self.wfile.closed:
                self._write_line({"type": "error", "error": self._safe_error(exc)})

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
        return re.sub(r"key=[^'\s]+", "key=REDACTED", str(exc))

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
