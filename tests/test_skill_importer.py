"""Skill URL importer — GitHub path parsing and authentication."""
import pytest

from services.memory.skill_importer import (
    ResolvedSource,
    SkillImportError,
    _assert_github_url,
    _fetch_bytes,
    _github_headers,
    _list_github_dir,
    _GITHUB_TOKEN,
    parse_skill_source,
)


def test_parse_github_blob_skill_md():
    src = parse_skill_source(
        "https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md"
    )
    assert src.owner == "anthropics"
    assert src.repo == "skills"
    assert src.ref == "main"
    assert src.path.endswith("skills/pdf/SKILL.md")


def test_parse_github_tree_directory():
    src = parse_skill_source(
        "https://github.com/example/my-skills/tree/develop/caveman-skill"
    )
    assert src.owner == "example"
    assert src.repo == "my-skills"
    assert src.ref == "develop"
    assert src.path == "caveman-skill"


def test_parse_raw_github():
    src = parse_skill_source(
        "https://raw.githubusercontent.com/o/r/main/path/SKILL.md"
    )
    assert src.owner == "o"
    assert src.repo == "r"
    assert src.ref == "main"
    assert src.path == "path/SKILL.md"


def test_rejects_non_github():
    with pytest.raises(SkillImportError):
        parse_skill_source("https://example.com/skill.md")


def test_fetch_bytes_rejects_cross_host_redirect(monkeypatch):
    class _Resp:
        url = "https://evil.example/secret"
        status_code = 200
        content = b"x"

        def raise_for_status(self):
            return None

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            return _Resp()

    monkeypatch.setattr("services.memory.skill_importer.httpx.Client", _Client)
    monkeypatch.setattr(
        "services.memory.skill_importer.check_outbound_url",
        lambda url: (True, ""),
    )
    with pytest.raises(SkillImportError, match="redirect target"):
        _fetch_bytes("https://raw.githubusercontent.com/o/r/main/SKILL.md")


def test_assert_github_url_allows_api_host():
    _assert_github_url(
        "https://api.github.com/repos/o/r/contents?ref=main",
        context="redirect target",
    )


def test_list_github_dir_accepts_api_github_response(monkeypatch):
    monkeypatch.setattr(
        "services.memory.skill_importer._fetch_text",
        lambda url: "# skill\n",
    )
    monkeypatch.setattr(
        "services.memory.skill_importer.check_outbound_url",
        lambda url: (True, ""),
    )

    class _Resp:
        url = "https://api.github.com/repos/o/r/contents?ref=main"
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "name": "SKILL.md",
                "type": "file",
                "download_url": "https://raw.githubusercontent.com/o/r/main/SKILL.md",
            }]

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            return _Resp()

    monkeypatch.setattr("services.memory.skill_importer.httpx.Client", _Client)

    out = {}
    src = ResolvedSource(owner="o", repo="r", ref="main", path="")
    _list_github_dir(src, "", out)
    assert "SKILL.md" in out


def _mock_httpx_client(monkeypatch, response):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            return response

    monkeypatch.setattr("services.memory.skill_importer.httpx.Client", _Client)
    monkeypatch.setattr(
        "services.memory.skill_importer.check_outbound_url",
        lambda url: (True, ""),
    )


def test_list_github_dir_surfaces_rate_limit(monkeypatch):
    class _Resp:
        url = "https://api.github.com/repos/o/r/contents?ref=main"
        status_code = 403

        def json(self):
            return {"message": "API rate limit exceeded for 203.0.113.1"}

    _mock_httpx_client(monkeypatch, _Resp())
    src = ResolvedSource(owner="o", repo="r", ref="main", path="")
    with pytest.raises(SkillImportError, match="rate limit"):
        _list_github_dir(src, "", {})


def test_fetch_bytes_surfaces_github_error_detail(monkeypatch):
    class _Resp:
        url = "https://raw.githubusercontent.com/o/r/main/SKILL.md"
        status_code = 403
        content = b""

        def json(self):
            return {"message": "Forbidden"}

    _mock_httpx_client(monkeypatch, _Resp())
    with pytest.raises(SkillImportError, match="GitHub request failed \\(403\\): Forbidden"):
        _fetch_bytes("https://raw.githubusercontent.com/o/r/main/SKILL.md")


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

