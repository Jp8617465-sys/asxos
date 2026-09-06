#!/usr/bin/env python3
"""Derive GitHub Actions credential and runtime effects from checked-in YAML.

This is a report-only Phase-0 control-plane probe.  It reads workflow definitions,
never contacts GitHub, never resolves secret values, and never changes workflow
state.  Secret *names* and declared permissions are configuration and are included
so the later production-effect classifier has a deterministic starting point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

_SECRET_REF = re.compile(r"\bsecrets\.([A-Za-z_][A-Za-z0-9_]*)\b")
_FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_PRODUCT_RUN = re.compile(
    r"(?:^|[\s;&|])(?:"
    r"python(?:3)?\s+(?:-m\s+)?(?:asxos|jobs[/.]|scripts[/.])|"
    r"pytest\b|ruff\b|mypy\b|make\b|asx\b|"
    r"bash\s+(?:\./)?scripts/|"
    r"pip\s+install\s+(?:[^\n]*\s)?-e(?:\s|$)"
    r")",
    re.IGNORECASE,
)
_MODEL_ACTION = re.compile(r"(?:claude|anthropic|openai)", re.IGNORECASE)
_MODEL_SECRET_NAMES = {
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "OPENAI_API_KEY",
}
_PRIVILEGED_PERMISSION_KEYS = {
    "actions",
    "attestations",
    "checks",
    "contents",
    "deployments",
    "id-token",
    "issues",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
}
_MAX_WORKFLOW_BYTES = 1_000_000


class _UniqueBaseLoader(yaml.BaseLoader):
    """String-only YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueBaseLoader, node: yaml.MappingNode, *, deep: bool = False
) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a workflow mapping",
                node.start_mark,
                "workflow mapping keys must be strings",
                key_node.start_mark,
            )
        if key == "<<":
            raise yaml.constructor.ConstructorError(
                "while constructing a workflow mapping",
                node.start_mark,
                "YAML merge keys are not accepted in security inventory inputs",
                key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a workflow mapping",
                node.start_mark,
                f"duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueBaseLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return [value]


def _secret_names(value: object, *, _seen: set[int] | None = None) -> set[str]:
    if _seen is None:
        _seen = set()
    if isinstance(value, str):
        return set(_SECRET_REF.findall(value))
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in _seen:
            return set()
        _seen.add(identity)
        result: set[str] = set()
        for key, item in value.items():
            result.update(_secret_names(key, _seen=_seen))
            result.update(_secret_names(item, _seen=_seen))
        return result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        identity = id(value)
        if identity in _seen:
            return set()
        _seen.add(identity)
        result = set()
        for item in value:
            result.update(_secret_names(item, _seen=_seen))
        return result
    return set()


def _normalise_permissions(value: object) -> dict[str, str]:
    if value is None:
        return {"_source": "repository-default"}
    if isinstance(value, str):
        return {"_all": value}
    result = {key: str(item) for key, item in _mapping(value).items()}
    if not result:
        result["_all"] = "none"
    return result


def _write_permissions(permissions: Mapping[str, str]) -> list[str]:
    if permissions.get("_all") == "write-all":
        return ["write-all"]
    return sorted(
        key
        for key, value in permissions.items()
        if key in _PRIVILEGED_PERMISSION_KEYS and value == "write"
    )


def _trigger_inventory(value: object) -> tuple[list[str], list[str]]:
    if isinstance(value, str):
        return [value], []
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return sorted(str(item) for item in value), []

    triggers = _mapping(value)
    schedules = _sequence(triggers.get("schedule"))
    crons: list[str] = []
    for entry in schedules:
        cron = _mapping(entry).get("cron")
        if cron is not None:
            crons.append(str(cron))
    return sorted(triggers), crons


def _is_remote_action_pinned(uses: str) -> bool:
    if uses.startswith("./") or uses.startswith("docker://"):
        return True
    if "@" not in uses:
        return False
    ref = uses.rsplit("@", 1)[1]
    return bool(_FULL_SHA.fullmatch(ref))


def _step_inventory(steps: object) -> dict[str, Any]:
    checkout_refs: list[str] = []
    action_uses: list[str] = []
    unpinned_actions: list[str] = []
    run_command_digests: list[str] = []
    executes_product_code = False
    model_action = False

    for raw_step in _sequence(steps):
        step = _mapping(raw_step)
        uses = str(step.get("uses", ""))
        run = str(step.get("run", ""))

        if uses:
            action_uses.append(uses)
            if not _is_remote_action_pinned(uses):
                unpinned_actions.append(uses)
            if uses.startswith("./"):
                executes_product_code = True
            if _MODEL_ACTION.search(uses):
                model_action = True
            if uses.split("@", 1)[0].lower() == "actions/checkout":
                ref = _mapping(step.get("with")).get("ref")
                checkout_refs.append(str(ref) if ref is not None else "<event-default>")

        if run:
            # A checked-in command can itself contain a credential or sensitive URL.
            # Retain a stable audit handle without reproducing the command text.
            run_command_digests.append(hashlib.sha256(run.encode()).hexdigest())
            if _PRODUCT_RUN.search(run):
                executes_product_code = True

    return {
        "checkout_refs": checkout_refs,
        "action_uses": action_uses,
        "unpinned_actions": sorted(set(unpinned_actions)),
        "run_command_digests": run_command_digests,
        "executes_product_code": executes_product_code,
        "uses_model_action": model_action,
    }


def inspect_workflow(path: Path, *, root: Path) -> dict[str, Any]:
    """Return a deterministic effect inventory for one workflow file."""

    if path.is_symlink():
        raise ValueError(f"{path}: workflow must not be a symlink")
    if path.stat().st_size > _MAX_WORKFLOW_BYTES:
        raise ValueError(
            f"{path}: workflow exceeds {_MAX_WORKFLOW_BYTES} byte safety limit"
        )
    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueBaseLoader)
    document = _mapping(loaded)
    if not document:
        raise ValueError(f"{path}: workflow must be a YAML mapping")

    triggers, crons = _trigger_inventory(document.get("on"))
    workflow_permissions = _normalise_permissions(document.get("permissions"))
    workflow_secrets = _secret_names(document.get("env"))
    scheduled = "schedule" in triggers
    jobs: list[dict[str, Any]] = []

    for job_name, raw_job in sorted(_mapping(document.get("jobs")).items()):
        job = _mapping(raw_job)
        step_inventory = _step_inventory(job.get("steps"))
        permissions = (
            _normalise_permissions(job.get("permissions"))
            if "permissions" in job
            else dict(workflow_permissions)
        )
        secrets = workflow_secrets | _secret_names(job)
        uses_model = step_inventory["uses_model_action"] or bool(
            secrets & _MODEL_SECRET_NAMES
        )
        write_permissions = _write_permissions(permissions)
        scheduled_default_checkout = scheduled and "<event-default>" in step_inventory[
            "checkout_refs"
        ]

        findings: list[str] = []
        if step_inventory["unpinned_actions"]:
            findings.append("unpinned-action")
        if uses_model and write_permissions:
            findings.append("model-with-write-permission")
        if scheduled_default_checkout:
            findings.append("scheduled-event-default-checkout")
        if scheduled and step_inventory["executes_product_code"] and secrets:
            findings.append("scheduled-product-code-with-explicit-secret")
        if step_inventory["executes_product_code"] and secrets:
            findings.append("product-code-with-explicit-secret")

        jobs.append(
            {
                "name": job_name,
                "permissions": permissions,
                "write_permissions": write_permissions,
                "environment": job.get("environment"),
                "explicit_secret_names": sorted(secrets),
                "executes_product_code": step_inventory["executes_product_code"],
                "uses_model_action": uses_model,
                "checkout_refs": step_inventory["checkout_refs"],
                "action_uses": step_inventory["action_uses"],
                "unpinned_actions": step_inventory["unpinned_actions"],
                "run_command_digests": step_inventory["run_command_digests"],
                "findings": sorted(findings),
            }
        )

    return {
        "path": path.relative_to(root).as_posix(),
        "name": str(document.get("name", path.stem)),
        "triggers": triggers,
        "crons": crons,
        "scheduled": scheduled,
        "workflow_permissions": workflow_permissions,
        "workflow_write_permissions": _write_permissions(workflow_permissions),
        "explicit_secret_names": sorted(_secret_names(document)),
        "jobs": jobs,
    }


