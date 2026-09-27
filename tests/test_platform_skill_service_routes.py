import hashlib
import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.platform_skill_service_routes import setup_platform_skill_service_routes
from services.memory.platform_skill_service_auth import sign_request
from services.memory.skills import SkillsManager


SECRET = "test-service-secret"
MARKDOWN = "---\nname: campaign-strategy\n---\n\n## Procedure\n\n- plan\n"


def write_skill(root: Path, *, name="campaign-strategy", status="published", platforms=None, toolsets=None):
    folder = root / "skills" / "general" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\nversion: 1.0.0\ncategory: general\nstatus: {status}\nconfidence: 0.9\nsource: learned\nowner: private-owner\n" +
        (f"platforms: [{platforms}]\n" if platforms else "") +
        (f"requires_toolsets: [{toolsets}]\n" if toolsets else "") +
        "---\n\n## Procedure\n\n- plan\n",
        encoding="utf-8",
    )


def client_for(tmp_path, rows):
    write_skill(tmp_path)
    data_file = tmp_path / "platform_skills.json"
    data_file.write_text(json.dumps({"version": 1, "skills": rows}), encoding="utf-8")
    import routes.platform_skill_service_routes as module
    module.PLATFORM_SKILLS_FILE = str(data_file)
    app = FastAPI()
    app.include_router(setup_platform_skill_service_routes(SkillsManager(str(tmp_path))))
    return TestClient(app)


def auth_headers(path, query="", method="GET"):
    timestamp = str(int(time.time()))
    return {
        "X-MavenSync-Service": "maven-harness",
        "X-MavenSync-Timestamp": timestamp,
        "X-MavenSync-Signature": sign_request(secret=SECRET, timestamp=timestamp, method=method, path=path, query=query),
    }


def test_service_list_and_retrieve_only_authorized_skill(tmp_path, monkeypatch):
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET", SECRET)
    client = client_for(tmp_path, [])
    markdown = tmp_path / "skills" / "general" / "campaign-strategy" / "SKILL.md"
    revision = "sha256:" + hashlib.sha256(markdown.read_text(encoding="utf-8").encode()).hexdigest()
    (tmp_path / "platform_skills.json").write_text(json.dumps({"version": 1, "skills": [{"skillId": "campaign-strategy", "revision": revision}]}), encoding="utf-8")
    started = time.perf_counter()
    response = client.get("/internal/maven/platform-skills", headers=auth_headers("/internal/maven/platform-skills"))
    list_elapsed = (time.perf_counter() - started) * 1000
    assert response.status_code == 200 and response.json()["count"] == 1
    query = f"revision={revision}"
    started = time.perf_counter()
    response = client.get(f"/internal/maven/platform-skills/campaign-strategy?{query}", headers=auth_headers("/internal/maven/platform-skills/campaign-strategy", query))
    retrieve_elapsed = (time.perf_counter() - started) * 1000
    assert response.status_code == 200 and response.json()["revision"] == revision
    print(f"platform skill bridge timing: list={list_elapsed:.2f}ms retrieve={retrieve_elapsed:.2f}ms")


def test_auth_and_authorization_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET", SECRET)
    client = client_for(tmp_path, [])
    path = "/internal/maven/platform-skills"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={**auth_headers(path), "X-MavenSync-Signature": "bad"}).status_code == 401
    assert client.get(path, headers=auth_headers(path)).json()["skills"] == []


def test_revision_unpublished_and_bounds_are_denied(tmp_path, monkeypatch):
    monkeypatch.setenv("MAVENSYNC_HQ_SKILL_SERVICE_SECRET", SECRET)
    client = client_for(tmp_path, [{"skillId": "campaign-strategy", "revision": "sha256:" + "0" * 64}])
    path = "/internal/maven/platform-skills/campaign-strategy"
    query = "revision=" + "sha256:" + "0" * 64
    assert client.get(f"{path}?{query}", headers=auth_headers(path, query)).status_code == 404
    assert client.get("/internal/maven/platform-skills?limit=999", headers=auth_headers("/internal/maven/platform-skills?limit=999", "limit=999")).status_code == 422
