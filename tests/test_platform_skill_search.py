"""Natural-language discovery must never bypass platform authorization."""
import json
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import platform_skill_service_routes as routes
from services.memory.skills import SkillsManager
from services.memory.platform_skill_authorization import content_revision
from test_platform_skill_service_routes import auth_headers, SECRET

OBJECTIVE = "strong social media hook for Instagram promotional post aimed at solo female entrepreneurs for MavenSync"
PATH = "/internal/maven/platform-skills"


def client_for(tmp_path, monkeypatch, gate="valid"):
    markdown = (
        "---\nname: hook-writing\nversion: 1.0.0\n"
        "description: Craft scroll-stopping hooks that capture attention in the first 1-3 seconds\n"
        "category: content\ntags: [hooks, engagement, social-media, copywriting]\n"
        + ("status: draft\n" if gate == "draft" else "status: published\n")
        + ("platforms: [instagram]\n" if gate == "platform" else "")
        + ("requires_toolsets: [creator]\n" if gate == "required" else "")
        + ("fallback_for_toolsets: [creator]\n" if gate == "fallback" else "")
        + "---\n\n## Procedure\nTest fixture only.\n"
    )
    folder = tmp_path / "skills" / "content" / "hook-writing"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(markdown, encoding="utf-8")
    revision = content_revision(markdown)
    rows = [] if gate == "unapproved" else [{
        "skillId": "hook-writing",
        "revision": content_revision("stale") if gate == "revision" else revision,
        "enabled": gate != "disabled",
    }]
    allowlist = tmp_path / "platform_skills.json"
    allowlist.write_text(json.dumps({"version": 1, "skills": rows}), encoding="utf-8")
    monkeypatch.setattr(routes, "PLATFORM_SKILLS_FILE", str(allowlist))
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET", SECRET)
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_ID", "maven-harness")
    app = FastAPI()
    app.include_router(routes.setup_platform_skill_service_routes(SkillsManager(str(tmp_path))))
    return TestClient(app), revision


@pytest.mark.parametrize("query,expected", [
    (OBJECTIVE, 1),
    ("configure database backups and restore PostgreSQL", 0),
    ("capture database backups", 0),
    ("content database migration", 0),
    ("content content database migration", 0),
    ("for the a to", 0),
    ("!!!", 0),
    ("hook-writing", 1),
    ("hooks", 1),
    ("hook", 1),
    ("SOCIAL MEDIA", 1),
    ("social-media", 1),
    ("copywriting", 1),
    ("", 1),
])
def test_search_relevance(tmp_path, monkeypatch, query, expected):
    client, revision = client_for(tmp_path, monkeypatch)
    params = urlencode({"q": query, "limit": 1})
    with client:
        response = client.get(PATH + "?" + params, headers=auth_headers(PATH, params))
    assert response.status_code == 200
    assert response.json()["count"] == expected
    if expected:
        assert response.json()["skills"][0]["id"] == "hook-writing"
        assert response.json()["skills"][0]["revision"] == revision


@pytest.mark.parametrize("gate", ["unapproved", "disabled", "revision", "draft", "platform", "required", "fallback"])
def test_relevant_query_cannot_override_gates(tmp_path, monkeypatch, gate):
    client, _ = client_for(tmp_path, monkeypatch, gate)
    params = urlencode({"q": OBJECTIVE, **({"toolsets": "creator"} if gate == "fallback" else {})})
    with client:
        response = client.get(PATH + "?" + params, headers=auth_headers(PATH, params))
        assert client.get(PATH + "?" + params).status_code == 401
    assert response.status_code == 200
    assert response.json()["skills"] == []
