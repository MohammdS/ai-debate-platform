import argparse
import asyncio

from src.sdk.factory import AIClientFactory
from src.services.debater import Debater
from src.services.judge import Judge
from src.services.orchestrator import DebateOrchestrator
from src.services.exporter import DebateExporter
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper

async def main():
    parser = argparse.ArgumentParser(description="AI Debate Platform")
    parser.add_argument("--topic", default="Is AI a threat?", help="Debate topic")
    parser.add_argument("--stance-a", default="AI is a significant threat", help="Stance for A")
    parser.add_argument("--stance-b", default="AI is not a threat", help="Stance for B")
    parser.add_argument("--provider", default="mock", help="AI provider (openai, mock)")
    args = parser.parse_args()

    config = ConfigManager()
    gatekeeper = ApiGatekeeper(rpm_limit=config.get_value("api", "rate_limit_rpm", 30))

    # Setup AI clients
    api_key = config.get_api_key(args.provider)
    client_a = AIClientFactory.create_client(args.provider, "debater-a", api_key)
    client_b = AIClientFactory.create_client(args.provider, "debater-b", api_key)
    client_j = AIClientFactory.create_client(args.provider, "judge", api_key)

    # Setup roles
    debater_a = Debater("A", args.stance_a, args.topic, client_a, gatekeeper)
    debater_b = Debater("B", args.stance_b, args.topic, client_b, gatekeeper)
    judge = Judge(client_j, gatekeeper)

    # Run debate
    orchestrator = DebateOrchestrator(debater_a, debater_b, judge)
    verdict = await orchestrator.run_debate()

    # Export results
    exporter = DebateExporter()
    exporter.export_to_markdown(args.topic, orchestrator.history, verdict)
    exporter.export_to_json(args.topic, orchestrator.history, verdict)
    print(f"\n[SUCCESS] Debate exported to results/debate_transcript.md")


if __name__ == "__main__":
    asyncio.run(main())
