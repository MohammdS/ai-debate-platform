"""Smoke test for the z.ai client. Requires ZAI_API_KEY in environment."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from src.sdk.zai_client import ZaiClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


async def main() -> None:
    api_key = os.getenv("ZAI_API_KEY", "")
    if not api_key:
        print("ERROR: ZAI_API_KEY is not set.")
        sys.exit(1)

    client = ZaiClient(model_name="glm-4.5-flash", api_key=api_key)
    messages = [{"role": "user", "content": "Say hello briefly."}]

    print("Sending request to z.ai...")
    response = await client.generate_response(messages)
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
