"""Pin the narrowly scoped browser-auth exemption for Maven's private bridge."""

import os
import re


def _app_source() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "app.py"), encoding="utf-8") as fh:
        return fh.read()


def _patterns(src: str):
    start = src.find("AUTH_EXEMPT_PATTERNS")
    assert start >= 0
    lb = src.find("[", start)
    depth = 0
    for i in range(lb, len(src)):
        if src[i] == "[":
            depth += 1
        elif src[i] == "]":
            depth -= 1
            if depth == 0:
                body = src[lb + 1:i]
                return [re.compile(p) for p in re.findall(r'_re\.compile\(\s*r"([^"]+)"\s*\)', body)]
    raise AssertionError("AUTH_EXEMPT_PATTERNS is not closed")


def test_collection_route_is_exactly_exempt_and_hmac_remains_required():
    src = _app_source()
    assert '"/internal/maven/platform-skills"' in src
    assert any(p.match("/internal/maven/platform-skills/skill") for p in _patterns(src))
    # The route itself must continue to call the existing HMAC verifier.
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "routes", "platform_skill_service_routes.py"), encoding="utf-8") as fh:
        route = fh.read()
    assert "verify_request(" in route
    assert "authenticate(request)" in route


def test_skill_route_is_exempt_but_unrelated_internal_routes_are_not():
    patterns = _patterns(_app_source())
    assert any(p.match("/internal/maven/platform-skills/hook-writing") for p in patterns)
    assert not any(p.match("/internal/other-service") for p in patterns)
    assert not any(p.match("/internal/maven/platform-skills") for p in patterns)


def test_existing_browser_auth_exemptions_and_protection_remain_unchanged():
    src = _app_source()
    assert '"/api/auth/login"' in src
    assert '"/login"' in src
    assert 'if path.startswith("/api/")' in src
    assert 'return RedirectResponse(url="/login", status_code=302)' in src
