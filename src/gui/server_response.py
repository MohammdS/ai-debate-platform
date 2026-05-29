from __future__ import annotations

import re

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def safe_error(exc: Exception) -> str:
    msg = str(exc)
    msg = re.sub(r"key=[^'\s]+", "key=REDACTED", msg)
    msg = re.sub(r"Bearer\s+\S+", "Bearer REDACTED", msg)
    return re.sub(r"(sk|gsk|AIza)-[A-Za-z0-9_\-]+", "REDACTED", msg)
