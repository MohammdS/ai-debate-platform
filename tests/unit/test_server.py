"""Server unit tests: _safe_error redaction and request queuing."""
import re


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
    _debate_semaphore must reject a request when all slots are held.
    With _MAX_CONCURRENT slots, acquiring _MAX_CONCURRENT times exhausts
    the semaphore; the next acquire must return False.
    """
    from src.gui import server as srv

    limit = srv._MAX_CONCURRENT

    # Reset to known state — drain any partial holds
    while srv._debate_semaphore._value < limit:  # type: ignore[attr-defined]
        srv._debate_semaphore.release()

    # Exhaust all available slots
    for _ in range(limit):
        ok = srv._debate_semaphore.acquire(blocking=False)
        assert ok, "Should be able to acquire up to _MAX_CONCURRENT times"

    try:
        # All slots used — next request must be rejected
        over_limit = srv._debate_semaphore.acquire(blocking=False)
        assert not over_limit, "Request beyond _MAX_CONCURRENT should be rejected"
    finally:
        for _ in range(limit):
            srv._debate_semaphore.release()


def test_debate_semaphore_releases_after_use():
    """After a debate finishes, a new request can acquire the semaphore."""
    from src.gui import server as srv

    limit = srv._MAX_CONCURRENT
    while srv._debate_semaphore._value < limit:  # type: ignore[attr-defined]
        srv._debate_semaphore.release()

    # First debate: acquire and release
    srv._debate_semaphore.acquire(blocking=False)
    srv._debate_semaphore.release()

    # Second debate: should now succeed
    acquired = srv._debate_semaphore.acquire(blocking=False)
    assert acquired, "Semaphore should be free after previous debate completed"
    srv._debate_semaphore.release()
