from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

_SCRIPT = Path(__file__).parents[1] / "scripts" / "workflow_effects.py"
_SPEC = importlib.util.spec_from_file_location("workflow_effects", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
workflow_effects = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(workflow_effects)


def _write_workflow(root: Path, name: str, body: str) -> Path:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    path = workflows / name
    path.write_text(body, encoding="utf-8")
    return path


def test_scheduled_secret_job_and_event_default_checkout_are_derived(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "daily.yml",
        """
name: daily
on:
  schedule:
    - cron: "0 1 * * *"
permissions:
  contents: read
jobs:
  run:
    runs-on: ubuntu-latest
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
      - run: python jobs/daily.py
""",
    )

    result = workflow_effects.build_inventory(
        tmp_path / ".github" / "workflows", root=tmp_path
    )

    assert result["summary"]["scheduled_workflow_count"] == 1
    assert result["summary"]["scheduled_runtime_jobs"] == [
        ".github/workflows/daily.yml::run"
    ]
    job = result["workflows"][0]["jobs"][0]
    assert job["checkout_refs"] == ["<event-default>"]
    assert job["explicit_secret_names"] == ["DATABASE_URL"]
    assert job["findings"] == [
        "product-code-with-explicit-secret",
        "scheduled-event-default-checkout",
        "scheduled-product-code-with-explicit-secret",
    ]


def test_explicit_release_ref_avoids_default_checkout_finding(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "release.yml",
        """
on:
  schedule:
    - cron: "0 1 * * *"
permissions: {}
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
        with:
          ref: refs/heads/production
      - run: python scripts/report.py
""",
    )

    workflow = workflow_effects.inspect_workflow(
        tmp_path / ".github" / "workflows" / "release.yml", root=tmp_path
    )

    job = workflow["jobs"][0]
    assert job["checkout_refs"] == ["refs/heads/production"]
    assert "scheduled-event-default-checkout" not in job["findings"]


def test_model_job_with_write_permission_is_reported(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "model.yml",
        """
on: workflow_dispatch
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@0123456789abcdef0123456789abcdef01234567
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
""",
    )

    result = workflow_effects.build_inventory(
        tmp_path / ".github" / "workflows", root=tmp_path
    )

    assert result["summary"]["model_write_jobs"] == [
        ".github/workflows/model.yml::build"
    ]
    job = result["workflows"][0]["jobs"][0]
    assert job["write_permissions"] == ["contents"]
    assert job["uses_model_action"] is True
    assert job["findings"] == ["model-with-write-permission"]


def test_unpinned_remote_action_is_reported_but_local_action_is_not(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "actions.yml",
        """
on: pull_request
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./local-action
""",
    )

    workflow = workflow_effects.inspect_workflow(
        tmp_path / ".github" / "workflows" / "actions.yml", root=tmp_path
    )

    job = workflow["jobs"][0]
    assert job["unpinned_actions"] == ["actions/checkout@v4"]
    assert job["executes_product_code"] is True
    assert job["findings"] == ["unpinned-action"]


def test_workflow_level_secret_is_inherited_by_job_inventory(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "inherited.yml",
        """
on: push
env:
  API_TOKEN: ${{ secrets.EXTERNAL_API_TOKEN }}
permissions: read-all
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: python -m asxos.cli.main --help
""",
    )

    workflow = workflow_effects.inspect_workflow(
        tmp_path / ".github" / "workflows" / "inherited.yml", root=tmp_path
    )

    job = workflow["jobs"][0]
    assert job["permissions"] == {"_all": "read-all"}
    assert job["explicit_secret_names"] == ["EXTERNAL_API_TOKEN"]
    assert job["findings"] == ["product-code-with-explicit-secret"]


def test_inventory_is_json_serialisable_and_stably_sorted(tmp_path: Path) -> None:
    _write_workflow(tmp_path, "z.yml", "on: push\njobs: {}\n")
    _write_workflow(tmp_path, "a.yaml", "on: pull_request\njobs: {}\n")

    result = workflow_effects.build_inventory(
        tmp_path / ".github" / "workflows", root=tmp_path
    )

    assert [item["path"] for item in result["workflows"]] == [
        ".github/workflows/a.yaml",
        ".github/workflows/z.yml",
    ]
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_duplicate_yaml_key_is_rejected(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        "duplicate.yml",
        "on: push\non: pull_request\njobs: {}\n",
    )

    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key: on"):
        workflow_effects.inspect_workflow(path, root=tmp_path)


def test_yaml_merge_key_is_rejected(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        "merge.yml",
        """
on: push
defaults: &defaults
  runs-on: ubuntu-latest
jobs:
  check:
    <<: *defaults
    steps: []
""",
    )

    with pytest.raises(
        yaml.constructor.ConstructorError,
        match="YAML merge keys are not accepted",
    ):
        workflow_effects.inspect_workflow(path, root=tmp_path)


def test_oversized_workflow_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_workflow(tmp_path, "large.yml", "on: push\njobs: {}\n")
    monkeypatch.setattr(workflow_effects, "_MAX_WORKFLOW_BYTES", 10)

    with pytest.raises(ValueError, match="workflow exceeds 10 byte safety limit"):
        workflow_effects.inspect_workflow(path, root=tmp_path)


def test_symlinked_workflow_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.yml"
    outside.write_text("on: push\njobs: {}\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    linked = workflows / "linked.yml"
    linked.symlink_to(outside)

    with pytest.raises(ValueError, match="must not be a symlink"):
        workflow_effects.inspect_workflow(linked, root=tmp_path)


def test_workflows_directory_must_be_beneath_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outside = tmp_path.parent / "outside-workflows"
    outside.mkdir(exist_ok=True)
    monkeypatch.setattr(
        "sys.argv",
        [str(_SCRIPT), "--root", str(tmp_path), "--workflows-dir", str(outside)],
    )

    with pytest.raises(SystemExit, match="must be inside"):
        workflow_effects.main()
