from src.sdk.base_client import BaseAIClient


class MockAIClient(BaseAIClient):
    """Mock AI client for testing and development."""

    supports_web_search: bool = False

    def _check_api_key(self) -> None:
        """No-op: mock client does not require a real API key."""

    async def generate_response(self, messages: list[dict]) -> str:
        """Simulates a response based on the role and last message."""
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        last_msg = messages[-1].get("content", "")
        round_num = (len(messages) // 2) + 1

        if (
            "impartial judge" in system_msg.lower()
            or "strict, impartial debate judge" in system_msg.lower()
        ):
            return (
                "SCORES\n"
                "Pro   — Logic: 16/20 | Evidence: 17/20 | Rebuttal Quality: 15/20 | Relevance: 18/20 | Clarity: 16/20 | TOTAL: 82/100\n"
                "Contra — Logic: 14/20 | Evidence: 13/20 | Rebuttal Quality: 14/20 | Relevance: 15/20 | Clarity: 14/20 | TOTAL: 70/100\n\n"
                "WINNER: Pro\n"
                "REASONING: Pro consistently backed claims with verifiable data and directly rebutted "
                "every point raised by Contra. Contra relied on rhetorical questions without sufficient "
                "factual grounding, which cost them heavily on evidence and rebuttal quality."
            )

        role = "PRO" if "PRO debater" in system_msg else "CONTRA"
        return (
            f"[{role} | Round {round_num}] "
            f"Your claim — '{last_msg[:40]}...' — is factually weak and logically flawed. "
            "The evidence overwhelmingly supports my position and I will not concede this point. "
            "My stance stands."
        )
