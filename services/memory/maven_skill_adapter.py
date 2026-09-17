"""Maven Skills → HQ Adapter.

Transforms Maven-format SKILL.md files into HQ-compatible format during import.
This adapter is structural only — it maps section headings and generates HQ
frontmatter, but preserves all Maven content verbatim.

Maven format signature:
    # Title
    ## Purpose
    ## Use When
    ## Process
    ## Quality Checklist
    ## Boundaries
    ...other Maven sections...

HQ format:
    ---
    name: ...
    description: ...
    ---
    ## When to Use
    ## Procedure
    ## Pitfalls
    ## Verification
    ...body_extra (preserved Maven sections)...

Usage:
    if is_maven_format(text):
        hq_text = adapt_maven_to_hq(text, source_url)
    else:
        hq_text = text  # Pass through unchanged
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Maven format detection
# ---------------------------------------------------------------------------

_MAVEN_SECTION_MARKERS = frozenset({
    "purpose",
    "use when",
    "process",
    "quality checklist",
    "boundaries",
    "inputs",
    "business context",
    "references",
    "tools",
    "output",
    "permissions",
    "attribution",
})


def is_maven_format(text: str) -> bool:
    """Detect Maven Skills format by structural markers.
    
    Conservative detection: requires H1 title AND at least 3 Maven-specific
    sections. This avoids false positives on arbitrary markdown.
    
    Returns True only for strong Maven signatures.
    """
    if not text or not text.strip():
        return False
    
    # HQ format has YAML frontmatter — explicitly NOT Maven
    if text.strip().startswith("---"):
        return False
    
    lines = text.splitlines()[:15]  # Check first 15 lines for signature
    
    # Require H1 title (e.g., "# Griller")
    has_h1_title = any(
        line.startswith("# ") and len(line) > 2 
        for line in lines
    )
    
    if not has_h1_title:
        return False
    
    # Count Maven-specific section markers
    maven_sections_found = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            section_name = stripped[3:].strip().lower()
            if section_name in _MAVEN_SECTION_MARKERS:
                maven_sections_found += 1
    
    # Conservative: require H1 + at least 3 Maven sections
    # Typical Maven skills have: Purpose, Use When, Process, Quality Checklist, Boundaries
    return maven_sections_found >= 3


# ---------------------------------------------------------------------------
# Maven section parser
# ---------------------------------------------------------------------------

_MAVEN_SECTION_MAP = {
    "purpose": "purpose",
    "use when": "use_when",
    "inputs": "inputs",
    "business context": "business_context",
    "references": "references",
    "tools": "tools",
    "process": "process",
    "output": "output",
    "permissions": "permissions",
    "quality checklist": "quality_checklist",
    "boundaries": "boundaries",
    "attribution": "attribution",
}


def parse_maven_sections(text: str) -> Dict[str, str]:
    """Parse Maven SKILL.md into section dictionary.
    
    Extracts H1 title and all ## sections. Content is preserved verbatim
    — no normalization, no reformatting.
    
    Returns dict with keys:
        title: str (from H1)
        purpose: str
        use_when: str
        process: str
        quality_checklist: str
        boundaries: str
        ...plus any other Maven sections found...
    """
    sections: Dict[str, str] = {}
    current_section: Optional[str] = None
    current_content: List[str] = []
    
    lines = text.splitlines()
    
    for line in lines:
        # H1 title (e.g., "# Griller")
        if line.startswith("# ") and current_section is None:
            sections["title"] = line[2:].strip()
            continue
        
        # H2 section start (e.g., "## Purpose")
        if line.startswith("## "):
            # Save previous section
            if current_section is not None:
                sections[current_section] = "\n".join(current_content).strip()
            
            section_name = line[3:].strip().lower()
            current_section = _MAVEN_SECTION_MAP.get(section_name, section_name)
            current_content = []
            continue
        
        # Accumulate section content
        if current_section is not None:
            current_content.append(line)
    
    # Save final section
    if current_section is not None:
        sections[current_section] = "\n".join(current_content).strip()
    
    return sections


# ---------------------------------------------------------------------------
# HQ frontmatter generator
# ---------------------------------------------------------------------------

def _slugify(text: str, fallback: str = "skill") -> str:
    """Convert text to kebab-case slug."""
    import re as _re
    s = str(text or "").strip().lower()
    s = _re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return (s or fallback)[:60]


def _now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to max_len characters."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    # Truncate at word boundary if possible
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len - 20:
        return truncated[:last_space] + "..."
    return truncated + "..."


def build_hq_frontmatter(
    maven_sections: Dict[str, str],
    source_url: str = "",
    category_override: Optional[str] = None,
) -> Dict[str, object]:
    """Generate HQ-required frontmatter from Maven sections.
    
    Deterministic defaults:
        name: slugified from H1 title
        description: truncated from Purpose
        version: 1.0.0
        category: from URL path or override or "imported"
        tags: []
        requires_toolsets: []
        status: published
        confidence: 0.9
        source: imported
        created: current UTC timestamp
    """
    # Extract name from title
    title = maven_sections.get("title", "")
    name = _slugify(title, fallback="imported-skill")
    
    # Extract description from Purpose
    purpose = maven_sections.get("purpose", "")
    description = _truncate(purpose, max_len=200)
    
    # Infer category from source URL path
    # e.g., ".../skills/business/griller" → "business"
    category = category_override or "imported"
    if source_url and "/skills/" in source_url:
        parts = source_url.split("/skills/")
        if len(parts) > 1:
            path_parts = parts[1].rstrip("/").split("/")
            if len(path_parts) >= 2:
                category = path_parts[0]  # e.g., "business"
    
    return {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "category": category,
        "tags": [],
        "requires_toolsets": [],
        "status": "published",
        "confidence": 0.9,
        "source": "imported",
        "created": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Section mapping (structural only, content preserved verbatim)
# ---------------------------------------------------------------------------

_MAVEN_TO_HQ_SECTION = {
    "use_when": "when_to_use",
    "process": "procedure",
    "boundaries": "pitfalls",
    "quality_checklist": "verification",
}


def map_maven_to_hq_sections(
    maven_sections: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Map Maven sections to HQ equivalents.
    
    Returns (hq_sections, preserved_sections):
        hq_sections: {"when_to_use", "procedure", "pitfalls", "verification"}
        preserved_sections: Maven-only sections to keep in body_extra
    
    CRITICAL: Content is preserved VERBATIM. No reformatting, no normalization.
    Only the section HEADING changes.
    """
    hq_sections: Dict[str, str] = {
        "when_to_use": "",
        "procedure": "",
        "pitfalls": "",
        "verification": "",
    }
    
    preserved: Dict[str, str] = {}
    
    for maven_key, content in maven_sections.items():
        if maven_key in _MAVEN_TO_HQ_SECTION:
            hq_key = _MAVEN_TO_HQ_SECTION[maven_key]
            hq_sections[hq_key] = content  # VERBATIM preservation
        elif maven_key not in ("title", "purpose"):
            # Preserve Maven-only sections
            preserved[maven_key] = content
    
    return hq_sections, preserved


