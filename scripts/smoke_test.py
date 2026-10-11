#!/usr/bin/env python
"""Backend smoke test script.

Tests the complete backend stack in order:
1. Settings load
2. CORS parsing
3. NVIDIA model configuration
4. FastAPI import
5. /health endpoint
6. NVIDIA direct connectivity
7. /assistant/chat endpoint

Output format:
[PASS] component
[FAIL] component - safe reason

Overall: PASS/FAIL

Run from repository root:
    python -m scripts.smoke_test
"""

from __future__ import annotations

import sys
import time
from typing import Callable


def print_status(component: str, success: bool, detail: str = "", elapsed: float | None = None) -> bool:
    """Print test status and return success flag."""
    if success:
        elapsed_str = f" - {elapsed:.1f}s" if elapsed is not None else ""
        print(f"[PASS] {component}{elapsed_str}")
    else:
        detail_str = f" - {detail}" if detail else ""
        print(f"[FAIL] {component}{detail_str}")
    return success


def run_test(name: str, test_fn: Callable[[], tuple[bool, str, float | None]]) -> tuple[bool, str, float | None]:
    """Run a test function and catch exceptions."""
    try:
        return test_fn()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


def test_settings() -> tuple[bool, str, float | None]:
    """Test 1: Settings load without exception."""
    from app.core.config import get_settings
    settings = get_settings()
    return True, "", None


def test_cors() -> tuple[bool, str, float | None]:
    """Test 2: CORS parses correctly as list."""
    from app.core.config import get_settings
    settings = get_settings()
    cors = settings.cors_allowed_origins
    expected = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if cors == expected:
        return True, "", None
    return False, f"CORS mismatch: got {cors}, expected {expected}", None


def test_nvidia_config() -> tuple[bool, str, float | None]:
    """Test 3: NVIDIA configuration is correct."""
    from app.core.config import get_settings
    settings = get_settings()

    checks = [
        (settings.nvidia_api_key is not None and settings.nvidia_api_key != "your_nvidia_api_key_here", "NVIDIA_API_KEY not configured"),
        (settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1", f"NVIDIA_BASE_URL incorrect: {settings.nvidia_base_url}"),
        (settings.nvidia_model == "google/diffusiongemma-26b-a4b-it", f"NVIDIA_MODEL incorrect: {settings.nvidia_model}"),
        (settings.nvidia_timeout_seconds == 120.0, f"NVIDIA_TIMEOUT_SECONDS incorrect: {settings.nvidia_timeout_seconds}"),
        (settings.nvidia_connect_timeout == 10.0, f"NVIDIA_CONNECT_TIMEOUT incorrect: {settings.nvidia_connect_timeout}"),
        (settings.nvidia_max_retries == 1, f"NVIDIA_MAX_RETRIES incorrect: {settings.nvidia_max_retries}"),
        (settings.nvidia_max_concurrent_requests == 2, f"NVIDIA_MAX_CONCURRENT_REQUESTS incorrect: {settings.nvidia_max_concurrent_requests}"),
        (settings.is_llm_configured(), "LLM not configured"),
    ]

    for check, msg in checks:
        if not check:
            return False, msg, None
    return True, "", None


def test_fastapi_import() -> tuple[bool, str, float | None]:
    """Test 4: FastAPI imports without error."""
    from app.api.main import app
    if app is None:
        return False, "FastAPI app is None", None
    routes = [r.path for r in app.routes]
    required = ["/health", "/assistant/chat"]
    for r in required:
        if r not in routes:
            return False, f"Missing route: {r}", None
    return True, "", None


def test_health() -> tuple[bool, str, float | None]:
    """Test 5: /health returns 200 with expected structure."""
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    start = time.perf_counter()
    r = client.get("/health")
    elapsed = time.perf_counter() - start

    if r.status_code != 200:
        return False, f"HTTP {r.status_code}", elapsed

    data = r.json()
    expected_keys = {"status", "llm", "data", "econometrics"}
    if set(data.keys()) != expected_keys:
        return False, f"Unexpected keys: {data.keys()}", elapsed

    if data.get("llm") != "configured":
        return False, f"LLM status: {data.get('llm')}", elapsed

    return True, "", elapsed


def test_nvidia_connectivity() -> tuple[bool, str, float | None]:
    """Test 6: Direct NVIDIA connectivity test."""
    from app.core.config import get_settings
    from app.core.llm import get_sync_client

    settings = get_settings()
    client = get_sync_client()

    # Use a prompt that reliably gets a response
    messages = [{"role": "user", "content": "Say hello"}]
    start = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.0,
            max_tokens=20,
            stream=False,
        )
        elapsed = time.perf_counter() - start
        content = response.choices[0].message.content
        # API call succeeded - that's what matters for connectivity
        return True, "", elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start
        error_msg = str(e)
        if "nvapi-" in error_msg:
            idx = error_msg.find("nvapi-")
            error_msg = error_msg[:idx] + "nvapi-***REDACTED***"
        return False, f"{type(e).__name__}: {error_msg}", elapsed


def test_assistant_chat() -> tuple[bool, str, float | None]:
    """Test 7: /assistant/chat returns 200 with valid response."""
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    payload = {
        "message": "Hello buddy",
        "page": "/",
        "page_context": "Monetary Policy Overview",
        "conversation": [],
    }
    start = time.perf_counter()
    r = client.post("/assistant/chat", json=payload)
    elapsed = time.perf_counter() - start

    if r.status_code != 200:
        detail = r.json().get("detail", "No detail") if r.status_code >= 400 else "Unknown"
        return False, f"HTTP {r.status_code}: {detail}", elapsed

    data = r.json()
    required_keys = {"answer", "page_context", "model", "warnings"}
    if not required_keys.issubset(data.keys()):
        return False, f"Missing keys in response: {required_keys - set(data.keys())}", elapsed

    if not data.get("answer") or not data["answer"].strip():
        return False, "Empty answer", elapsed

    if data.get("model") != "google/diffusiongemma-26b-a4b-it":
        return False, f"Wrong model: {data.get('model')}", elapsed

    return True, "", elapsed


def main() -> int:
    """Run all smoke tests in sequence."""
    print("Backend Smoke Test")
    print("=" * 50)

    tests = [
        ("Settings", test_settings),
        ("CORS", test_cors),
        ("NVIDIA configuration", test_nvidia_config),
        ("FastAPI import", test_fastapi_import),
        ("/health", test_health),
        ("NVIDIA connectivity", test_nvidia_connectivity),
        ("/assistant/chat", test_assistant_chat),
    ]

    all_passed = True
    for name, test_fn in tests:
        success, detail, elapsed = run_test(name, test_fn)
        if not print_status(name, success, detail, elapsed):
            all_passed = False
            if name in ("Settings", "CORS", "NVIDIA configuration", "FastAPI import"):
                print("\nCritical failure, stopping dependent tests.")
                break

    print("=" * 50)
    print(f"Overall: {'PASS' if all_passed else 'FAIL'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())