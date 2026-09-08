"""Cross-file invariants for the staged autonomy policy.

These tests do not pretend the target policy is active. They keep the authority
documents coherent while the server-side activation items are built.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_activation_checklist_is_complete_and_contiguous() -> None:
    policy = _read("docs/product/autonomy-policy.md")
    numbers = [
        int(value)
        for value in re.findall(r"(?m)^(\d+)\. \*\*", policy)
    ]
    assert numbers == list(range(1, 19))
    assert "re-verifies items 1–17" in policy


def test_cross_harness_contract_is_on_the_authority_ladder() -> None:
    authority = _read("docs/product/arbi-authority.md")
    claude = _read("CLAUDE.md")
    assert "@AGENTS.md" in claude
    assert "`AGENTS.md` §8" in authority
    assert "`AGENTS.md`, `docs/product/autonomy-policy.md`" in authority


def test_migration_merge_and_application_are_separate() -> None:
    agents = _read("AGENTS.md")
    policy = _read("docs/product/autonomy-policy.md")
    permission_model = _read("docs/product/arbi-permission-model.md")
    assert "merging its definition is not\n  permission to apply it" in agents
    assert "Migration application." in agents
    assert "Migration authority split." in policy
    assert "Merging the definition is not\n  permission to apply it." in permission_model
    assert "Production migration application remains owner-only." in permission_model


def test_standing_requires_variable_and_ledger_attestation() -> None:
    agents = _read("AGENTS.md")
    policy = _read("docs/product/autonomy-policy.md")
    assert "control ledger attests this policy's exact digest" in agents
    assert "`AUTONOMY=STANDING` alone is not a key" in policy
    assert "`ARBI_UNATTENDED=1` remains\n    mechanically draft-only" in policy


def test_only_attested_state_workflows_may_write_autonomy() -> None:
    agents = _read("AGENTS.md")
    policy = _read("docs/product/autonomy-policy.md")
    assert (
        "attested `activation`, `breaker` and `restore` workflows may write it"
        in agents
    )
    assert "`risk-classify`, `activation`,\n`breaker`, `restore`" in agents
    assert "attested activation, breaker and restore workflows" in policy
    assert "Owner approves one activation dispatch" in policy


def test_check_and_branch_publishers_are_distinct() -> None:
    agents = _read("AGENTS.md")
    policy = _read("docs/product/autonomy-policy.md")
    assert "check-publisher job uses a reduced Verifier App token" in agents
    assert "check-publisher job uses a reduced Verifier App token" in policy
    assert "branch Publisher App has no checks permission" in policy
    assert "publisher App posts `risk-classify`" not in policy


def test_codeowners_routes_all_declared_sensitive_surfaces() -> None:
    codeowners = _read(".github/CODEOWNERS")
    expected = {
        "/AGENTS.md",
        "/CLAUDE.md",
        "/.github/**",
        "/.claude/**",
        "/.cursor/**",
        "/docs/product/**",
        "/asxos/brief/**",
        "/asxos/jobs/utils/fallback_email.py",
        "/asxos/domain/decision_engine/**",
        "/asxos/comms/**",
        "/asxos/insights/personal/**",
        "/asxos/capital/**",
        "/migrations/**",
    }
    declared = {
        line.split()[0]
        for line in codeowners.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert expected <= declared
