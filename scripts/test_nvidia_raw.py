#!/usr/bin/env python
"""Standalone NVIDIA connectivity test using raw httpx.

Tests the NVIDIA OpenAI-compatible endpoint directly with raw HTTP,
bypassing the OpenAI SDK entirely. This isolates whether issues are
in the SDK layer or the network/endpoint itself.

Sends POST to: https://integrate.api.nvidia.com/v1/chat/completions

Headers:
    Authorization: Bearer <key>
    Content-Type: application/json

Body:
    {
      "model": "google/diffusiongemma-26b-a4b-it",
      "messages": [{"role": "user", "content": "Reply with exactly OK"}],
      "temperature": 0,
      "max_tokens": 10,
      "stream": false
    }

Timeout: 120 seconds (connect: 10s, read: 120s)

Prints ONLY:
    Model: <model>
    Base URL: <base_url>
    Elapsed: <seconds>s
    HTTP Status: <status>
    Status: OK / FAILED
    Response: <response>

NEVER prints:
    API key
    Authorization header
    full request/response body
"""

from __future__ import annotations

import sys
import time

import httpx

from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    model = settings.nvidia_model
    base_url = settings.nvidia_base_url
    api_key = settings.nvidia_api_key

    if not api_key:
        print("Error: NVIDIA_API_KEY not configured", flush=True)
        return 1

    # Build the full endpoint URL
    endpoint = base_url.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly OK"}],
        "temperature": 0,
        "max_tokens": 10,
        "stream": False,
    }

    # Use the configured timeout (120s) for full test
    test_read_timeout = settings.nvidia_timeout_seconds
    timeout = httpx.Timeout(
        connect=settings.nvidia_connect_timeout,
        read=test_read_timeout,
        write=test_read_timeout,
        pool=settings.nvidia_connect_timeout,
    )

    print(f"Model: {model}", flush=True)
    print(f"Base URL: {base_url}", flush=True)
    print(f"Endpoint: {endpoint}", flush=True)
    print(f"Timeouts: connect={settings.nvidia_connect_timeout}s read={test_read_timeout}s", flush=True)

    start_time = time.perf_counter()

    try:
        print("Creating httpx client...", flush=True)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            print("Client created, sending request...", flush=True)
            response = client.post(endpoint, headers=headers, json=payload)
            print(f"Response received: {response.status_code}", flush=True)
        
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s", flush=True)
        print(f"HTTP Status: {response.status_code}", flush=True)

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print("Status: OK", flush=True)
            print(f"Response: {content.strip()}", flush=True)
            return 0
        else:
            print("Status: FAILED", flush=True)
            error_text = response.text[:200] if response.text else "No response body"
            print(f"Error Response: {error_text}", flush=True)
            return 1

    except httpx.TimeoutException as exc:
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s", flush=True)
        print("Status: FAILED", flush=True)
        print(f"Exception: {exc.__class__.__name__}", flush=True)
        print(f"Error: Request timed out ({type(exc).__name__})", flush=True)
        return 1

    except httpx.ConnectError as exc:
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s", flush=True)
        print("Status: FAILED", flush=True)
        print(f"Exception: {exc.__class__.__name__}", flush=True)
        print(f"Error: Connection failed - {exc}", flush=True)
        return 1

    except httpx.HTTPStatusError as exc:
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s", flush=True)
        print(f"HTTP Status: {exc.response.status_code}", flush=True)
        print("Status: FAILED", flush=True)
        print(f"Exception: {exc.__class__.__name__}", flush=True)
        print(f"Error: HTTP {exc.response.status_code}", flush=True)
        return 1

    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        print(f"Elapsed: {elapsed:.3f}s", flush=True)
        print("Status: FAILED", flush=True)
        print(f"Exception: {exc.__class__.__name__}", flush=True)
        error_msg = str(exc)
        if "nvapi-" in error_msg:
            idx = error_msg.find("nvapi-")
            error_msg = error_msg[:idx] + "nvapi-***REDACTED***"
        print(f"Error: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())