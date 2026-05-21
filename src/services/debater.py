
from src.sdk.base_client import BaseAIClient
from src.shared.gatekeeper import ApiGatekeeper


class Debater:
    """Represents a competitive AI debater."""

    def __init__(self, name: str, stance: str, topic: str,
                 client: BaseAIClient, gatekeeper: ApiGatekeeper):
        self.name = name
        self.stance = stance
        self.topic = topic
        self.client = client
        self.gatekeeper = gatekeeper
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return (
            f"You are a world-class competitive debater. Stance: {self.stance}. "
            f"Topic: {self.topic}. Win at all costs. Stand up for your ideas. "
            "Never concede. Be logical and persistent."
        )

    async def get_argument(self, history: list[dict[str, str]]) -> str:
        """Generates the next argument in the debate."""
        messages = [{"role": "system", "content": self.system_prompt}] + history
        return await self.gatekeeper.execute(self.client.generate_response, messages)
