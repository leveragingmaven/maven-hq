"""Deny-by-default authorization for Maven platform skills.

The allowlist is operator-managed data under ``DATA_DIR``.  It is an
additional gate on top of the normal owner, publication, platform, and
toolset checks; it does not change skill ownership or grant customer access.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

_REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_ENTRIES = 1024


class PlatformSkillAllowlistError(ValueError):
    """Raised when the operator allowlist is malformed."""


@dataclass(frozen=True)
class PlatformSkillGrant:
    skill_id: str
    revision: str
    enabled: bool = True


def content_revision(markdown: str) -> str:
    """Return the stable revision used by the operator allowlist and cache."""
    if not isinstance(markdown, str):
        raise TypeError("skill markdown must be text")
    return "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def load_platform_allowlist(path: str | Path) -> tuple[PlatformSkillGrant, ...]:
    """Load and validate the operator file; malformed input fails closed."""
    file_path = Path(path)
    if not file_path.exists():
        return ()
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlatformSkillAllowlistError("platform skill allowlist is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("skills"), list):
        raise PlatformSkillAllowlistError("platform skill allowlist must be version 1 with a skills list")
    rows = payload["skills"]
    if len(rows) > _MAX_ENTRIES:
        raise PlatformSkillAllowlistError("platform skill allowlist is too large")
    grants: list[PlatformSkillGrant] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {"skillId", "revision", "enabled"}:
            raise PlatformSkillAllowlistError("platform skill allowlist entry is malformed")
        skill_id = row.get("skillId")
        revision = row.get("revision")
        enabled = row.get("enabled", True)
        if not isinstance(skill_id, str) or not skill_id.strip() or len(skill_id) > 128:
            raise PlatformSkillAllowlistError("platform skill allowlist skillId is invalid")
        if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
            raise PlatformSkillAllowlistError("platform skill allowlist revision is invalid")
        if not isinstance(enabled, bool):
            raise PlatformSkillAllowlistError("platform skill allowlist enabled flag is invalid")
        skill_id = skill_id.strip()
        if skill_id in seen:
            raise PlatformSkillAllowlistError("platform skill allowlist contains duplicate skillId")
        seen.add(skill_id)
        grants.append(PlatformSkillGrant(skill_id, revision, enabled))
    return tuple(grants)


def authorize_platform_skill(
    skill: Mapping[str, Any],
    markdown: str,
    grants: Sequence[PlatformSkillGrant],
    *,
    platform: str | None = None,
    active_toolsets: Sequence[str] | None = None,
) -> bool:
    """Return whether a skill passes every existing gate and the allowlist."""
    if not isinstance(skill, Mapping) or not isinstance(markdown, str):
        return False
    skill_id = skill.get("id") or skill.get("name")
    if not isinstance(skill_id, str) or not skill_id.strip() or skill.get("name") != skill_id:
        return False
    if skill.get("status") != "published":
        return False
    required_platforms = skill.get("platforms") or []
    if not isinstance(required_platforms, list) or any(not isinstance(item, str) for item in required_platforms):
        return False
    if required_platforms and (not isinstance(platform, str) or platform not in required_platforms):
        return False
    required_toolsets = skill.get("requires_toolsets") or []
    fallback_toolsets = skill.get("fallback_for_toolsets") or []
    if not isinstance(required_toolsets, list) or not isinstance(fallback_toolsets, list):
        return False
    if any(not isinstance(item, str) for item in required_toolsets + fallback_toolsets):
        return False
    active = set(active_toolsets or ())
    if required_toolsets and (active_toolsets is None or not set(required_toolsets).issubset(active)):
        return False
    if fallback_toolsets and active.intersection(fallback_toolsets):
        return False
    revision = content_revision(markdown)
    return any(grant.enabled and grant.skill_id == skill_id.strip() and grant.revision == revision for grant in grants)

