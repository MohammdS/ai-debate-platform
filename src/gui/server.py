import asyncio
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from src.gui.debate_runner import run_debate_from_payload, stream_debate_from_payload
from src.gui.server_paths import result_file, static_file
from src.gui.server_response import CONTENT_TYPES, safe_error
from src.shared.config import ConfigManager

_cfg = ConfigManager()
_MAX_CONCURRENT = _cfg.server_max_concurrent_debates
# Process-local guard: enough for one demo server, not a distributed queue.
_debate_semaphore = threading.Semaphore(_MAX_CONCURRENT)
_result_file = result_file


class DebateGuiHandler(SimpleHTTPRequestHandler):
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
        return safe_error(exc)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_result_file(self, session_id: str | None):
        try:
            path = result_file(session_id)
        except ValueError:
            self.send_error(400)
            return
        if not path.exists():
            self._send_json({"topic": "", "history": [], "verdict": ""})
            return
        self._send_bytes(path.read_bytes(), ".json")

    def _send_static(self):
        route = unquote(self.path.split("?", 1)[0]).lstrip("/")
        try:
            file_path = static_file(route)
        except PermissionError:
            self.send_error(403)
            return
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
    server = ThreadingHTTPServer((_cfg.server_host, _cfg.server_port), DebateGuiHandler)
    print(f"AI Debate GUI running at http://{_cfg.server_host}:{_cfg.server_port}")
    server.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
