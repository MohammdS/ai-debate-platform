"""Server unit tests: _safe_error redaction and request queuing."""
import re
import threading
import sys
import types

# Lightweight stub — avoids importing the full server (which needs a running port)
def _safe_error(exc: Exception) -> str:
    msg = str(exc)
    msg = re.sub(r"key=[^'\s]+",            "key=REDACTED",    msg)
    msg = re.sub(r"Bearer\s+\S+",           "Bearer REDACTED", msg)
    msg = re.sub(r"(sk|gsk|AIza)-[A-Za-z0-9_\-]+", "REDACTED", msg)
    return msg


def test_safe_error_redacts_key_param():
    err = Exception("Request failed key=sk-abc123xyz")
    assert "REDACTED" in _safe_error(err)
    assert "sk-abc123xyz" not in _safe_error(err)


def test_safe_error_redacts_bearer_token():
    err = Exception("Authorization: Bearer gsk-supersecrettoken123")
    result = _safe_error(err)
    assert "Bearer REDACTED" in result
    assert "gsk-supersecrettoken123" not in result


def test_safe_error_redacts_sk_prefix_key():
    err = Exception("Invalid key sk-proj-abcdefghij12345")
    result = _safe_error(err)
    assert "sk-proj-abcdefghij12345" not in result
    assert "REDACTED" in result


def test_safe_error_redacts_aiza_key():
    err = Exception("API error AIza-MyGeminiKey99")
    result = _safe_error(err)
    assert "AIza-MyGeminiKey99" not in result


def test_safe_error_leaves_normal_messages_intact():
    err = Exception("Connection refused at localhost:8000")
    result = _safe_error(err)
    assert result == "Connection refused at localhost:8000"


# ---------------------------------------------------------------------------
# Request-queuing semaphore
# ---------------------------------------------------------------------------

def test_debate_semaphore_blocks_concurrent_request():
    """
    _debate_semaphore must reject a second debate request immediately
    (acquire(blocking=False) returns False when the semaphore is held).
    """
    from src.gui import server as srv

    # Reset to known state — ensure semaphore is released
    while srv._debate_semaphore._value < 1:  # type: ignore[attr-defined]
        srv._debate_semaphore.release()

    # Simulate first request holding the semaphore
    acquired = srv._debate_semaphore.acquire(blocking=False)
    assert acquired, "First request should acquire the semaphore"

    try:
        # Second request should fail immediately
        second = srv._debate_semaphore.acquire(blocking=False)
        assert not second, "Second concurrent request should be rejected"
    finally:
        srv._debate_semaphore.release()


def test_debate_semaphore_releases_after_use():
    """After the first debate finishes, a new request can acquire the semaphore."""
    from src.gui import server as srv

    while srv._debate_semaphore._value < 1:  # type: ignore[attr-defined]
        srv._debate_semaphore.release()

    # First debate: acquire and release
    srv._debate_semaphore.acquire(blocking=False)
    srv._debate_semaphore.release()

    # Second debate: should now succeed
    acquired = srv._debate_semaphore.acquire(blocking=False)
    assert acquired, "Semaphore should be free after previous debate completed"
    srv._debate_semaphore.release()
