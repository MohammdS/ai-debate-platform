import asyncio
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from httpx import HTTPStatusError as _HTTPStatusError
except ImportError:
    _HTTPStatusError = None  # type: ignore[assignment,misc]

_RATE_LIMITS_PATH = Path(__file__).resolve().parents[2] / "config" / "rate_limits.json"


def _load_limits(provider: str) -> dict:
    """Load rate limit config for a provider from config/rate_limits.json."""
    try:
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        return data.get(provider, data.get("default", {}))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class ApiGatekeeper:
    """
    Centralized API call manager.

    - Rate limiting: enforces minimum interval between calls (RPM-based).
    - Timeout:       each call wrapped in asyncio.wait_for to avoid hangs.
    - Retry:         exponential backoff up to max_retries attempts.
    - Logging:       every call attempt and outcome is logged.
    - Config:        limits read from config/rate_limits.json by provider.

    API keys are never stored here — they live in env vars only.
    """

    def __init__(self, rpm_limit: int | None = None, timeout: float | None = None,
                 max_retries: int | None = None, provider: str = "default"):
        limits = _load_limits(provider)
        self.rpm_limit   = rpm_limit   if rpm_limit   is not None else limits.get("rpm_limit",       30)
        self.timeout     = timeout     if timeout     is not None else limits.get("timeout_seconds", 60.0)
        self.max_retries = max_retries if max_retries is not None else limits.get("max_retries",      3)
        self.interval    = 60.0 / self.rpm_limit
        self._last_call  = 0.0
        self._rate_lock  = asyncio.Lock()
        self._logger     = logging.getLogger("gatekeeper")
        self._call_count = 0

    async def _throttle(self) -> None:
        """Acquire rate-limit slot; lock released before the API call."""
        async with self._rate_lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_call = time.monotonic()

    async def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute func(*args, **kwargs) with rate limiting, timeout, and retries.

        Logs each attempt and its outcome.
        Raises the last exception if all retries are exhausted.
        """
        await self._throttle()
        self._call_count += 1
        call_id = self._call_count
        self._logger.info("API call #%d starting (timeout=%.1fs, retries=%d)",
                          call_id, self.timeout, self.max_retries)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=self.timeout
                )
                self._logger.info("API call #%d succeeded on attempt %d",
                                  call_id, attempt + 1)
                return result
            except TimeoutError as exc:
                self._logger.warning("API call #%d timed out (attempt %d/%d)",
                                     call_id, attempt + 1, self.max_retries)
                last_exc = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            except Exception as exc:
                # 429 Too Many Requests — back off longer than standard retry
                if _HTTPStatusError and isinstance(exc, _HTTPStatusError) and exc.response.status_code == 429:
                    retry_after = int(exc.response.headers.get("retry-after", 60))
                    self._logger.warning("API call #%d got 429 — waiting %ds before retry",
                                         call_id, retry_after)
                    await asyncio.sleep(retry_after)
                else:
                    self._logger.warning("API call #%d failed (attempt %d/%d): %s",
                                         call_id, attempt + 1, self.max_retries, exc)
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                last_exc = exc
                continue

        self._logger.error("API call #%d exhausted all %d retries",
                           call_id, self.max_retries)
        raise last_exc