def test_github_headers_no_token():
    """When no GITHUB_TOKEN is set, headers should only include Accept."""
    import os
    # Ensure token is not set
    original = os.environ.pop("GITHUB_TOKEN", None)
    try:
        # Reload module to pick up env change
        import importlib
        import services.memory.skill_importer as importer
        importer._GITHUB_TOKEN = None
        headers = importer._github_headers()
        assert headers == {"Accept": "application/vnd.github+json"}
        assert "Authorization" not in headers
    finally:
        if original:
            os.environ["GITHUB_TOKEN"] = original


def test_github_headers_with_token(monkeypatch):
    """When GITHUB_TOKEN is set, Authorization header should be included."""
    import os
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_12345")
    
    # Reload module to pick up env change
    import importlib
    import services.memory.skill_importer as importer
    importlib.reload(importer)
    
    headers = importer._github_headers()
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["Authorization"] == "Bearer test_token_12345"


def test_authenticated_request_includes_auth_header(monkeypatch):
    """Authenticated GitHub requests should include Authorization header."""
    captured_headers = {}
    
    class _Resp:
        url = "https://api.github.com/repos/o/r/contents?ref=main"
        status_code = 200
        
        def json(self):
            return []
    
    class _Client:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, url, headers=None):
            captured_headers['headers'] = dict(headers) if headers else {}
            return _Resp()
    
    monkeypatch.setattr("services.memory.skill_importer.httpx.Client", _Client)
    monkeypatch.setattr("services.memory.skill_importer.check_outbound_url", lambda url: (True, ""))
    monkeypatch.setenv("GITHUB_TOKEN", "secret_token_xyz")
    
    # Reload to pick up token
    import importlib
    import services.memory.skill_importer as importer
    importlib.reload(importer)
    
    src = ResolvedSource(owner="o", repo="r", ref="main", path="")
    try:
        importer._list_github_dir(src, "", {})
    except Exception:
        pass  # May fail for other reasons, we just want to check headers
    
    assert "Authorization" in captured_headers.get('headers', {})
    assert captured_headers['headers']["Authorization"] == "Bearer secret_token_xyz"


def test_token_not_in_error_output(monkeypatch):
    """GitHub token should never appear in error messages."""
    class _Resp:
        url = "https://api.github.com/repos/o/r/contents"
        status_code = 403
        content = b""
        
        def json(self):
            return {"message": "Bad credentials"}
    
    class _Client:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, url, headers=None):
            return _Resp()
    
    monkeypatch.setattr("services.memory.skill_importer.httpx.Client", _Client)
    monkeypatch.setattr("services.memory.skill_importer.check_outbound_url", lambda url: (True, ""))
    monkeypatch.setenv("GITHUB_TOKEN", "super_secret_token_12345")
    
    # Reload to pick up token
    import importlib
    import services.memory.skill_importer as importer
    importlib.reload(importer)
    
    src = ResolvedSource(owner="o", repo="r", ref="main", path="")
    with pytest.raises(SkillImportError) as exc_info:
        importer._list_github_dir(src, "", {})
    
    error_msg = str(exc_info.value)
    assert "super_secret_token_12345" not in error_msg
    assert "token" not in error_msg.lower() or "GITHUB_TOKEN" in error_msg  # Only mention env var name


def test_maven_adapter_path_executes_after_auth(monkeypatch):
    """Verify Maven adapter still executes after authenticated content retrieval."""
    # This test ensures the authentication layer doesn't break the Maven adapter flow
    
    maven_content = """# Griller

## Purpose

Test purpose.

## Use When

- Test case

## Process

### 1. Step one

## Quality Checklist

- [ ] Test passes

## Boundaries

Test boundaries.
"""
    
    # Mock the fetch to return Maven-formatted content
    monkeypatch.setattr(
        "services.memory.skill_importer._fetch_text",
        lambda url: maven_content
    )
    monkeypatch.setattr(
        "services.memory.skill_importer._list_github_dir",
        lambda src, rel, out, depth=0: out.update({"SKILL.md": maven_content})
    )
    monkeypatch.setattr(
        "services.memory.skill_importer.check_outbound_url",
        lambda url: (True, "")
    )
    
    from services.memory.skill_importer import fetch_skill_bundle
    
    files, src = fetch_skill_bundle(
        "https://github.com/leveragingmaven/maven-skills/tree/main/skills/business/griller"
    )
    
    assert "SKILL.md" in files
    assert "# Griller" in files["SKILL.md"]
    assert "## Purpose" in files["SKILL.md"]
