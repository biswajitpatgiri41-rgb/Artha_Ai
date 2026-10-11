"""In-process API telemetry used by the local admin operations dashboard."""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any


class RequestTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = time.monotonic()
        self._active = 0
        self._events: deque[dict[str, Any]] = deque(maxlen=500)
        self._visitors: dict[str, dict[str, Any]] = {}

    def begin(self) -> float:
        started = time.monotonic()
        with self._lock:
            self._active += 1
        return started

    def finish(
        self,
        started: float,
        method: str,
        path: str,
        status_code: int,
        bytes_in: int,
        bytes_out: int,
        client_ip: str | None = None,
    ) -> None:
        now = time.monotonic()
        event = {
            "id": f"{int(now * 1_000_000)}-{status_code}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "error" if status_code >= 500 else "warning" if status_code >= 400 else "success",
            "message": f"{method} {path} | {status_code} | {(now - started) * 1000:.0f} ms | in {bytes_in} B / out {bytes_out} B",
            "source": "FastAPI",
        }
        with self._lock:
            self._active = max(0, self._active - 1)
            if not path.startswith("/api/admin/"):
                self._events.appendleft({**event, "_monotonic": now, "_bytes_in": bytes_in, "_bytes_out": bytes_out, "_status": status_code})
                if client_ip:
                    visitor = self._visitors.setdefault(client_ip, {"ip_address": client_ip, "first_seen": event["timestamp"], "request_count": 0})
                    visitor["last_seen"] = event["timestamp"]
                    visitor["last_path"] = path
                    visitor["request_count"] += 1
                    visitor["_monotonic"] = now

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            recent = [event for event in self._events if now - event["_monotonic"] <= 60]
            traffic_window = [event for event in recent if now - event["_monotonic"] <= 10]
            events = [{key: value for key, value in event.items() if not key.startswith("_")} for event in list(self._events)[:20]]
            active = self._active
            uptime = now - self._started

        seconds = max(1.0, min(10.0, now - traffic_window[-1]["_monotonic"]) if traffic_window else 1.0)
        byte_in = sum(event["_bytes_in"] for event in traffic_window) / seconds
        byte_out = sum(event["_bytes_out"] for event in traffic_window) / seconds
        error_count = sum(event["_status"] >= 500 for event in recent)
        metrics: dict[str, Any] = {
            "cpu": None,
            "memory": None,
            "disk": None,
            "network": (byte_in + byte_out) / (1024 * 1024),
            "incomingMBps": byte_in / (1024 * 1024),
            "outgoingMBps": byte_out / (1024 * 1024),
            "uptime": uptime,
            "requestsPerSecond": len(recent) / min(60, max(1, uptime)),
            "errorRate": (error_count / len(recent) * 100) if recent else 0.0,
            "activeConnections": active,
            "sampledAt": datetime.now(timezone.utc).isoformat(),
            "trafficScope": "HTTP requests handled by this API process; rolling 10-second byte rate",
        }
        try:
            import psutil

            metrics["cpu"] = psutil.cpu_percent(interval=None)
            metrics["memory"] = psutil.virtual_memory().percent
            metrics["disk"] = psutil.disk_usage("/").percent
        except (ImportError, OSError, RuntimeError):
            pass
        return {"metrics": metrics, "activity": events, "request_count_60s": len(recent)}

    def active_visitors(self, active_seconds: int = 300) -> dict[str, Any]:
        """Return distinct client IPs that made a non-admin request recently.

        This is an IP-based estimate, not a count of physical devices or people.
        Data is held in process memory only and expires from this view after five minutes.
        """
        now = time.monotonic()
        cutoff = now - active_seconds
        with self._lock:
            active = [
                {key: value for key, value in visitor.items() if not key.startswith("_")}
                for visitor in self._visitors.values()
                if visitor["_monotonic"] >= cutoff
            ]
            # Bound memory without persisting visitor addresses.
            self._visitors = {
                ip: visitor for ip, visitor in self._visitors.items()
                if visitor["_monotonic"] >= now - max(active_seconds * 4, 3600)
            }
        active.sort(key=lambda visitor: visitor["last_seen"], reverse=True)
        return {
            "active_window_seconds": active_seconds,
            "active_ip_count": len(active),
            "visitors": active,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "note": "Distinct IP addresses observed on requests to this API in the last five minutes; NAT, shared networks, and proxies can combine or obscure devices. In-memory only.",
        }


telemetry = RequestTelemetry()
