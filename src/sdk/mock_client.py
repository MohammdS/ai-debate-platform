
from src.sdk.base_client import BaseAIClient


class MockAIClient(BaseAIClient):
    """Mock AI client for testing and development."""

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Simulates a response based on the role and last message."""
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        last_msg = messages[-1].get("content", "")

        if "impartial judge" in system_msg.lower():
            return "Based on the arguments presented, I declare Debater A the winner. Score: 85-75."

        return f"I strongly disagree with your point about '{last_msg[:20]}...'. My stance remains firm."
