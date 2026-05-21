import time

import pytest

from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_gatekeeper_rate_limit():
    gatekeeper = ApiGatekeeper(rpm_limit=600) # 10 calls per second

    async def mock_call():
        return "done"

    start_time = time.time()
    await gatekeeper.execute(mock_call)
    await gatekeeper.execute(mock_call)
    end_time = time.time()

    # Second call should wait at least 0.1s
    assert end_time - start_time >= 0.05
