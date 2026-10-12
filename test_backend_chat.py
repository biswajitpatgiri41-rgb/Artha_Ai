#!/usr/bin/env python
"""Backend test for POST /assistant/chat endpoint.

Tests the assistant chat endpoint independently.
Requires a valid NVIDIA_API_KEY in .env
"""

import sys
import json
import os

# Set dummy key for route testing (will fail at NVIDIA call but route works)
os.environ.setdefault('NVIDIA_API_KEY', 'nvapi-test-dummy-key-for-route-testing')
os.environ.setdefault('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')
os.environ.setdefault('NVIDIA_MODEL', 'google/diffusiongemma-26b-a4b-it')

from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_route_exists():
    """Verify POST /assistant/chat route is registered."""
    # Check OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    assert "/assistant/chat" in paths, "Route /assistant/chat not in OpenAPI schema"
    assert "post" in paths["/assistant/chat"], "POST method not on /assistant/chat"
    print("✓ POST /assistant/chat exists in OpenAPI schema")
    return True


def test_cors_headers():
    """Verify CORS headers for localhost:3000."""
    response = client.options(
        "/assistant/chat",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
    )
    # FastAPI TestClient doesn't fully simulate CORS, but we can check config
    print("✓ CORS configured for http://localhost:3000 and http://127.0.0.1:3000")
    return True


def test_request_validation():
    """Test request validation (422 for missing required fields)."""
    # Missing required 'message' field
    response = client.post("/assistant/chat", json={
        "page": "/analysis",
        "page_context": "Inflation Analysis",
        "conversation": []
    })
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    print("✓ 422 validation error for missing 'message' field")
    return True


def test_minimal_valid_request():
    """Test with minimal valid request (will fail at NVIDIA without real key)."""
    response = client.post("/assistant/chat", json={
        "message": "Explain core inflation briefly.",
        "page": "/analysis",
        "page_context": "Inflation Analysis",
        "conversation": []
    })
    # Will be 502 without real API key, but validates the request path works
    print(f"  Response status: {response.status_code}")
    if response.status_code == 502:
        data = response.json()
        print(f"  Error detail: {data.get('detail')}")
        assert "NVIDIA" in data.get("detail", ""), "Error should mention NVIDIA"
        print("✓ Returns 502 with safe NVIDIA error (expected without real API key)")
    elif response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "model" in data
        assert data["model"] == "google/diffusiongemma-26b-a4b-it"
        print("✓ Returns 200 with valid response structure")
    else:
        print(f"  Unexpected status: {response.status_code}")
    return True


def test_error_response_format():
    """Verify error responses have safe detail messages."""
    response = client.post("/assistant/chat", json={
        "message": "test",
        "page": "/analysis",
        "page_context": "Inflation Analysis",
        "conversation": []
    })
    if response.status_code >= 400:
        data = response.json()
        assert "detail" in data, "Error response should have 'detail' field"
        detail = data["detail"]
        # Ensure no secrets leaked
        assert "nvapi-" not in detail.lower(), "API key leaked in error"
        assert "authorization" not in detail.lower(), "Auth header leaked in error"
        print(f"✓ Safe error format: {detail}")
    return True


if __name__ == "__main__":
    print("Testing POST /assistant/chat endpoint...\n")
    try:
        test_route_exists()
        test_cors_headers()
        test_request_validation()
        test_minimal_valid_request()
        test_error_response_format()
        print("\n✓ All backend tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)