"""Pins on the workflow exposure inventory.

The inventory answers one question: **which workflows run at the pull-request
head with repository secrets available?** Same-repo PRs receive secrets — only
fork PRs are withheld — so any such workflow is reachable by an agent-authored
PR, and if that PR can edit the workflow file, the modified definition is what
runs.

Every detector here is proved to fire on a fixture. That matters more than usual:
the framing this replaced ("push to `claude/**`") was derived from a grep and
gave the wrong answer in both directions — it counted seven workflows where two
matched, and it missed both of the genuinely exposed ones.

Module-loading follows tests/test_workflow_effects.py.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "tools" / "workflow_inventory.py"
_SPEC = importlib.util.spec_from_file_location("workflow_inventory", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
inv = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inv)


def _write(root: Path, name: str, body: str) -> Path:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def _one(root: Path) -> dict:
    (entry,) = inv.build_inventory(root / ".github" / "workflows", root=root)["workflows"]
    return entry


# ---------------------------------------------------------------------------
# The exposure criterion
# ---------------------------------------------------------------------------


def test_pull_request_with_secret_is_exposed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "review.yml",
        """
name: review
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets.OPENAI_API_KEY }}"
""",
    )
    entry = _one(tmp_path)
    assert entry["runs_at_pr_head"] is True
    assert entry["secret_refs"] == ["OPENAI_API_KEY"]
    assert entry["exposed_to_authored_pr"] is True


def test_pull_request_without_secret_is_not_exposed(tmp_path: Path) -> None:
    """A secretless PR lane is the safe shape — it must not be flagged, or the
    signal drowns in the three CI lanes that are fine."""
    _write(
        tmp_path,
        "ci.yml",
        """
name: ci
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
""",
    )
    entry = _one(tmp_path)
    assert entry["runs_at_pr_head"] is True
    assert entry["exposed_to_authored_pr"] is False


def test_scheduled_secret_workflow_is_not_pr_head(tmp_path: Path) -> None:
    """Secret-bearing but not PR-triggered: out of scope for this criterion."""
    _write(
        tmp_path,
        "nightly.yml",
        """
name: nightly
on:
  schedule:
    - cron: "0 1 * * *"
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: psql "${{ secrets.DATABASE_URL }}"
""",
    )
    entry = _one(tmp_path)
    assert entry["runs_at_pr_head"] is False
    assert entry["exposed_to_authored_pr"] is False


def test_workflow_run_and_pull_request_target_count_as_pr_head(tmp_path: Path) -> None:
    """Both run in base-repo context with secrets. Blocking only
    pull_request_target would leave workflow_run wide open."""
    for name, trigger in (("a.yml", "pull_request_target"), ("b.yml", "workflow_run")):
        root = tmp_path / trigger
        _write(
            root,
            name,
            f"""
name: {trigger}
on:
  {trigger}:
    types: [completed]
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{{{ secrets.TOKEN }}}}"
""",
        )
        entry = _one(root)
        assert entry["runs_at_pr_head"] is True, trigger
        assert entry["exposed_to_authored_pr"] is True, trigger


# ---------------------------------------------------------------------------
# Secret spellings a bare `secrets.NAME` scan cannot see
# ---------------------------------------------------------------------------


def test_secrets_inherit_is_detected(tmp_path: Path) -> None:
    """`secrets: inherit` has no dot, and passes EVERY repository secret to the
    called workflow. A `secrets\\.` regex misses it entirely."""
    _write(
        tmp_path,
        "caller.yml",
        """
name: caller
on:
  pull_request:
jobs:
  call:
    uses: ./.github/workflows/verify.yml
    secrets: inherit
""",
    )
    entry = _one(tmp_path)
    assert entry["secrets_inherit"] is True
    assert entry["secret_refs"] == []
    assert entry["exposed_to_authored_pr"] is True


def test_secrets_context_dump_is_detected(tmp_path: Path) -> None:
    """`toJSON(secrets)` and `secrets['NAME']` also carry no dot-name."""
    for name, expr in (
        ("dump.yml", "${{ toJSON(secrets) }}"),
        ("bracket.yml", "${{ secrets['DATABASE_URL'] }}"),
    ):
        root = tmp_path / name
        _write(
            root,
            name,
            f"""
name: {name}
on:
  pull_request:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "{expr}"
