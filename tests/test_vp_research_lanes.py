"""Pins on the two value-to-price lanes: sealing and testing stay separate dispatches.

The pre-registration is only worth the name if the hypothesis is sealed BEFORE any
evidence exists. Two guards already encode that inside the code: the CLI's
``vp-register`` refuses outright once a run exists for the hypothesis, and
``jobs/run_vp_test.py`` hard-fails unless the hypothesis row is already there.

These tests pin the third, infrastructure-level guard — that the two acts are
reachable only as two separate dispatches. ``vp-research.yml`` promises in its own
header that it cannot register its own pre-registration; an input on that workflow
which sealed the hypothesis would quietly hand it exactly the capability the header
disclaims, and every test above it would still pass.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = (ROOT / ".github/workflows/vp-register.yml").read_text()
RESEARCH = (ROOT / ".github/workflows/vp-research.yml").read_text()


def _trigger_block(workflow: str) -> str:
    return workflow.split("concurrency:", 1)[0]


def test_both_lanes_are_dispatch_only() -> None:
    """Re-running a predictive test on a cadence IS multiple testing.

    Sealing on a cadence is worse: it would mint a fresh hypothesis id on every
    fire, which is how a pre-registration becomes a search over statements.
    """
    for workflow in (REGISTER, RESEARCH):
        assert "workflow_dispatch:" in workflow
        trigger = _trigger_block(workflow)
        assert "\n  schedule:" not in trigger
        assert "\n  workflow_run:" not in trigger
        assert "\n  push:" not in trigger
        assert "\n  pull_request:" not in trigger


def test_the_test_lane_cannot_seal_its_own_preregistration() -> None:
    """The decisive pin. `run` must never be able to register the hypothesis."""
    assert "vp-register" not in RESEARCH.split("jobs:", 1)[1]
    assert "save_hypothesis" not in RESEARCH
    assert "\n      register:" not in RESEARCH
    assert "inputs.register" not in RESEARCH


def test_the_register_lane_does_not_run_the_test() -> None:
    """And the converse: sealing must not produce a verdict in the same dispatch."""
    assert "run_vp_test" not in REGISTER
    assert "--cutoffs" not in REGISTER
    assert "inputs.cutoffs" not in REGISTER


def test_both_lanes_persist_only_on_an_explicit_opt_in() -> None:
    """Migration 0050 makes every row here undeletable, so the default writes nothing."""
    for workflow in (REGISTER, RESEARCH):
        persist = workflow.split("persist:", 1)[1].split("type: boolean", 1)[0]
        assert "default: false" in persist
        assert "inputs.persist &&" in workflow


def test_both_lanes_carry_only_the_database_secret_and_run_from_main() -> None:
    """A workflow holding a production secret must not run at a PR head (AGENTS.md §8)."""
    for workflow in (REGISTER, RESEARCH):
        assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in workflow
        assert "ref: refs/heads/main" in workflow
        assert "permissions:\n  contents: read" in workflow

        secrets_used = {
            fragment.split("}}", 1)[0].strip()
            for fragment in workflow.split("${{ secrets.")[1:]
        }
        assert secrets_used == {"DATABASE_URL"}, secrets_used
