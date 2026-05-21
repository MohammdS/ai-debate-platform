
from src.sdk.base_client import BaseAIClient


class MockAIClient(BaseAIClient):
    """Mock AI client for testing and development."""

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Simulates a response based on the role and last message."""
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        last_msg = messages[-1].get("content", "")
        round_num = (len(messages) // 2) + 1

        if "impartial judge" in system_msg.lower():
            return "Based on the 20 rounds of intense debate, I declare Debater A the winner. Score: 85-75."

        stances = {
            "Debater_A": "Pro-stance argument",
            "Debater_B": "Opposing-stance rebuttal"
        }

        return (
            f"Round {round_num}: I stand firmly by my position. "
            f"Regarding your last point: '{last_msg[:30]}...', "
            "it fails to address the core logical necessity of my stance. "
            "I seek victory and will not concede."
        )

