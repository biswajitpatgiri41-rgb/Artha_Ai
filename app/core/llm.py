"""Centralised NVIDIA OpenAI‑compatible client.

The module exposes :func:`get_async_client` which returns a singleton instance of
``AsyncOpenAI`` configured to point at the NVIDIA endpoint.  The client is
created lazily and re‑used for all subsequent calls.

The :func:`request_model` helper abstracts the common pattern of sending a
prompt to a model and receiving a structured JSON response.  It accepts a
model name, temperature, and max tokens, and performs basic timeout and
exception handling.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx
from openai import (
    AsyncOpenAI,
    OpenAI,
    APIError,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    InternalServerError,
    BadRequestError,
)

from .config import get_settings

__all__ = ["get_async_client", "get_sync_client", "request_model", "request_model_async", "ProviderError"]

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Provider error with classified status code for HTTP mapping."""
    
    def __init__(self, message: str, status_code: int = 502, original: Exception | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.original = original


def _build_timeout_config(settings) -> httpx.Timeout:
    """Build httpx Timeout with explicit connect/read/write/pool timeouts."""
    return httpx.Timeout(
        connect=settings.nvidia_connect_timeout,
        read=settings.nvidia_timeout_seconds,
        write=settings.nvidia_timeout_seconds,
        pool=settings.nvidia_connect_timeout,
    )


def get_sync_client() -> OpenAI:
    """Return a singleton synchronous OpenAI client configured for NVIDIA.

    Uses explicit httpx timeout configuration.
    """

    if not hasattr(get_sync_client, "_client"):
        settings = get_settings()
        timeout_config = _build_timeout_config(settings)
        get_sync_client._client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=timeout_config,
            max_retries=settings.nvidia_max_retries,
        )  # type: ignore[arg-type]
    return get_sync_client._client


def get_async_client() -> AsyncOpenAI:
    """Return a singleton asynchronous OpenAI client configured for NVIDIA.

    Uses explicit httpx timeout configuration. Preferred for async FastAPI routes.
    """

    if not hasattr(get_async_client, "_client"):
        settings = get_settings()
        timeout_config = _build_timeout_config(settings)
        get_async_client._client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=timeout_config,
            max_retries=settings.nvidia_max_retries,
        )  # type: ignore[arg-type]
    return get_async_client._client


