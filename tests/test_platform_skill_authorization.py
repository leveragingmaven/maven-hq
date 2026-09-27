import json
from pathlib import Path

import pytest

from services.memory.platform_skill_authorization import (
    PlatformSkillAllowlistError,
    authorize_platform_skill,
    content_revision,
    load_platform_allowlist,
)


MARKDOWN = "---\nname: campaign-strategy\n---\n\n## Procedure\n\n- plan\n"


def skill(**overrides):
    value = {
        "id": "campaign-strategy",
        "name": "campaign-strategy",
        "status": "published",
        "platforms": [],
        "requires_toolsets": [],
        "fallback_for_toolsets": [],
    }
    value.update(overrides)
    return value


def write_allowlist(path: Path, rows):
    path.write_text(json.dumps({"version": 1, "skills": rows}), encoding="utf-8")


def test_allowlisted_matching_revision_is_authorized(tmp_path):
    path = tmp_path / "platform_skills.json"
    write_allowlist(path, [{"skillId": "campaign-strategy", "revision": content_revision(MARKDOWN)}])
    grants = load_platform_allowlist(path)
    assert authorize_platform_skill(skill(), MARKDOWN, grants)


def test_default_deny_disabled_and_revision_mismatch(tmp_path):
    path = tmp_path / "platform_skills.json"
    write_allowlist(path, [{"skillId": "campaign-strategy", "revision": content_revision(MARKDOWN), "enabled": False}])
    grants = load_platform_allowlist(path)
    assert not authorize_platform_skill(skill(), MARKDOWN, grants)
    assert not authorize_platform_skill(skill(), MARKDOWN + "changed", grants)
    assert not authorize_platform_skill(skill(), MARKDOWN, ())


def test_owner_cannot_override_platform_authorization(tmp_path):
    path = tmp_path / "platform_skills.json"
    write_allowlist(path, [{"skillId": "campaign-strategy", "revision": content_revision(MARKDOWN)}])
    grants = load_platform_allowlist(path)
    assert authorize_platform_skill(skill(owner="private-owner"), MARKDOWN, grants)
    assert not authorize_platform_skill(skill(id="other-skill", name="other-skill", owner="platform-owner"), MARKDOWN, grants)
    assert not authorize_platform_skill(skill(owner="platform-owner"), MARKDOWN, ())


def test_existing_publication_platform_and_toolset_gates_apply(tmp_path):
    path = tmp_path / "platform_skills.json"
    write_allowlist(path, [{"skillId": "campaign-strategy", "revision": content_revision(MARKDOWN)}])
    grants = load_platform_allowlist(path)
    assert not authorize_platform_skill(skill(status="draft"), MARKDOWN, grants)
    assert not authorize_platform_skill(skill(platforms=["instagram"]), MARKDOWN, grants)
    assert authorize_platform_skill(skill(platforms=["instagram"]), MARKDOWN, grants, platform="instagram") is True
    gated = skill(requires_toolsets=["creator"])
    assert not authorize_platform_skill(gated, MARKDOWN, grants, active_toolsets=[])
    assert authorize_platform_skill(gated, MARKDOWN, grants, active_toolsets=["creator"])
    assert not authorize_platform_skill(skill(fallback_for_toolsets=["creator"]), MARKDOWN, grants, active_toolsets=["creator"])


def test_malformed_allowlist_fails_closed(tmp_path):
    path = tmp_path / "platform_skills.json"
    path.write_text("{\"version\": 1, \"skills\": [{\"skillId\": \"x\"}]}", encoding="utf-8")
    with pytest.raises(PlatformSkillAllowlistError):
        load_platform_allowlist(path)
