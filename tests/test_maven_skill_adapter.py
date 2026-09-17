"""Tests for Maven Skills → HQ Adapter.

These tests verify:
1. Maven Griller is detected as Maven format
2. HQ-native skills pass through unchanged
3. Section mapping preserves content verbatim
4. Maven-only sections are preserved in body_extra
5. Round-trip through Skill.from_markdown()/to_markdown() works
6. Malformed input fails gracefully
"""
import pytest
from services.memory.maven_skill_adapter import (
    is_maven_format,
    parse_maven_sections,
    adapt_maven_to_hq,
    adapt_if_maven,
    MavenAdapterError,
)
from services.memory.skill_format import Skill

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def maven_griller() -> str:
    """Real Maven Griller SKILL.md content."""
    return """# Griller

## Purpose

Turn vague ideas, plans, offers, strategies, or creative concepts into clear actionable briefs through adaptive interviewing. Use when the user needs to clarify thinking before execution, stress-test a plan, or identify gaps in their reasoning.

## Use When

- User has a vague idea and needs to figure out what they actually want (Discovery mode)
- User believes their plan is clear but needs pressure-testing (Pressure Test mode)
- User explicitly says "grill me", "stress test this", "poke holes in this", or similar

## Inputs

- The idea, plan, strategy, offer, or concept to examine (can be vague or detailed)
- User's current understanding of their goal (may be unclear)

## Business Context

- business.goals
- offer.current
- audience.primary
- brand.voice

## References

- ecc/decision-synthesis (for decision tracking and synthesis)

## Tools

- None (reasoning and interviewing only)

## Process

### 1. **Determine mode and scope** — Ask: "What are we working on?"

### 2. **Establish the domain** — Confirm the domain and stay in that lane.

### 3. **Ask one question at a time** — Never ask multiple questions in one message.

## Output

- Structured brief containing summary, decisions, constraints, next action

## Permissions

- None (interviewing and reasoning only)

## Quality Checklist

- [ ] Asked one question at a time (no multi-question barrages)
- [ ] Each question responded to what user actually said
- [ ] Stayed in domain unless user explicitly shifted

## Boundaries

**This skill does:**
- Ask clarifying questions one at a time
- Challenge assumptions and surface risks

**This skill does NOT:**
- Execute the plan being discussed
- Write deliverables (copy, code, designs, strategies)

## Attribution

This skill adapts the structured interview methodology from `stevegsax/grill-me` (MIT License).
"""


@pytest.fixture
def hq_native_skill() -> str:
    """HQ-native format skill (should pass through unchanged)."""
    return """---
name: test-skill
description: A test skill.
version: 1.0.0
category: general
tags: [test]
requires_toolsets: []
status: published
confidence: 0.8
source: learned
---

## When to Use

Use this skill for testing purposes.

## Procedure

1. First step
2. Second step

## Pitfalls

- Common mistake to avoid

## Verification

- [ ] Test passes
"""


# ---------------------------------------------------------------------------
# Format detection tests
# ---------------------------------------------------------------------------

def test_detects_maven_griller(maven_griller: str):
    """Maven Griller should be detected as Maven format."""
    assert is_maven_format(maven_griller) is True


def test_detects_hq_native_unchanged(hq_native_skill: str):
    """HQ-native skill with frontmatter should NOT be detected as Maven."""
    assert is_maven_format(hq_native_skill) is False


def test_empty_text_not_maven():
    """Empty text should not be detected as Maven."""
    assert is_maven_format("") is False
    assert is_maven_format("   ") is False


def test_missing_h1_not_maven():
    """Text without H1 title should not be detected as Maven."""
    text = """## Purpose
Some content

## Process
Some steps
"""
    assert is_maven_format(text) is False


def test_few_maven_sections_not_maven():
    """Text with only 1-2 Maven sections should not be detected."""
    text = """# Title

## Purpose
Some content

## Random Section
Other content
"""
    assert is_maven_format(text) is False


# ---------------------------------------------------------------------------
# Section parsing tests
# ---------------------------------------------------------------------------

def test_parse_maven_griller_sections(maven_griller: str):
    """Parse Maven Griller into correct sections."""
    sections = parse_maven_sections(maven_griller)
    
    assert sections["title"] == "Griller"
    assert "Turn vague ideas" in sections["purpose"]
    assert "User has a vague idea" in sections["use_when"]
    assert "### 1. **Determine mode" in sections["process"]
    assert "Asked one question" in sections["quality_checklist"]
    assert "This skill does:" in sections["boundaries"]
    assert "business.goals" in sections["business_context"]
    assert "ecc/decision-synthesis" in sections["references"]
    assert "stevegsax/grill-me" in sections["attribution"]


# ---------------------------------------------------------------------------
# Adaptation tests
# ---------------------------------------------------------------------------

def test_adapt_griller_produces_valid_hq(maven_griller: str):
    """Maven Griller should adapt to valid HQ format."""
    hq_text = adapt_maven_to_hq(maven_griller, "https://github.com/leveragingmaven/maven-skills/tree/main/skills/business/griller")
    
    # Verify frontmatter exists
    assert hq_text.startswith("---\n")
    assert "name: griller" in hq_text
    assert "description:" in hq_text
    assert "category: business" in hq_text
    assert "status: published" in hq_text
    assert "confidence: 0.9" in hq_text
    assert "source: imported" in hq_text
    
    # Verify HQ sections exist
    assert "## When to Use" in hq_text
    assert "## Procedure" in hq_text
    assert "## Pitfalls" in hq_text
    assert "## Verification" in hq_text
    
    # Verify content is preserved VERBATIM
    assert "User has a vague idea" in hq_text  # From Use When
    assert "### 1. **Determine mode" in hq_text  # From Process (verbatim!)
    assert "This skill does:" in hq_text  # From Boundaries
    assert "[ ] Asked one question" in hq_text  # From Quality Checklist


