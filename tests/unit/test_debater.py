import pytest

from src.sdk.mock_client import MockAIClient
from src.services.debater import Debater
from src.shared.gatekeeper import ApiGatekeeper


@pytest.mark.asyncio
async def test_debater_generate_argument():
    client = MockAIClient("test", "key")
    gatekeeper = ApiGatekeeper()
    debater = Debater("A", "Pro-AI", "AI Future", client, gatekeeper)

    arg = await debater.get_argument([{"role": "user", "content": "Hello"}])
    assert "stand firmly by my position" in arg