def _classify_provider_error(exc: Exception) -> ProviderError:
    """Classify OpenAI SDK and httpx exceptions into ProviderError with appropriate HTTP status."""

    # httpx exceptions (for raw HTTP requests)
    if isinstance(exc, httpx.ConnectTimeout):
        return ProviderError(
            "AI provider connection timed out",
            status_code=504,
            original=exc,
        )
    if isinstance(exc, httpx.ReadTimeout):
        return ProviderError(
            "AI provider response timed out",
            status_code=504,
            original=exc,
        )
    if isinstance(exc, httpx.ConnectError):
        return ProviderError(
            "Could not connect to AI provider",
            status_code=502,
            original=exc,
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 401:
            return ProviderError(
                "NVIDIA authentication failed. Check API key.",
                status_code=502,
                original=exc,
            )
        if status_code == 403:
            return ProviderError(
                "NVIDIA provider/model access error.",
                status_code=502,
                original=exc,
            )
        if status_code == 404:
            return ProviderError(
                "NVIDIA configured model or endpoint unavailable.",
                status_code=502,
                original=exc,
            )
        if status_code == 429:
            return ProviderError(
                "NVIDIA request limit reached.",
                status_code=429,
                original=exc,
            )
        if 500 <= status_code < 600:
            return ProviderError(
                "AI provider temporarily unavailable.",
                status_code=502,
                original=exc,
            )
        # Other HTTP status errors
        return ProviderError(
            "NVIDIA HTTP error: " + str(status_code),
            status_code=502,
            original=exc,
        )

    # Authentication/authorization errors (OpenAI SDK)
    if isinstance(exc, AuthenticationError):
        return ProviderError(
            "NVIDIA authentication failed. Check API key.",
            status_code=502,  # Provider configuration error
            original=exc,
        )
    if isinstance(exc, PermissionDeniedError):
        return ProviderError(
            "NVIDIA permission denied. Check API key permissions.",
            status_code=502,
            original=exc,
        )

    # Rate limiting
    if isinstance(exc, RateLimitError):
        return ProviderError(
            "NVIDIA rate limit exceeded.",
            status_code=429,
            original=exc,
        )

    # Timeout
    if isinstance(exc, APITimeoutError):
        return ProviderError(
            "NVIDIA request timed out.",
            status_code=504,
            original=exc,
        )

    # Bad request (invalid parameters, model, etc.)
    if isinstance(exc, BadRequestError):
        status_code = getattr(exc, "status_code", None)
        return ProviderError(
            "AI provider rejected the request configuration.",
            status_code=status_code if status_code and 400 <= status_code < 500 else 502,
            original=exc,
        )

    # Connection errors
    if isinstance(exc, APIConnectionError):
        return ProviderError(
            "NVIDIA connection failed.",
            status_code=502,
            original=exc,
        )

    # Not found (model/endpoint)
    if isinstance(exc, NotFoundError):
        return ProviderError(
            "NVIDIA model or endpoint not found.",
            status_code=502,
            original=exc,
        )

    # Server errors
    if isinstance(exc, InternalServerError):
        return ProviderError(
            "NVIDIA internal server error.",
            status_code=502,
            original=exc,
        )

    # Generic API error - try to extract status code
    if isinstance(exc, APIError):
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            return ProviderError(
                "NVIDIA authentication failed. Check API key.",
                status_code=502,
                original=exc,
            )
        if status_code == 403:
            return ProviderError(
                "NVIDIA permission denied. Check API key permissions.",
                status_code=502,
                original=exc,
            )
        if status_code == 404:
            return ProviderError(
                "NVIDIA model or endpoint not found.",
                status_code=502,
                original=exc,
            )
        if status_code == 429:
            return ProviderError(
                "NVIDIA rate limit exceeded.",
                status_code=429,
                original=exc,
            )
        if status_code and 500 <= status_code < 600:
            return ProviderError(
                "NVIDIA server error (" + str(status_code) + ").",
                status_code=502,
                original=exc,
            )

    # Unknown error
    return ProviderError(
        "AI provider is currently unavailable.",
        status_code=502,
        original=exc,
    )
def request_model(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> str:
    """Send a synchronous request to the NVIDIA OpenAI‑compatible endpoint.

    Parameters
    ----------
    model:
        The model name to use.
    messages:
        List of message dicts for the chat completion.
    temperature:
        Sampling temperature.
    max_tokens:
        Maximum tokens to generate.
    timeout:
        Optional per-request timeout override (seconds). If None, uses client default.
    **kwargs:
        Additional arguments forwarded to :meth:`OpenAI.chat.completions.create`.
    """

    client = get_sync_client()
    start_time = time.perf_counter()
    logger.info("assistant request: model=%s messages=%d approx_chars=%d", model, len(messages), sum(len(m.get("content", "")) for m in messages))
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - network errors
        elapsed = time.perf_counter() - start_time
        logger.error("assistant request failed: model=%s latency=%.3fs error_class=%s error=%s", model, elapsed, exc.__class__.__name__, exc)
        raise _classify_provider_error(exc) from exc

    elapsed = time.perf_counter() - start_time
    content = response.choices[0].message.content
    logger.info("assistant response: model=%s latency=%.3fs status=success", model, elapsed)
    return content


async def request_model_async(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> str:
    """Send an asynchronous request to the NVIDIA OpenAI‑compatible endpoint.

    Parameters
    ----------
    model:
        The model name to use.
    messages:
        List of message dicts for the chat completion.
    temperature:
        Sampling temperature.
    max_tokens:
        Maximum tokens to generate.
    timeout:
        Optional per-request timeout override (seconds). If None, uses client default.
    **kwargs:
        Additional arguments forwarded to :meth:`AsyncOpenAI.chat.completions.create`.
    """

    client = get_async_client()
    start_time = time.perf_counter()
    logger.info("assistant request (async): model=%s messages=%d approx_chars=%d", model, len(messages), sum(len(m.get("content", "")) for m in messages))
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - network errors
        elapsed = time.perf_counter() - start_time
        logger.error("assistant request failed (async): model=%s latency=%.3fs error_class=%s error=%s", model, elapsed, exc.__class__.__name__, exc)
        raise _classify_provider_error(exc) from exc

    elapsed = time.perf_counter() - start_time
    content = response.choices[0].message.content
    logger.info("assistant response (async): model=%s latency=%.3fs status=success", model, elapsed)
    return content