def test_adapt_preserves_maven_sections(maven_griller: str):
    """Maven-only sections should be preserved in output."""
    hq_text = adapt_maven_to_hq(maven_griller, "https://...")
    
    # These are Maven-only sections that should be preserved
    assert "## Inputs" in hq_text
    assert "## Business Context" in hq_text
    assert "## References" in hq_text
    assert "## Tools" in hq_text
    assert "## Output" in hq_text
    assert "## Permissions" in hq_text
    assert "## Attribution" in hq_text
    
    # Verify content is preserved
    assert "business.goals" in hq_text
    assert "ecc/decision-synthesis" in hq_text
    assert "stevegsax/grill-me" in hq_text


def test_adapt_preserves_process_verbatim(maven_griller: str):
    """Process section content must be preserved EXACTLY."""
    hq_text = adapt_maven_to_hq(maven_griller, "https://...")
    
    # Extract Procedure section
    proc_start = hq_text.find("## Procedure\n")
    assert proc_start >= 0
    
    # The original Process content should be there verbatim
    assert "### 1. **Determine mode and scope**" in hq_text
    assert "### 2. **Establish the domain**" in hq_text
    assert "### 3. **Ask one question at a time**" in hq_text


def test_adapt_if_maven_returns_flag(maven_griller: str):
    """adapt_if_maven should return (text, was_adapted) tuple."""
    result, was_adapted = adapt_if_maven(maven_griller, "https://...")
    
    assert was_adapted is True
    assert "name: griller" in result


def test_adapt_if_maven_hq_passthrough(hq_native_skill: str):
    """HQ-native skills should pass through unchanged."""
    result, was_adapted = adapt_if_maven(hq_native_skill, "")
    
    assert was_adapted is False
    assert result == hq_native_skill


# ---------------------------------------------------------------------------
# Skill parsing tests
# ---------------------------------------------------------------------------

def test_converted_griller_parses_with_skill_from_markdown(maven_griller: str):
    """Converted Griller should parse successfully with Skill.from_markdown()."""
    hq_text = adapt_maven_to_hq(maven_griller, "https://...")
    
    # This should not raise
    skill = Skill.from_markdown(hq_text)
    
    assert skill.name == "griller"
    assert "Turn vague ideas" in skill.description
    assert skill.category == "business"
    assert skill.status == "published"
    assert skill.source == "imported"
    assert len(skill.procedure) > 0
    assert len(skill.verification) > 0


def test_roundtrip_preserves_maven_sections(maven_griller: str):
    """Skill.to_markdown() should preserve Maven-only sections."""
    hq_text = adapt_maven_to_hq(maven_griller, "https://...")
    skill = Skill.from_markdown(hq_text)
    output = skill.to_markdown()
    
    # Maven-only sections should survive round-trip
    assert "## Inputs" in output
    assert "## Business Context" in output
    assert "## References" in output
    assert "## Attribution" in output
    assert "stevegsax/grill-me" in output


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

def test_empty_input_raises_error():
    """Empty input should raise MavenAdapterError."""
    with pytest.raises(MavenAdapterError, match="Empty"):
        adapt_maven_to_hq("", "https://...")


def test_missing_title_raises_error():
    """Maven skill without title should raise."""
    text = """## Purpose
Some content

## Process
Steps

## Use When
When
"""
    with pytest.raises(MavenAdapterError, match="missing required"):
        adapt_maven_to_hq(text, "https://...")


def test_missing_purpose_raises_error():
    """Maven skill without purpose should raise."""
    text = """# Title

## Process
Steps

## Use When
When
"""
    with pytest.raises(MavenAdapterError, match="missing required"):
        adapt_maven_to_hq(text, "https://...")


def test_adapt_if_maven_propagates_error():
    """adapt_if_maven should propagate MavenAdapterError."""
    with pytest.raises(MavenAdapterError):
        adapt_if_maven("", "https://...")


# ---------------------------------------------------------------------------
# Category inference tests
# ---------------------------------------------------------------------------

def test_category_inferred_from_url(maven_griller: str):
    """Category should be inferred from URL path."""
    hq_text = adapt_maven_to_hq(
        maven_griller,
        "https://github.com/leveragingmaven/maven-skills/tree/main/skills/business/griller"
    )
    assert "category: business" in hq_text


def test_category_inferred_from_video_url(maven_griller: str):
    """Category inference should work for other categories."""
    hq_text = adapt_maven_to_hq(
        maven_griller,
        "https://github.com/leveragingmaven/maven-skills/tree/main/skills/video/editor"
    )
    assert "category: video" in hq_text


def test_category_override_works(maven_griller: str):
    """Category override should take precedence."""
    hq_text = adapt_maven_to_hq(
        maven_griller,
        "https://...",
        category_override="custom-category"
    )
    assert "category: custom-category" in hq_text


def test_default_category_when_no_url(maven_griller: str):
    """Default category should be 'imported' when no URL provided."""
    hq_text = adapt_maven_to_hq(maven_griller, "")
    assert "category: imported" in hq_text
