"""Connectivity test for the NVIDIA LLM client.

The test sends a simple prompt and verifies that the response contains the
exact string ``CONNECTION_OK``.  It is intentionally minimal and does not
log any sensitive information.
"""

import asyncio

from app.core.llm import request_model
from app.core.config import get_settings


async def main():
    settings = get_settings()
    messages = [
        {"role": "system", "content": "You are a connectivity checker."},
        {"role": "user", "content": "Reply with exactly: CONNECTION_OK"},
    ]
    response = request_model(
        model=settings.nvidia_model,
        messages=messages,
        temperature=0.0,
        max_tokens=10,
    )
    if "CONNECTION_OK" in response:
        print("Connection test succeeded")
    else:
        raise RuntimeError("Connection test failed: unexpected response")


if __name__ == "__main__":
    asyncio.run(main())
