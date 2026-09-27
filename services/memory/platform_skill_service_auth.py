"""Dedicated server-to-server authentication for the Maven skill bridge."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

SERVICE_HEADER = "X-MavenSync-Service"
TIMESTAMP_HEADER = "X-MavenSync-Timestamp"
SIGNATURE_HEADER = "X-MavenSync-Signature"
DEFAULT_SERVICE_ID = "maven-harness"
MAX_CLOCK_SKEW_SECONDS = 300


def canonical_request(*, timestamp: str, method: str, path: str, query: str) -> bytes:
    return f"{timestamp}\n{method.upper()}\n{path}\n{query}".encode("utf-8")


def sign_request(*, secret: str, timestamp: str, method: str, path: str, query: str) -> str:
    return hmac.new(secret.encode("utf-8"), canonical_request(timestamp=timestamp, method=method, path=path, query=query), hashlib.sha256).hexdigest()


def verify_request(*, service: str | None, timestamp: str | None, signature: str | None, method: str, path: str, query: str, secret: str | None = None, expected_service: str | None = None, now: float | None = None) -> bool:
    configured_secret = secret if secret is not None else os.getenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET")
    configured_service = expected_service if expected_service is not None else os.getenv("MAVENSYNC_HQ_SKILL_SERVICE_ID", DEFAULT_SERVICE_ID)
    if not configured_secret or not service or not timestamp or not signature or not hmac.compare_digest(service, configured_service):
        return False
    try:
        issued = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = int(time.time() if now is None else now)
    if abs(current - issued) > MAX_CLOCK_SKEW_SECONDS:
        return False
    expected = sign_request(secret=configured_secret, timestamp=timestamp, method=method, path=path, query=query)
    return hmac.compare_digest(signature.lower(), expected)

