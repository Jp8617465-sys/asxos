"""Pins the owner-routing half of the autonomy protected-path contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
OWNER = "@Jp8617465-sys"

REQUIRED_PATTERNS = {
    "/AGENTS.md",
    "/CLAUDE.md",
    "/docs/product/**",
    "/.github/**",
    "/.claude/**",
    "/asxos/brief/**",
    "/asxos/domain/decision_engine/**",
    "/asxos/jobs/utils/fallback_email.py",
    "/asxos/insights/**",
    "/asxos/capital/**",
    "/migrations/**",
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
