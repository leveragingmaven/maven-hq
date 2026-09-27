"""Private, read-only Maven platform skill bridge."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from src.constants import PLATFORM_SKILLS_FILE
from services.memory.platform_skill_authorization import (
    PlatformSkillAllowlistError,
    authorize_platform_skill,
    content_revision,
    load_platform_allowlist,
)
from services.memory.platform_skill_service_auth import (
    SERVICE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    verify_request,
)
from services.memory.skills import SkillsManager

MAX_RESULTS = 50
MAX_QUERY_LENGTH = 256
MAX_MARKDOWN_LENGTH = 12_000


def setup_platform_skill_service_routes(skills_manager: SkillsManager) -> APIRouter:
    router = APIRouter(prefix="/internal/maven/platform-skills", tags=["internal-platform-skills"])

    def authenticate(request: Request) -> None:
        if not verify_request(
            service=request.headers.get(SERVICE_HEADER),
            timestamp=request.headers.get(TIMESTAMP_HEADER),
            signature=request.headers.get(SIGNATURE_HEADER),
            method=request.method,
            path=request.url.path,
            query=request.url.query,
        ):
            raise HTTPException(status_code=401, detail="invalid service authentication")

    def grants():
        try:
            return load_platform_allowlist(PLATFORM_SKILLS_FILE)
        except PlatformSkillAllowlistError as exc:
            raise HTTPException(status_code=503, detail="platform skill authorization is unavailable") from exc

    def context(platform: Optional[str], toolsets: Optional[str]) -> tuple[Optional[str], Optional[list[str]]]:
        if platform is not None and (not platform.strip() or len(platform) > 64):
            raise HTTPException(status_code=400, detail="platform is invalid")
        if toolsets is None:
            active = None
        else:
            values = [item.strip() for item in toolsets.split(",") if item.strip()]
            if len(values) > 20 or any(len(item) > 64 for item in values):
                raise HTTPException(status_code=400, detail="toolsets are invalid")
            active = values
        return (platform.strip() if platform else None), active

    def authorized(skill: dict, *, platform: Optional[str], active_toolsets: Optional[list[str]], allowlist) -> tuple[dict, str] | None:
        owner = skill.get("owner")
        markdown = skills_manager.read_skill_md(skill.get("name", ""), owner=owner)
        if markdown is None or len(markdown.encode("utf-8")) > MAX_MARKDOWN_LENGTH:
            return None
        if not authorize_platform_skill(skill, markdown, allowlist, platform=platform, active_toolsets=active_toolsets):
            return None
        return skill, markdown

    @router.get("")
    async def list_platform_skills(
        request: Request,
        q: Optional[str] = Query(default=None, max_length=MAX_QUERY_LENGTH),
        limit: int = Query(default=20, ge=1, le=MAX_RESULTS),
        platform: Optional[str] = Query(default=None, max_length=64),
        toolsets: Optional[str] = Query(default=None, max_length=512),
    ):
        authenticate(request)
        if q is not None and len(q.strip()) > MAX_QUERY_LENGTH:
            raise HTTPException(status_code=400, detail="query is too long")
        platform, active_toolsets = context(platform, toolsets)
        allowlist = grants()
        needle = (q or "").strip().lower()
        results = []
        for skill in skills_manager.load_all():
            if needle:
                haystack = " ".join(str(skill.get(key) or "") for key in ("id", "name", "description", "category", "when_to_use"))
                haystack += " " + " ".join(str(item) for item in skill.get("tags") or [])
                if needle not in haystack.lower():
                    continue
            match = authorized(skill, platform=platform, active_toolsets=active_toolsets, allowlist=allowlist)
            if match is None:
                continue
            selected, markdown = match
            results.append({
                "id": selected["id"],
                "name": selected["name"],
                "description": str(selected.get("description") or "")[:1024],
                "version": selected.get("version"),
                "revision": content_revision(markdown),
                "platforms": selected.get("platforms") or [],
                "requires_toolsets": selected.get("requires_toolsets") or [],
            })
            if len(results) >= limit:
                break
        return {"skills": results, "count": len(results)}

    @router.get("/{skill_id}")
    async def retrieve_platform_skill(
        skill_id: str,
        request: Request,
        revision: str = Query(..., min_length=71, max_length=71),
        platform: Optional[str] = Query(default=None, max_length=64),
        toolsets: Optional[str] = Query(default=None, max_length=512),
    ):
        authenticate(request)
        if not skill_id.strip() or len(skill_id) > 128:
            raise HTTPException(status_code=400, detail="skill id is invalid")
        platform, active_toolsets = context(platform, toolsets)
        allowlist = grants()
        skill = next((item for item in skills_manager.load_all() if item.get("id") == skill_id or item.get("name") == skill_id), None)
        if skill is None:
            raise HTTPException(status_code=404, detail="platform skill not found")
        match = authorized(skill, platform=platform, active_toolsets=active_toolsets, allowlist=allowlist)
        if match is None:
            raise HTTPException(status_code=404, detail="platform skill not found")
        selected, markdown = match
        actual_revision = content_revision(markdown)
        if revision != actual_revision:
            raise HTTPException(status_code=409, detail="skill revision is not authorized")
        return {
            "id": selected["id"],
            "name": selected["name"],
            "description": str(selected.get("description") or "")[:1024],
            "version": selected.get("version"),
            "revision": actual_revision,
            "platforms": selected.get("platforms") or [],
            "requires_toolsets": selected.get("requires_toolsets") or [],
            "markdown": markdown,
        }

    return router

