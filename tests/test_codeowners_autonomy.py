"""Pins the owner-routing half of the autonomy protected-path contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
OWNER = "@Jp8617465-sys"

# Existing Amber rows in AGENTS.md §4, plus reserved Amber/Red rows that must
# be owned before the first file of that kind is written.
REQUIRED_PATTERNS = {
    "/AGENTS.md",
    "/CLAUDE.md",
    "/docs/product/**",
    "/.github/**",
    "/.claude/**",
    "/asxos/brief/**",
    "/asxos/brief/email.py",
    "/asxos/jobs/utils/fallback_email.py",
    "/asxos/comms/**",
    "/asxos/domain/decision_engine/**",
    "/asxos/insights/personal/**",
    "/asxos/insights/**",
    "/asxos/capital/**",
    "/migrations/**",
}

# Codex harness files stay outside the authority fence until James ADOPTs or
# REJECTs that capability. Do not add these patterns.
FENCE_EXCLUSIONS = {
    "/.codex/**",
    "/.codex/",
    ".codex/**",
}


def _rules() -> dict[str, tuple[str, ...]]:
    rules: dict[str, tuple[str, ...]] = {}
    for raw in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        rules[pattern] = tuple(owners)
    return rules


def test_autonomy_protected_paths_route_to_james() -> None:
    rules = _rules()
    assert REQUIRED_PATTERNS <= rules.keys()
    assert all(OWNER in rules[pattern] for pattern in REQUIRED_PATTERNS)


def test_codeowners_has_no_catch_all_that_masks_risk_routing() -> None:
    assert "*" not in _rules()


def test_codex_harness_is_outside_the_authority_fence() -> None:
    rules = _rules()
    overlapping = set(rules) & FENCE_EXCLUSIONS
    assert overlapping == set()
    for pattern in rules:
        assert ".codex" not in pattern.lower()


def test_agents_md_reserved_comms_path_is_owned() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "`asxos/comms/`" in agents
    assert "/asxos/comms/**" in _rules()
