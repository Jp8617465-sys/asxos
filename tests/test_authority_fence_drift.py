"""The authority fence is defined twice, in two grammars. They must agree.

`.claude/settings.json`'s `permissions.deny` array is the primary, mechanical
boundary for the direct-tool and recognised-Bash-command paths.
`.claude/hooks/authority-guard.sh`'s `AUTHORITY_FRAGMENTS` array covers the
residual — interpreter-mediated writes and symlink aliases — and needs its own
copy of the same set.

They are held in different files, in different notations (`Edit(/a/**)` versus
the bare prefix `a/`), and until now the only thing asserting they stay in step
was a comment at `authority-guard.sh:44-50` saying so. A comment is not a check.
Either file could gain or lose a path and the other would not notice.

This is a plain drift test, not a guard test: it reads both files and compares
sets. It passes against the fence as it stands today; its value is entirely in
the day someone edits one file and not the other.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_HOOK = ROOT / ".claude" / "hooks" / "authority-guard.sh"
SETTINGS = ROOT / ".claude" / "settings.json"


def _fragments_from_hook() -> set[str]:
    source = AUTHORITY_HOOK.read_text(encoding="utf-8")
    block = re.search(r"AUTHORITY_FRAGMENTS=\((.*?)\n\)", source, re.DOTALL)
    assert block, "AUTHORITY_FRAGMENTS array not found in authority-guard.sh"
    return set(re.findall(r'"([^"]+)"', block.group(1)))


def _fragments_from_settings() -> set[str]:
    deny = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]["deny"]
    out: set[str] = set()
    for entry in deny:
        match = re.fullmatch(r"(?:Edit|Read)\((.+)\)", entry)
        if not match:
            continue  # mcp__* tool denials are not path rules
        path = match.group(1).lstrip("/")
        # `a/**` (glob) and `a/` (hook prefix) express the same directory rule.
        out.add(path[:-2] if path.endswith("**") else path)
    return out


def test_settings_deny_and_hook_fragments_describe_the_same_set() -> None:
    hook, settings = _fragments_from_hook(), _fragments_from_settings()
    assert hook == settings, (
        "authority fence drift between .claude/settings.json and "
        ".claude/hooks/authority-guard.sh\n"
        f"  only in hook:     {sorted(hook - settings)}\n"
        f"  only in settings: {sorted(settings - hook)}"
    )


def test_both_grammars_are_non_empty_and_parse() -> None:
    """A regex that silently stops matching would make the test above vacuous —
    two empty sets are equal."""
    assert len(_fragments_from_hook()) > 10
    assert len(_fragments_from_settings()) > 10


def test_github_is_fenced_in_both_grammars() -> None:
    """No test asserted this before, in any file, so nothing would have caught
    `.github/` being dropped from either list."""
    assert ".github/" in _fragments_from_hook()
    assert ".github/" in _fragments_from_settings()


def test_env_and_claude_surfaces_are_fenced_in_both_grammars() -> None:
    for fragment in (
        ".env",
        "AGENTS.md",
        ".claude/agents/",
        ".claude/rules/",
        "docs/product/autonomy-policy.md",
        "render.yaml",
    ):
        assert fragment in _fragments_from_hook(), fragment
        assert fragment in _fragments_from_settings(), fragment


def test_cross_harness_authority_is_covered_by_unattended_guard_and_codeowners() -> None:
    unattended = (ROOT / ".claude" / "hooks" / "unattended-guard.sh").read_text()
    codeowners = (ROOT / ".github" / "CODEOWNERS").read_text()
    for path in ("AGENTS.md", "docs/product/autonomy-policy.md"):
        assert path in unattended, path
        assert f"/{path}" in codeowners, path
