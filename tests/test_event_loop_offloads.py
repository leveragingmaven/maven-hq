"""Regression tests: event-loop blocking operations must stay off the loop.

Phase 2 of the HQ stabilization work identified synchronous operations that
executed directly inside ``async def`` request handlers / middleware on
Odysseus's single uvicorn event loop. Production logs captured the signature:
~48 static requests stalled ~6.8s and released together when one handler
blocked the loop (single worker, shared loop).

These tests pin each corrected call site:

- app.py AuthMiddleware bearer path — bcrypt.checkpw (CPU-expensive) must run
  via asyncio.to_thread (mirrors the pinned login-path fix in
  tests/test_auth_event_loop.py).
- routes/task_routes.py delete_task — calendar cascade (sync httpx, up to
  10s per call) must run via asyncio.to_thread.
- routes/cookbook_routes.py model_serve — ollama free-port pick (sync ssh
  subprocess.run / blocking sockets) must run via asyncio.to_thread.
- routes/email_routes.py google_oauth_callback — token exchange + userinfo
  (sync httpx, 10s timeouts) must run via asyncio.to_thread.
- routes/contacts/contacts_routes.py — CardDAV fetch/create/update/delete
  (sync httpx) must run via asyncio.to_thread.
- src/task_scheduler.py _deliver_via_email and routes/email_pollers.py
  urgency alerts — sync SMTP (may also refresh a Google token via sync
  httpx) must run via asyncio.to_thread.

Behavioral tests drive the real route handlers with monkeypatched
``asyncio.to_thread`` (recording which functions were offloaded) — the same
technique as test_auth_event_loop.py. Modules too heavy to import in the
test process (app.py) are pinned at source level, following the existing
source-pin pattern (test_setup_device_auth_static.py).
"""

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


_REPO = Path(__file__).resolve().parent.parent


# ── Source pins (modules too heavy / side-effectful to import) ───────────


def test_auth_middleware_bearer_bcrypt_offloaded_to_thread():
    """app.py bearer-token branch must run the bcrypt candidate scan through
    asyncio.to_thread, not inline in the middleware coroutine."""
    src = (_REPO / "app.py").read_text(encoding="utf-8")
    assert "def _match_api_token():" in src, (
        "bcrypt candidate scan should live in a helper that can be offloaded"
    )
    assert "matched_id, matched_owner, matched_scopes = await _asyncio.to_thread(_match_api_token)" in src, (
        "bearer-token bcrypt scan must be offloaded via asyncio.to_thread"
    )
    # The helper must contain the checkpw call (so the inline loop is gone).
    helper_start = src.index("def _match_api_token():")
    helper_body = src[helper_start:helper_start + 600]
    assert "_bcrypt.checkpw(" in helper_body


def test_task_delete_cascade_offloaded_to_thread():
    src = (_REPO / "routes" / "task_routes.py").read_text(encoding="utf-8")
    assert "await asyncio.to_thread(_maybe_cascade_calendar_event, task)" in src
    # The old inline call must be gone (it used to run before db.delete).
    assert "_maybe_cascade_calendar_event(task)\n            db.delete(task)" not in src


def test_model_serve_port_pick_offloaded_to_thread():
    src = (_REPO / "routes" / "cookbook_routes.py").read_text(encoding="utf-8")
    assert re.search(
        r"await asyncio\.to_thread\(\s*_pick_free_port_for_ollama", src
    ), "ollama free-port pick must be offloaded via asyncio.to_thread"


def test_email_oauth_callback_http_offloaded_to_thread():
    src = (_REPO / "routes" / "email_routes.py").read_text(encoding="utf-8")
    assert "await asyncio.to_thread(_exchange_token)" in src
    assert "await asyncio.to_thread(_fetch_userinfo)" in src


def test_task_scheduler_email_delivery_offloaded_to_thread():
    src = (_REPO / "src" / "task_scheduler.py").read_text(encoding="utf-8")
    assert re.search(
        r"await asyncio\.to_thread\(\s*_send_smtp_message", src
    ), "_deliver_via_email must offload sync SMTP to a worker thread"


def test_email_pollers_urgency_send_offloaded_to_thread():
    src = (_REPO / "routes" / "email_pollers.py").read_text(encoding="utf-8")
    assert re.search(
        r"await asyncio\.to_thread\(\s*_send_smtp_message", src
    ), "urgency alert SMTP send must be offloaded to a worker thread"


# ── Behavioral: task delete cascade ──────────────────────────────────────

