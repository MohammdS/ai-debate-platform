from __future__ import annotations

import argparse
import asyncio

from src.cli.menu import interactive_menu
from src.cli.runner import run_debate
from src.shared.version import VERSION


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Debate Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to launch the interactive menu.",
    )
    parser.add_argument("--version", action="version", version=f"ai-debate-platform {VERSION}")
    parser.add_argument("--topic",           default=None)
    parser.add_argument("--stance-a",        default=None, dest="stance_a")
    parser.add_argument("--stance-b",        default=None, dest="stance_b")
    parser.add_argument("--provider-a",      default="zai",  dest="provider_a",
                        help="groq | gemini | openai | zai | mock")
    parser.add_argument("--provider-b",      default="groq", dest="provider_b",
                        help="groq | gemini | openai | zai | mock")
    parser.add_argument("--judge-provider",  default="groq", dest="judge_provider",
                        help="groq | gemini | openai | zai | mock")
    args = parser.parse_args()

    if not args.topic or not args.stance_a or not args.stance_b:
        params = interactive_menu()
    else:
        params = {
            "topic":         args.topic,
            "stance_a":      args.stance_a,
            "stance_b":      args.stance_b,
            "provider_a":    args.provider_a,
            "provider_b":    args.provider_b,
            "judge_provider": args.judge_provider,
        }

    asyncio.run(run_debate(**params))


if __name__ == "__main__":
    main()
