"""Exercise real discovery filters without logging fixture content."""
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import platform_skill_service_routes as routes
from services.memory.skills import SkillsManager
from services.memory.platform_skill_authorization import content_revision
from test_platform_skill_service_routes import auth_headers, SECRET

@pytest.mark.parametrize("case,reason", [
    ("valid", None),
    ("query", "query_mismatch"),
    ("status", "not_published"),
    ("platform", "platform_ineligible"),
    ("required", "required_toolsets_missing"),
    ("fallback", "fallback_toolset_active"),
    ("disabled", "disabled"),
    ("revision", "revision_mismatch"),
    ("missing", None),
    ("large", "markdown_too_large"),
])
def test_discovery_reports_only_fixed_reasons(tmp_path, monkeypatch, caplog, case, reason):
    name = "private-fixture"
    markdown = (
        "---\nname: private-fixture\ndescription: PRIVATE_DESCRIPTION\n"
        + ("status: draft\n" if case == "status" else "status: published\n")
        + ("platforms: [private-platform]\n" if case == "platform" else "")
        + ("requires_toolsets: [private-toolset]\n" if case == "required" else "")
        + ("fallback_for_toolsets: [private-toolset]\n" if case == "fallback" else "")
        + "---\nPRIVATE_CONTENT"
        + ("x" * 12000 if case == "large" else "")
    )
    folder = tmp_path / "skills" / "content" / name
    folder.mkdir(parents=True)
    if case != "missing":
        (folder / "SKILL.md").write_text(markdown, encoding="utf-8")
    revision = content_revision(markdown)
    allowlist = tmp_path / "platform_skills.json"
    allowlist.write_text(json.dumps({"version": 1, "skills": [{
        "skillId": name,
        "revision": content_revision("different") if case == "revision" else revision,
        "enabled": case != "disabled",
    }]}), encoding="utf-8")
    monkeypatch.setattr(routes, "PLATFORM_SKILLS_FILE", str(allowlist))
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET", SECRET)
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_ID", "maven-harness")
    app = FastAPI()
    app.include_router(routes.setup_platform_skill_service_routes(SkillsManager(str(tmp_path))))
    query = "q=PRIVATE_QUERY" if case == "query" else "toolsets=private-toolset" if case == "fallback" else ""
    path = "/internal/maven/platform-skills"
    caplog.set_level(logging.INFO, logger=routes.__name__)
    with TestClient(app) as client:
        response = client.get(path + ("?" + query if query else ""), headers=auth_headers(path, query))
        assert response.status_code == 200
        assert response.json()["count"] == (1 if case == "valid" else 0)
        before = len(caplog.records)
        assert client.get(path).status_code == 401
        assert len(caplog.records) == before
    records = [r.getMessage() for r in caplog.records if r.name == routes.__name__]
    assert len(records) == 1
    record = json.loads(records[0].split(" ", 1)[1])
    assert record["rejections"] == ({reason: 1} if reason else {})
    assert record["allowlistedDiscoveredCount"] == (0 if case == "missing" else 1)
    for private in (name, revision, SECRET, "PRIVATE_DESCRIPTION", "PRIVATE_CONTENT", "PRIVATE_QUERY", "private-platform", "private-toolset", str(tmp_path)):
        assert private not in records[0]
