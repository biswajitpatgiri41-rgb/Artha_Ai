#!/usr/bin/env python
"""Standalone NVIDIA connectivity test using OpenAI SDK.

Tests the NVIDIA OpenAI-compatible endpoint independently from FastAPI and Next.js.
Uses the centralized configuration from app.core.config.

Sends:
    USER: Reply with exactly OK

Uses the configured model (NVIDIA_MODEL).

Prints ONLY:
    Model: <model>
    Base URL: <base_url>
    Elapsed: <seconds>s
    Status: OK / FAILED
    Response: <response>

if successful.

On failure prints:
    Model: <model>
    Base URL: <base_url>
    Elapsed: <seconds>s
    Status: FAILED
    Exception: <exception_class>
    Error: <safe_error_message>

NEVER prints:
    API key
    Authorization header
    full environment variables
"""

from __future__ import annotations

import sys
import time

from app.core.config import get_settings
from app.core.llm import get_sync_client


def main() -> int:
    settings = get_settings()
    model = settings.nvidia_model
    base_url = settings.nvidia_base_url

    messages = [
        {"role": "user", "content": "Reply with exactly OK"},
    ]

    client = get_sync_client()
    start_time = time.perf_counter()

    print(f"Model: {model}")
    print(f"Base URL: {base_url}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            max_tokens=10,
            stream=False,
        )
        elapsed = time.perf_counter() - start_time
        content = response.choices[0].message.content
        print(f"Elapsed: {elapsed:.3f}s")
        print("Status: OK")
        print(f"Response: {content.strip()}")
        return 0

    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s")
        print("Status: FAILED")
        print(f"Exception: {exc.__class__.__name__}")
        # Safe error message without credentials
        error_msg = str(exc)
        if "nvapi-" in error_msg:
            idx = error_msg.find("nvapi-")
            error_msg = error_msg[:idx] + "nvapi-***REDACTED***"
        print(f"Error: {error_msg}")
        # Print HTTP status if available
        status_code = getattr(exc, "status_code", None)
        if status_code:
            print(f"HTTP Status: {status_code}")
        return 1


if __name__ == "__main__":
    sys.exit(main())