def build_inventory(workflows_dir: Path, *, root: Path) -> dict[str, Any]:
    """Inspect every YAML workflow under ``workflows_dir``."""

    workflow_paths = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflows_dir.glob(pattern)
        if path.is_file()
    )
    workflows = [inspect_workflow(path, root=root) for path in workflow_paths]

    finding_counts: dict[str, int] = {}
    scheduled_runtime_jobs: list[str] = []
    model_write_jobs: list[str] = []
    secret_names: set[str] = set()
    for workflow in workflows:
        secret_names.update(workflow["explicit_secret_names"])
        for job in workflow["jobs"]:
            identity = f"{workflow['path']}::{job['name']}"
            for finding in job["findings"]:
                finding_counts[finding] = finding_counts.get(finding, 0) + 1
            if workflow["scheduled"] and job["executes_product_code"]:
                scheduled_runtime_jobs.append(identity)
            if "model-with-write-permission" in job["findings"]:
                model_write_jobs.append(identity)

    return {
        "schema_version": 1,
        "workflows_dir": workflows_dir.relative_to(root).as_posix(),
        "summary": {
            "workflow_count": len(workflows),
            "scheduled_workflow_count": sum(item["scheduled"] for item in workflows),
            "explicit_secret_names": sorted(secret_names),
            "scheduled_runtime_jobs": scheduled_runtime_jobs,
            "model_write_jobs": model_write_jobs,
            "finding_counts": dict(sorted(finding_counts.items())),
        },
        "workflows": workflows,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="workflow directory relative to --root",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = args.root.resolve()
    workflows_dir = args.workflows_dir
    if not workflows_dir.is_absolute():
        workflows_dir = root / workflows_dir
    workflows_dir = workflows_dir.resolve()
    try:
        workflows_dir.relative_to(root)
    except ValueError as exc:
        raise SystemExit("--workflows-dir must be inside --root") from exc
    if not workflows_dir.is_dir():
        raise SystemExit(f"workflow directory does not exist: {workflows_dir}")

    inventory = build_inventory(workflows_dir, root=root)
    print(
        json.dumps(
            inventory,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