def _task_delete_endpoint():
    from tests.helpers.import_state import clear_fake_database_modules

    clear_fake_database_modules()

    import core.database as cdb
    import routes.task_routes as task_routes

    # Real SQLAlchemy session factory over the real ORM models (temp file —
    # in-memory SQLite + NullPool loses tables between connections).
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    import tempfile

    tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    engine = create_engine(
        f"sqlite:///{tmpdb.name}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    cdb.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    task_routes.SessionLocal = factory

    router = task_routes.setup_task_routes(MagicMock())
    for route in router.routes:
        path = getattr(route, "path", "")
        if path == "/api/tasks/{task_id}" and "DELETE" in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError("DELETE /api/tasks/{task_id} route not found")


@pytest.mark.asyncio
async def test_delete_task_cascade_runs_via_to_thread(monkeypatch):
    """Deleting a cookbook_serve task must run its calendar cascade (sync
    httpx inside) through asyncio.to_thread, never inline on the loop."""
    from tests.helpers.import_state import clear_fake_database_modules

    clear_fake_database_modules()
    import core.database as cdb
    import routes.task_routes as task_routes

    delete_task = _task_delete_endpoint()

    # Seed an active cookbook_serve task (the only action that cascades).
    db = task_routes.SessionLocal()
    try:
        task = cdb.ScheduledTask(
            id="cascade-target",
            owner="alice",
            name="Serve: test-model",
            prompt="{}",
            task_type="action",
            action="cookbook_serve",
            trigger_type="webhook",
            status="active",
            output_target="session",
        )
        db.add(task)
        db.commit()
    finally:
        db.close()

    offloaded = []

    async def fake_to_thread(fn, *args, **kwargs):
        offloaded.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr("routes.task_routes.asyncio.to_thread", fake_to_thread)

    request = SimpleNamespace(state=SimpleNamespace(current_user="alice"))
    result = await delete_task(request, "cascade-target")

    assert result == {"ok": True}
    assert task_routes._maybe_cascade_calendar_event in offloaded, (
        "calendar cascade (sync httpx) must be offloaded to a worker thread"
    )


# ── Behavioral: contacts CardDAV calls ───────────────────────────────────

def _contacts_endpoint(name):
    from routes.contacts.contacts_routes import setup_contacts_routes

    router = setup_contacts_routes()
    for route in router.routes:
        if getattr(getattr(route, "endpoint", None), "__name__", "") == name:
            return route.endpoint
    raise AssertionError(f"contacts endpoint {name!r} not found")


@pytest.mark.asyncio
async def test_contacts_list_fetch_runs_via_to_thread(monkeypatch):
    """GET /contacts list must run _fetch_contacts (sync CardDAV httpx inside)
    through asyncio.to_thread."""
    import routes.contacts.contacts_routes as cr

    sentinel_contacts = [{"uid": "u1", "name": "Test", "emails": [], "phones": []}]

    def fake_fetch(force=False):
        return sentinel_contacts

    monkeypatch.setattr(cr, "_fetch_contacts", fake_fetch)

    offloaded = []

    async def fake_to_thread(fn, *args, **kwargs):
        offloaded.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr("routes.contacts.contacts_routes.asyncio.to_thread", fake_to_thread)

    list_contacts = _contacts_endpoint("list_contacts")
    result = await list_contacts(_admin="")

    assert result["contacts"] == sentinel_contacts
    assert fake_fetch in offloaded, (
        "_fetch_contacts (sync CardDAV httpx) must be offloaded to a worker thread"
    )


@pytest.mark.asyncio
async def test_contacts_delete_runs_via_to_thread(monkeypatch):
    """DELETE /contacts/{uid} must run _delete_contact (sync CardDAV httpx,
    plus a forced re-fetch) through asyncio.to_thread."""
    import routes.contacts.contacts_routes as cr

    def fake_delete(uid):
        return True

    monkeypatch.setattr(cr, "_delete_contact", fake_delete)

    offloaded = []

    async def fake_to_thread(fn, *args, **kwargs):
        offloaded.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr("routes.contacts.contacts_routes.asyncio.to_thread", fake_to_thread)

    delete_contact = _contacts_endpoint("delete_contact")
    result = await delete_contact("u1", _admin="")

    assert result == {"success": True}
    assert fake_delete in offloaded, (
        "_delete_contact (sync CardDAV httpx) must be offloaded to a worker thread"
    )


# ── Behavioral: Google OAuth callback ────────────────────────────────────

class _FakeEmailRequest:
    """Minimal stand-in for starlette Request — the callback only reads headers."""
    headers = {"host": "localhost:7000"}


def _email_callback_endpoint():
    from routes.email_routes import setup_email_routes

    router = setup_email_routes()
    for route in router.routes:
        if route.path == "/api/email/oauth/google/callback" and "GET" in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError("google_oauth_callback route not found")


@pytest.mark.asyncio
async def test_oauth_callback_http_calls_run_via_to_thread(monkeypatch):
    """The Google OAuth callback's token exchange and userinfo fetch (sync
    httpx, 10s timeouts each) must both run through asyncio.to_thread."""
    from routes.email_helpers import make_oauth_state
    import unittest.mock as mock

    callback = _email_callback_endpoint()

    token_resp = mock.MagicMock()
    token_resp.raise_for_status = mock.MagicMock()
    token_resp.json.return_value = {
        "access_token": "ya29.t", "refresh_token": "r", "expires_in": 3600
    }
    userinfo_resp = mock.MagicMock()
    userinfo_resp.is_success = True
    userinfo_resp.json.return_value = {"email": "alice@x.com", "name": "Alice"}

    # DB lookup after the HTTP calls returns no row → account_not_found
    # redirect; the point of this test is the offload, not the persistence.
    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = None
    factory = MagicMock(return_value=db_mock)

    offloaded = []

    async def fake_to_thread(fn, *args, **kwargs):
        offloaded.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr("routes.email_routes.asyncio.to_thread", fake_to_thread)

    state = make_oauth_state("acct-ol", "alice")

    with mock.patch("httpx.post", return_value=token_resp), \
         mock.patch("httpx.get", return_value=userinfo_resp), \
         mock.patch("core.database.SessionLocal", factory):
        resp = await callback(
            code="4/code", state=state, error=None, request=_FakeEmailRequest()
        )

    loc = resp.headers["location"]
    assert "email_oauth_error=account_not_found" in loc
    assert len(offloaded) == 2, (
        f"both httpx calls (token exchange, userinfo) must be offloaded; got {len(offloaded)}"
    )
