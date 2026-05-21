
from src.services.debater import Debater
from src.services.judge import Judge
from src.shared.logger import setup_logger


class DebateOrchestrator:
    """Orchestrates the flow of a 20-message AI debate."""

    def __init__(self, debater_a: Debater, debater_b: Debater, judge: Judge, rounds: int = 10):
        self.debater_a = debater_a
        self.debater_b = debater_b
        self.judge = judge
        self.rounds = rounds
        self.history: list[dict[str, str]] = []
        self.logger = setup_logger()

    async def run_debate(self) -> str:
        """Executes the 20-round debate and returns the judge's verdict."""
        self.logger.info(f"Starting debate on topic: {self.debater_a.topic}")

        for round_num in range(1, self.rounds + 1):
            self.logger.info(f"Round {round_num}/{self.rounds}")

            # Debater A turn
            arg_a = await self.debater_a.get_argument(self.history)
            self.history.append({"role": "user", "name": "Debater_A", "content": arg_a})
            print(f"\nDebater A: {arg_a}")

            # Debater B turn
            arg_b = await self.debater_b.get_argument(self.history)
            self.history.append({"role": "user", "name": "Debater_B", "content": arg_b})
            print(f"\nDebater B: {arg_b}")

        self.logger.info("Debate concluded. Requesting verdict...")
        verdict = await self.judge.evaluate(self.history)
        print(f"\nJUDGE VERDICT:\n{verdict}")
        return verdict
