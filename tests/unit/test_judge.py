import pytest

from src.sdk.mock_client import MockAIClient
from src.services.judge import Judge
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_judge_evaluate():
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper()
    judge = Judge(client, gatekeeper)

    verdict = await judge.evaluate([{"role": "user", "content": "Argument"}])
    assert "winner" in verdict.lower()
