import asyncio
import time
from collections.abc import Callable
from typing import Any


class ApiGatekeeper:
    """Centralized API call manager for rate limiting and retries."""

    def __init__(self, rpm_limit: int = 30):
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / rpm_limit
        self.last_call_time = 0.0
        self.lock = asyncio.Lock()

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Executes an API call with rate limiting and basic retry logic."""
        async with self.lock:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)

            self.last_call_time = time.time()

            # Simple retry logic for demonstration
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)
