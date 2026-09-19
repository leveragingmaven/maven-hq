"""Focused regression tests for the Phase 1 static-serving patch:

- HTML stays revalidated (no-cache) — both from /static and from
  serve_html_with_nonce (index/login/backgrounds).
- JS/CSS receive a bounded browser-cache lifetime instead of blanket
  Cache-Control: no-cache.
- Compressible text static responses are gzip encoded when the client sends
  Accept-Encoding: gzip.
- Already-compressed / binary assets are NOT transformed (identity bytes).
"""

import gzip

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.static_serving import (
    ALREADY_COMPRESSED_CONTENT_TYPES,
    HTML_CACHE_CONTROL,
    MEDIA_ASSETS_CACHE_CONTROL,
    TEXT_ASSETS_CACHE_CONTROL,
    RevalidatingStaticFiles,
    SelectiveGZipMiddleware,
)


@pytest.fixture()
def static_client(tmp_path):
    """Tiny app: the real mount + real middleware, no app.py import."""
    static_root = tmp_path / "static"
    static_root.mkdir()
    big_js = b"var x = " + b"1" * 4096 + b";\n"  # > minimum_size so gzip applies
    (static_root / "app.js").write_bytes(big_js)
    (static_root / "style.css").write_bytes(b"body { color: " + b"a" * 4096 + b"; }\n")
    (static_root / "index.html").write_bytes(b"<!doctype html><html><body>hi</body></html>\n")
    # Incompressible binary: 1 KB of high-entropy bytes (gzip of it would be larger).
    (static_root / "logo.png").write_bytes(bytes(range(256)) * 4)

    app = FastAPI()
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1024, compresslevel=6)
    app.mount("/static", RevalidatingStaticFiles(directory=str(static_root)), name="static")
    return TestClient(app)


def test_html_from_static_is_no_cache(static_client):
    r = static_client.get("/static/index.html")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-cache"


def test_js_gets_text_asset_cache_control(static_client):
    r = static_client.get("/static/app.js")
    assert r.status_code == 200
    assert r.headers["cache-control"] == TEXT_ASSETS_CACHE_CONTROL
    assert "max-age=300" in r.headers["cache-control"]
    assert "no-cache" != r.headers["cache-control"]


def test_css_gets_text_asset_cache_control(static_client):
    r = static_client.get("/static/style.css")
    assert r.status_code == 200
    assert r.headers["cache-control"] == TEXT_ASSETS_CACHE_CONTROL


def test_media_gets_immutable_cache_control(static_client):
    r = static_client.get("/static/logo.png")
    assert r.status_code == 200
    assert r.headers["cache-control"] == MEDIA_ASSETS_CACHE_CONTROL
    assert "immutable" in r.headers["cache-control"]


def test_text_static_is_gzipped_when_requested(static_client):
    r = static_client.get(
        "/static/app.js", headers={"Accept-Encoding": "gzip"}
    )
    assert r.status_code == 200
    # Middleware must have declared gzip on the wire...
    assert r.headers.get("content-encoding") == "gzip"
    # ...and the gzip stream must decode back to the exact original file
    # (httpx transparently decompresses, so a valid round-trip proves the
    # body really was gzip, not identity bytes mislabeled as gzip).
    assert r.content == b"var x = " + b"1" * 4096 + b";\n"
    # The ETag must still be present for conditional revalidation.
    assert r.headers.get("etag")


def test_text_static_identity_when_not_requested(static_client):
    r = static_client.get("/static/app.js", headers={"Accept-Encoding": "identity"})
    assert r.status_code == 200
    assert "content-encoding" not in r.headers
    assert len(r.content) > 4096


def test_binary_asset_not_transformed(static_client):
    r = static_client.get("/static/logo.png", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert "content-encoding" not in r.headers
    assert r.headers["content-type"].startswith("image/png")
    # Exact bytes round-trip: no (double) compression applied.
    assert r.content == bytes(range(256)) * 4


def test_svg_is_compressible_not_excluded():
    """SVG is text — it must remain in the compressible set."""
    assert "image/svg" not in ALREADY_COMPRESSED_CONTENT_TYPES


def test_compressed_media_types_present():
    for ct in ("image/png", "video/", "font/woff2", "application/zip", "text/event-stream"):
        assert ct in ALREADY_COMPRESSED_CONTENT_TYPES


# ---- serve_html_with_nonce keeps HTML revalidated --------------------------


def test_serve_html_with_nonce_sets_no_cache():
    from src.app_helpers import serve_html_with_nonce

    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("<html><script nonce=\"{{CSP_NONCE}}\"></script></html>")
        req = type("R", (), {"state": type("S", (), {"csp_nonce": "abc123"})()})()
        resp = serve_html_with_nonce(request=req, file_path=path)
        assert resp.headers["cache-control"] == "no-cache"
        assert "abc123" in resp.body.decode()
    finally:
        os.unlink(path)


# ---- constants sanity ------------------------------------------------------


def test_policy_constants_are_stable():
    assert HTML_CACHE_CONTROL == "no-cache"
    assert TEXT_ASSETS_CACHE_CONTROL == "max-age=300, stale-while-revalidate=86400"
    assert MEDIA_ASSETS_CACHE_CONTROL == "max-age=2592000, immutable"