# ---------------------------------------------------------------------------
# HQ format assembler
# ---------------------------------------------------------------------------

def _emit_frontmatter(fm: Dict[str, object]) -> str:
    """Emit YAML frontmatter block."""
    lines = []
    for key, value in fm.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            if value:
                lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _emit_hq_body(
    hq_sections: Dict[str, str],
    preserved_sections: Dict[str, str],
    source_url: str = "",
) -> str:
    """Assemble HQ body with preserved Maven sections.
    
    HQ sections:
        ## When to Use
        ## Procedure
        ## Pitfalls
        ## Verification
    
    Preserved sections appended as-is with original Maven headings.
    """
    _HQ_HEADING_MAP = {
        "when_to_use": "When to Use",
        "procedure": "Procedure",
        "pitfalls": "Pitfalls",
        "verification": "Verification",
    }
    
    parts: List[str] = []
    
    # Emit HQ-required sections (only if non-empty)
    for hq_key, heading in _HQ_HEADING_MAP.items():
        content = hq_sections.get(hq_key, "").strip()
        if content:
            parts.append(f"## {heading}\n\n{content}")
    
    # Emit preserved Maven sections with original headings
    _MAVEN_HEADING_MAP = {
        "inputs": "Inputs",
        "business_context": "Business Context",
        "references": "References",
        "tools": "Tools",
        "output": "Output",
        "permissions": "Permissions",
        "attribution": "Attribution",
    }
    
    for maven_key, content in preserved_sections.items():
        if content.strip():
            heading = _MAVEN_HEADING_MAP.get(maven_key, maven_key.replace("_", " ").title())
            parts.append(f"## {heading}\n\n{content}")
    
    # Append source attribution
    if source_url:
        parts.append(f"## Source\n\nImported from {source_url}")
    
    return "\n\n".join(parts) + "\n" if parts else ""


# ---------------------------------------------------------------------------
# Main adapter entry point
# ---------------------------------------------------------------------------

class MavenAdapterError(Exception):
    """Raised when Maven adaptation fails."""
    pass


def adapt_maven_to_hq(
    maven_text: str,
    source_url: str = "",
    category_override: Optional[str] = None,
) -> str:
    """Transform Maven-format SKILL.md to HQ-compatible format.
    
    This is a STRUCTURAL conversion only:
    - Maps section headings (Process → Procedure, etc.)
    - Generates HQ frontmatter
    - Preserves ALL content verbatim
    - Preserves ALL Maven-only sections in body_extra
    
    Args:
        maven_text: Raw Maven-format SKILL.md content
        source_url: GitHub URL for attribution and category inference
        category_override: Optional category (default: inferred from URL)
    
    Returns:
        HQ-compatible SKILL.md with YAML frontmatter
    
    Raises:
        MavenAdapterError: If required Maven sections are missing
    """
    if not maven_text or not maven_text.strip():
        raise MavenAdapterError("Empty Maven skill content")
    
    # Parse Maven sections
    maven_sections = parse_maven_sections(maven_text)
    
    # Validate required sections
    required = ["title", "purpose"]
    missing = [r for r in required if not maven_sections.get(r)]
    if missing:
        raise MavenAdapterError(
            f"Maven skill missing required sections: {', '.join(missing)}"
        )
    
    # Build HQ frontmatter
    frontmatter = build_hq_frontmatter(
        maven_sections,
        source_url=source_url,
        category_override=category_override,
    )
    
    # Map sections (verbatim content preservation)
    hq_sections, preserved = map_maven_to_hq_sections(maven_sections)
    
    # Assemble HQ format
    fm_text = _emit_frontmatter(frontmatter)
    body_text = _emit_hq_body(hq_sections, preserved, source_url)
    
    return f"---\n{fm_text}\n---\n\n{body_text}"


def adapt_if_maven(
    text: str,
    source_url: str = "",
    category_override: Optional[str] = None,
) -> Tuple[str, bool]:
    """Adapt text if it's Maven format, otherwise pass through.
    
    Returns (result_text, was_adapted):
        result_text: HQ-compatible SKILL.md
        was_adapted: True if Maven format was detected and adapted
    
    This is the safe entry point for the import pipeline.
    """
    if is_maven_format(text):
        try:
            adapted = adapt_maven_to_hq(text, source_url, category_override)
            return adapted, True
        except MavenAdapterError as e:
            logger.warning(f"Maven adapter failed: {e}")
            raise
    return text, False
