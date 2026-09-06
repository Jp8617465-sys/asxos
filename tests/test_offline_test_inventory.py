"""Pins on the offline-test inventory generator and its committed artifact.

Two jobs. First, prove the generator actually detects what it claims — a
detector nobody has watched fire reads as coverage while finding nothing, the
same argument ``tests/test_no_bare_date_today.py`` makes for its AST visitor.
Second, stop ``docs/ops/offline-test-inventory.json`` rotting: the artifact is
the standing statement of the suite's deliberate external surface, and a stale
one is worse than none because it is read as current.

The module-loading idiom follows ``tests/test_workflow_effects.py``.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "offline_test_inventory.py"
_ARTIFACT = _ROOT / "docs" / "ops" / "offline-test-inventory.json"

_SPEC = importlib.util.spec_from_file_location("offline_test_inventory", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
offline_test_inventory = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(offline_test_inventory)


def _write(root: Path, name: str, body: str) -> Path:
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    path = tests / name
    path.write_text(body, encoding="utf-8")
    return path


def _build(root: Path) -> dict:
    return offline_test_inventory.build_inventory(root / "tests", root=root)


# ---------------------------------------------------------------------------
# The generator detects each finding
# ---------------------------------------------------------------------------


def test_env_gated_integration_is_derived(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test_integration.py",
        """
import os
import psycopg2
import pytest

pytestmark = pytest.mark.network

_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
if _URL is None:
    pytest.skip("needs a database", allow_module_level=True)
""",
    )
    inventory = _build(tmp_path)
    (entry,) = inventory["tests"]
    assert entry["findings"] == [
        "env-gated-integration",
        "network-client-import",
        "network-marked",
    ]
    assert entry["opt_in_env_vars"] == ["MIGRATION_TEST_DATABASE_URL"]
    assert entry["egress_client_imports"] == ["psycopg2"]
    assert inventory["summary"]["opt_in_env_vars"] == ["MIGRATION_TEST_DATABASE_URL"]


def test_unconditional_network_marker_is_flagged(tmp_path: Path) -> None:
    """A marker with no env gate is the shape that would let a genuinely
    external test run on an ordinary invocation."""
    _write(
        tmp_path,
        "test_marked.py",
        """
import pytest

@pytest.mark.network
def test_calls_out():
    pass
""",
    )
    (entry,) = _build(tmp_path)["tests"]
    assert "network-marked-without-env-gate" in entry["findings"]
    assert entry["network_marked_tests"] == ["test_calls_out"]


def test_subprocess_command_is_derived(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test_spawn.py",
        """
import subprocess
import sys

def test_a():
    subprocess.run(["bash", "-n", "x.sh"])

def test_b():
    subprocess.run([sys.executable, "-c", "print(1)"])
""",
    )
    (entry,) = _build(tmp_path)["tests"]
    assert entry["findings"] == ["subprocess-spawns-process"]
    assert entry["spawned_commands"] == ["bash", "sys.executable"]


def test_unremarkable_module_is_omitted(tmp_path: Path) -> None:
    """Only flagged modules are reported, so the artifact does not churn on
    every unrelated test added to the suite."""
    _write(tmp_path, "test_plain.py", "def test_ok():\n    assert True\n")
    inventory = _build(tmp_path)
    assert inventory["tests"] == []
    assert inventory["summary"]["flagged_module_count"] == 0


def test_detection_ignores_comments_and_docstrings(tmp_path: Path) -> None:
    """AST, not grep. A module that merely *discusses* the marker is not marked —
    otherwise every doc-bearing module would land in the inventory."""
    _write(
        tmp_path,
        "test_prose.py",
        '''"""Explains that @pytest.mark.network exists and uses httpx."""
# import httpx  -- and pytest.mark.network -- are only mentioned here
def test_ok():
    assert True
''',
    )
    assert _build(tmp_path)["tests"] == []


# ---------------------------------------------------------------------------
# The committed artifact stays true
# ---------------------------------------------------------------------------


def test_committed_artifact_matches_a_fresh_run() -> None:
    """Regenerate with:

        python scripts/offline_test_inventory.py --root . > docs/ops/offline-test-inventory.json
    """
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    fresh = json.loads(
        json.dumps(_build(_ROOT), sort_keys=True)
    )
    assert committed == fresh, (
        "docs/ops/offline-test-inventory.json is stale. The suite's external "
        "surface changed; regenerate the artifact and review the diff."
    )


# ---------------------------------------------------------------------------
# Modules that mention the marker in prose or in fixture source without being
# marked. A textual scan cannot tell these apart from a real marker — which is
# precisely why the generator parses the AST — so they are listed explicitly
# rather than the cross-check below being weakened to a subset test.
# ---------------------------------------------------------------------------
_DISCUSSES_MARKER_ONLY = {
    # Builds marked modules as fixture strings and greps for the marker itself.
    "tests/test_offline_test_inventory.py",
}


def _modules_mentioning_marker() -> set[str]:
    pattern = re.compile(r"pytest\.mark\.network")
    return {
        path.relative_to(_ROOT).as_posix()
        for path in sorted((_ROOT / "tests").glob("test_*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    }


def test_marker_text_scan_agrees_with_the_inventory() -> None:
    """Independent cross-check: a textual scan must find the same modules.

    The generator reads the AST. Grepping is a genuinely different method, so
    agreement between the two is evidence rather than a tautology — if the AST
    matcher silently stopped matching, this would still see the marker.
    """
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    by_text = _modules_mentioning_marker() - _DISCUSSES_MARKER_ONLY
    assert by_text == set(committed["summary"]["network_marked_modules"])


def test_discussion_allowlist_does_not_outlive_what_it_excuses() -> None:
    """The allow-list must not silently widen into a hole.

    Each entry has to still exist, still mention the marker, and still NOT be
    marked. If one becomes genuinely marked, it belongs in the inventory and the
    entry has to go.
    """
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    marked = set(committed["summary"]["network_marked_modules"])
    for rel in sorted(_DISCUSSES_MARKER_ONLY):
        path = _ROOT / rel
        assert path.exists(), f"allow-listed module no longer exists: {rel}"
        assert rel in _modules_mentioning_marker(), (
            f"{rel} no longer mentions pytest.mark.network — "
            "remove it from _DISCUSSES_MARKER_ONLY."
        )
        assert rel not in marked, (
            f"{rel} is now genuinely network-marked — remove it from "
            "_DISCUSSES_MARKER_ONLY so the cross-check covers it."
        )


def test_every_opt_in_is_env_gated_or_justified() -> None:
    """The suite's external surface, stated as an assertion.

    Exactly one module may reach a real endpoint, and only when
    MIGRATION_TEST_DATABASE_URL is set. The guard's own regression module also
    carries the marker, but its marked test asserts the guard is disarmed and
    performs no egress. Any third entry is a deliberate expansion of the
    external surface and must be reviewed here.
    """
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    assert committed["summary"]["network_marked_modules"] == [
        "tests/test_network_guard.py",
        "tests/test_price_revision_migration_integration.py",
    ]
    assert committed["summary"]["opt_in_env_vars"] == ["MIGRATION_TEST_DATABASE_URL"]


def test_artifact_declares_its_schema_version() -> None:
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    assert committed["schema_version"] == 1
    assert committed["tests_dir"] == "tests"
