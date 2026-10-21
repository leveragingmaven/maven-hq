# tests/test_security_headers_middleware.py
"""
Focused regression coverage for `SecurityHeadersMiddleware`
(core/middleware.py), added alongside the HSTS + Permissions-Policy
hardening:

  1. HSTS is emitted only for HTTPS requests, including those reaching
     the app over a reverse proxy (`X-Forwarded-Proto: https`).
  2. HSTS is absent on plain HTTP so local/dev deployments are unaffected.
  3. `Permissions-Policy` locks down camera/geolocation but preserves
     same-origin microphone access (`microphone=(self)`), so the app's
     own voice/STT flow (`getUserMedia({ audio: true })`) keeps working.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.middleware import SecurityHeadersMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    def root():
        return {"ok": True}

    return app


def _client(base_url="http://testserver"):
    return TestClient(_build_app(), base_url=base_url)


def test_hsts_absent_on_plain_http():
    response = _client().get("/")

    assert "strict-transport-security" not in response.headers


def test_hsts_present_for_direct_https_requests():
    response = _client(base_url="https://testserver").get("/")

    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_hsts_present_via_x_forwarded_proto_https():
    response = _client().get("/", headers={"X-Forwarded-Proto": "https"})

    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_permissions_policy_locks_camera_and_geolocation_but_allows_self_microphone():
    response = _client().get("/")

    policy = response.headers["permissions-policy"]
    assert policy == "camera=(), microphone=(self), geolocation=()"

    # Explicitly pin the contract the reviewer flagged: an empty allowlist
    # would also block the app's own same-origin voice/STT button.
    assert "microphone=()" not in policy
    assert "microphone=(self)" in policy


# --- FRAME_ANCESTORS allowlist (iframe compatibility) ----------------------

import pytest

from core.middleware import frame_ancestors_allowlist


@pytest.fixture
def frame_env(monkeypatch):
    def _set(value):
        monkeypatch.setenv("FRAME_ANCESTORS", value)
    monkeypatch.delenv("FRAME_ANCESTORS", raising=False)
    return _set


def test_allowlist_unset_defaults_to_deny(frame_env):
    assert frame_ancestors_allowlist() is None
    response = _client().get("/")
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_allowlist_valid_self_and_origin(frame_env):
    frame_env("'self',https://command.mavensync.space")
    assert frame_ancestors_allowlist() == "'self' https://command.mavensync.space"
    response = _client().get("/")
    # Valid allowlist: CSP governs; XFO omitted (cannot express allowlists).
    assert "x-frame-options" not in response.headers
    assert (
        "frame-ancestors 'self' https://command.mavensync.space"
        in response.headers["content-security-policy"]
    )


def test_allowlist_rejects_http_origin_fails_closed(frame_env):
    frame_env("http://evil.example")
    assert frame_ancestors_allowlist() is None
    response = _client().get("/")
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_allowlist_rejects_path_query_and_credentials(frame_env):
    for bad in (
        "https://command.mavensync.space/embed",
        "https://command.mavensync.space?x=1",
        "https://command.mavensync.space#frag",
        "https://user:pass@command.mavensync.space",
        "https://command.mavensync.space, javascript:alert(1)",
        "frame-ancestors *",
        "'unsafe-inline'",
    ):
        frame_env(bad)
        assert frame_ancestors_allowlist() is None, bad


def test_allowlist_allows_explicit_port_and_self_only(frame_env):
    frame_env("'self'")
    assert frame_ancestors_allowlist() == "'self'"
    frame_env("https://app.example.com:8443")
    assert frame_ancestors_allowlist() == "https://app.example.com:8443"


def test_allowlist_preserves_other_csp_directives(frame_env):
    frame_env("'self',https://command.mavensync.space")
    response = _client().get("/")
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'nonce-" in csp
    assert "frame-src 'self'" in csp