""",
        )
        entry = _one(root)
        assert entry["secrets_context_dump"] is True, expr
        assert entry["exposed_to_authored_pr"] is True, expr


def test_workflow_effects_alone_misses_these_spellings(tmp_path: Path) -> None:
    """Why this module exists rather than extending the caller.

    scripts/workflow_effects.py's `_secret_names()` finds only `secrets.NAME`.
    Pinning that here means the day it grows to cover these, this test fails and
    the duplication can be removed deliberately rather than by accident.
    """
    source = """
jobs:
  a:
    secrets: inherit
    steps:
      - run: echo "${{ toJSON(secrets) }} ${{ secrets['X'] }}"
"""
    document = inv._wf.yaml.load(source, Loader=inv._wf._UniqueBaseLoader)
    assert inv._wf._secret_names(document) == set()


# ---------------------------------------------------------------------------
# Action pin classification
# ---------------------------------------------------------------------------


def test_pin_state_distinguishes_local_and_docker_from_sha() -> None:
    """The reused helper calls `./local` and `docker://tag` "pinned".

    Correct for its own question, wrong for this one: a local composite action
    carries arbitrary steps and has no SHA to check, and a docker tag is mutable.
    """
    assert inv._pin_state("actions/checkout@" + "a" * 40) == "sha"
    assert inv._pin_state("actions/checkout@v4") == "tag"
    assert inv._pin_state("actions/checkout@main") == "branch"
    assert inv._pin_state("./.github/actions/thing") == "local"
    assert inv._pin_state("docker://alpine:3") == "docker"
    assert inv._pin_state("actions/checkout") == "unpinned"

    # The divergence, pinned so it cannot regress silently.
    assert inv._wf._is_remote_action_pinned("docker://alpine:3") is True
    assert inv._wf._is_remote_action_pinned("./.github/actions/thing") is True


def test_unsafe_pins_are_reported(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pins.yml",
        """
name: pins
on: [push]
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker://alpine:3
      - uses: ./.github/actions/local
""",
    )
    entry = _one(tmp_path)
    assert entry["unsafe_pins"] == [
        "./.github/actions/local",
        "actions/checkout@v4",
        "docker://alpine:3",
    ]


# ---------------------------------------------------------------------------
# Self-referential path filter
# ---------------------------------------------------------------------------


def test_self_referential_path_filter_is_flagged(tmp_path: Path) -> None:
    """A workflow whose own path filter names its own file re-runs itself on a PR
    that edits it — the literal "edits that workflow file" case."""
    _write(
        tmp_path,
        "drift.yml",
        """
name: drift
on:
  pull_request:
    paths:
      - "migrations/**"
      - ".github/workflows/drift.yml"
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets.DATABASE_URL }}"
""",
    )
    entry = _one(tmp_path)
    assert entry["self_referential_path_filter"] is True
    assert entry["exposed_to_authored_pr"] is True


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_markdown_is_rendered_from_the_records(tmp_path: Path) -> None:
    """The table is derived, never hand-written, so prose cannot drift from data."""
    _write(
        tmp_path,
        "review.yml",
        """
name: review
on:
  pull_request:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets.OPENAI_API_KEY }}"
""",
    )
    inventory = inv.build_inventory(tmp_path / ".github" / "workflows", root=tmp_path)
    table = inv.render_markdown(inventory)
    assert "OPENAI_API_KEY" in table
    assert "**YES**" in table
    assert "exposed to an authored PR: 1" in table


def test_inventory_is_json_serialisable_and_versioned(tmp_path: Path) -> None:
    _write(tmp_path, "ci.yml", "name: ci\non: [push]\njobs:\n  a:\n    steps: []\n")
    inventory = inv.build_inventory(tmp_path / ".github" / "workflows", root=tmp_path)
    assert inventory["schema_version"] == 1
    json.dumps(inventory, sort_keys=True)


# ---------------------------------------------------------------------------
# The live repo — the finding, asserted
# ---------------------------------------------------------------------------


def test_live_repo_exposure_set_is_pinned() -> None:
    """No workflow runs at the pull-request head with a repository secret.

    That is ACP phase P1's requirement, and this assertion is where it is met:
    `migration-drift.yml` and `pr-review-agent.yml` both lost their
    `pull_request` trigger, so the exposure set is empty rather than "two
    controlled uses".

    Any future entry is a deliberate expansion of the exposure surface and must
    be reviewed here — adding one means an agent-authored PR can again reach a
    secret at its own head.
    """
    inventory = inv.build_inventory(_ROOT / ".github" / "workflows", root=_ROOT)
    assert inventory["summary"]["exposed_to_authored_pr"] == []
    assert inventory["summary"]["secrets_inherit_workflows"] == []
    assert inventory["summary"]["unsafe_pin_workflows"] == []
