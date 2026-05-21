
from src.sdk.base_client import BaseAIClient
from src.shared.gatekeeper import ApiGatekeeper


class Judge:
    """Represents an impartial AI judge."""

    def __init__(self, client: BaseAIClient, gatekeeper: ApiGatekeeper):
        self.client = client
        self.gatekeeper = gatekeeper
        self.system_prompt = (
            "You are an impartial judge for an intellectual debate. "
            "Evaluate logical consistency, evidence, and persuasiveness. "
            "Declare a winner and provide scores (0-100) for both."
        )

    async def evaluate(self, transcript: list[dict[str, str]]) -> str:
        """Evaluates the entire debate transcript."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Please judge this debate:\n{transcript}"}
        ]
        return await self.gatekeeper.execute(self.client.generate_response, messages)
