from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from src.sdk.exceptions import AIClientError, RateLimitError
from src.shared.rate_config import DEFAULT_RPM_LIMIT, load_limits, load_pricing

_load_pricing = load_pricing  # kept for backward-compat imports


class ApiGatekeeper:
    """Centralized API call manager: rate limiting, timeout, retry, fallback,
    token tracking, cost estimation, and structured JSON logging.
    Rate limiting is enforced globally per provider."""

    _provider_locks: dict[str, asyncio.Lock] = {}
    _provider_loops: dict[str, asyncio.AbstractEventLoop | None] = {}
    _provider_last_call: dict[str, float] = {}
    @classmethod
    def _get_provider_lock(cls, provider: str) -> asyncio.Lock:
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if provider not in cls._provider_locks or cls._provider_loops.get(provider) is not loop:
            cls._provider_locks[provider]     = asyncio.Lock()
            cls._provider_loops[provider]     = loop
            cls._provider_last_call[provider] = 0.0
        return cls._provider_locks[provider]

    def __init__(self, rpm_limit: int | None = None, timeout: float | None = None,
                 max_retries: int | None = None, provider: str = "default",
                 model: str = "default"):
        limits = load_limits(provider)
        self._provider  = provider
        self._model     = model
        self._in_rate, self._out_rate = load_pricing(provider, model)
        self.rpm_limit    = rpm_limit   if rpm_limit   is not None else limits.get("rpm_limit",       DEFAULT_RPM_LIMIT)
        self.timeout      = timeout     if timeout     is not None else limits.get("timeout_seconds", 60.0)
        self.max_retries  = max_retries if max_retries is not None else limits.get("max_retries",      3)
        self._retry_after = limits.get("retry_after_seconds", 30)
        self.interval     = 60.0 / self.rpm_limit
        self._rate_lock   = self._get_provider_lock(provider)
        self._logger      = logging.getLogger("gatekeeper")
        self._call_count  = self.total_calls = self.total_errors = 0
        self.total_latency_ms = self.total_tokens_in = self.total_tokens_out = self.estimated_cost_usd = 0.0

    def get_stats(self) -> dict:
        return {"total_calls": self.total_calls, "total_latency_ms": self.total_latency_ms,
                "total_errors": self.total_errors, "total_tokens_in": self.total_tokens_in,
                "total_tokens_out": self.total_tokens_out,
                "estimated_cost_usd": round(self.estimated_cost_usd, 6)}

    def _read_usage(self, func: Callable) -> tuple[int, int]:
        usage = getattr(getattr(func, "__self__", None), "last_usage", {})
        return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))

    def _accrue(self, tokens_in: int, tokens_out: int) -> float:
        self.total_tokens_in += tokens_in; self.total_tokens_out += tokens_out  # noqa: E702
        cost = (tokens_in * self._in_rate + tokens_out * self._out_rate) / 1_000_000
        self.estimated_cost_usd += cost; return cost  # noqa: E702

    def _record_success(self, t_start: float, func: Callable) -> tuple[float, int, int, float]:
        latency = (time.monotonic() - t_start) * 1000
        t_in, t_out = self._read_usage(func)
        cost = self._accrue(t_in, t_out)
        self.total_calls += 1; self.total_latency_ms += latency  # noqa: E702
        return latency, t_in, t_out, cost

    async def _throttle(self) -> None:
        async with self._rate_lock:
            if (gap := self.interval - (time.monotonic() - self._provider_last_call[self._provider])) > 0:
                await asyncio.sleep(gap)
            self._provider_last_call[self._provider] = time.monotonic()

    def _log_structured(self, latency_ms: float, success: bool, error: str | None,
                        tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0) -> None:
        self._logger.debug(json.dumps({
            "event": "api_call", "provider": self._provider, "model": self._model,
            "latency_ms": round(latency_ms, 2), "success": success, "error": error,
            "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": round(cost, 6),
        }))

    async def _execute_with_retry(self, func: Callable, args: tuple, kwargs: dict,
                                  call_id: int, fallback_client: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            t_start = time.monotonic()
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
                latency, t_in, t_out, cost = self._record_success(t_start, func)
                self._logger.info("API call #%d succeeded (attempt %d, %d+%d tokens, $%.6f)",
                                  call_id, attempt + 1, t_in, t_out, cost)
                self._log_structured(latency, True, None, t_in, t_out, cost)
                return result
            except TimeoutError as exc:
                self._logger.warning("API call #%d timed out (attempt %d/%d)",
                                     call_id, attempt + 1, self.max_retries)
                last_exc = exc
            except RateLimitError as exc:
                self._logger.warning("API call #%d RateLimitError — waiting %ds",
                                     call_id, self._retry_after)
                last_exc = exc
                await asyncio.sleep(self._retry_after)
                continue
            except AIClientError as exc:
                self._logger.warning("API call #%d AIClientError (attempt %d/%d): %s",
                                     call_id, attempt + 1, self.max_retries, exc)
                last_exc = exc
                if fallback_client is not None:
                    self._logger.info("API call #%d — trying fallback client", call_id)
                    try:
                        fb_res = await asyncio.wait_for(
                            fallback_client.generate_response(*args, **kwargs), timeout=self.timeout)
                        lat, *_ = self._record_success(t_start, fallback_client.generate_response)
                        self._log_structured(lat, True, None)
                        return fb_res
                    except Exception as fb_exc:
                        self._logger.warning("Fallback also failed: %s", fb_exc)
                        last_exc = fb_exc
            except Exception as exc:
                self._logger.warning("API call #%d failed (attempt %d/%d): %s",
                                     call_id, attempt + 1, self.max_retries, exc)
                last_exc = exc
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        return last_exc  # sentinel: caller checks isinstance(result, Exception)

    async def execute(self, func: Callable, *args: Any,
                      fallback_client: Any = None, **kwargs: Any) -> Any:
        """Execute func with rate limiting, timeout, retries, and token tracking."""
        await self._throttle()
        self._call_count += 1
        call_id = self._call_count
        self._logger.info("API call #%d starting (timeout=%.1fs, retries=%d)",
                          call_id, self.timeout, self.max_retries)
        result = await self._execute_with_retry(func, args, kwargs, call_id, fallback_client)
        if isinstance(result, Exception):
            self.total_calls  += 1
            self.total_errors += 1
            self._log_structured(0.0, False, str(result))
            self._logger.error("API call #%d exhausted all %d retries", call_id, self.max_retries)
            raise result
        return result
