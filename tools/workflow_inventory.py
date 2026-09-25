#!/usr/bin/env python3
"""Typed inventory of GitHub Actions exposure, derived from checked-in YAML.

Report-only. Parses workflow definitions with the hardened loader from
``scripts/workflow_effects.py``, contacts GitHub never, and resolves no secret
value — only secret *names*, which are configuration.

Why this exists, and why the criterion is what it is
----------------------------------------------------
The question a reviewer needs answered is **not** "which workflows run on push to
``claude/**``". It is:

    which workflows run at the PULL-REQUEST HEAD with repository secrets available?

Same-repo pull requests qualify: GitHub withholds secrets only from *fork* PRs.
So a workflow with a ``pull_request`` trigger and a secret reference is reachable
by an agent-authored PR, and — if that PR can edit the workflow file itself —
the *modified* definition is what runs, at head, with the secret.

Framing it as "push to claude/**" produced a wrong answer once already: a grep
for the branch pattern suggested seven exposed workflows, where reading the
``on:`` blocks showed two, both secretless, and missed the two that are actually
exposed (``migration-drift`` via its own path filter, ``pr-review-agent`` on
``ready_for_review``). The criterion below is computed from the parsed document,
never asserted by hand.

Emits typed JSON records so the output can feed the production-effect manifest
builder directly. ``--format md`` renders the review table from those same
records, so the prose can never drift from the data.

Reuse and one deliberate divergence
-----------------------------------
Loader, permission normalisation and secret-name extraction come from
``scripts/workflow_effects.py``. ``_secret_names()`` there already recurses over
the whole document, so it sees ``run:`` bodies, not just ``env:`` blocks.

It is **not** reused for action pinning. ``_is_remote_action_pinned()`` returns
True for ``./local`` and ``docker://image:tag`` refs — correct for its own
question ("is a remote action unpinned?"), wrong for this one: a local composite
action carries arbitrary steps and has no SHA to check, and a docker tag is
mutable. This module records a ``pin_state`` enum instead, so those two are
visible rather than silently counted as safe.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

_PR_HEAD_TRIGGERS = frozenset({"pull_request", "pull_request_target", "workflow_run"})
# The second criterion (build loop, 2026-09-25). These events carry a payload written by
# anyone who can open an issue or comment on this PUBLIC repository. A workflow that
# runs on one of them must hold no lane secret and never run the agent action: the
# payload would be untrusted text sitting next to a PAT, which is the shape Layer 1 of
# the build loop exists to keep model-free.
_UNTRUSTED_EVENT_TRIGGERS = frozenset(
    {
        "issues",
        "issue_comment",
        "pull_request_review",
        "pull_request_review_comment",
        "discussion",
        "discussion_comment",
    }
)
_LANE_SECRETS = frozenset({"ARBI_GITHUB_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "SUPABASE_ACCESS_TOKEN"})
_AGENT_ACTION = "anthropics/claude-code-action"
_FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

# Secret access spellings that a bare `secrets.NAME` scan does not see.
_SECRETS_CONTEXT_DUMP = re.compile(
    r"toJSON\s*\(\s*secrets\s*\)|secrets\s*\[\s*['\"]", re.IGNORECASE
)
_EXECUTED_PATH = re.compile(r"\b(?:asxos|jobs|scripts|tools|tests|migrations)/[\w./-]+")


def _load_workflow_effects() -> Any:
    """Import scripts/workflow_effects.py by path.

    `scripts/` is excluded from the installed package and carries no
    `__init__.py`, so a path import is the honest way in — the same idiom
    `tests/test_workflow_effects.py` uses.
    """
    path = Path(__file__).resolve().parents[1] / "scripts" / "workflow_effects.py"
    spec = importlib.util.spec_from_file_location("workflow_effects", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_wf = _load_workflow_effects()


def _pin_state(uses: str) -> str:
    """Classify an action reference. Deliberately finer than a pinned/unpinned bool."""
    if uses.startswith("./") or uses.startswith("../"):
        return "local"
    if uses.startswith("docker://"):
        return "docker"
    if "@" not in uses:
        return "unpinned"
    ref = uses.rsplit("@", 1)[1]
    if _FULL_SHA.fullmatch(ref):
        return "sha"
    if re.fullmatch(r"v?\d+(\.\d+)*", ref):
        return "tag"
    return "branch"


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _trigger_details(on_value: object) -> dict[str, Any]:
    """Pull triggers, branch filters and path filters out of the `on:` block."""
    triggers: list[str] = []
    branch_filters: list[str] = []
    path_filters: list[str] = []

    if isinstance(on_value, str):
        triggers = [on_value]
    elif isinstance(on_value, list):
        triggers = [str(item) for item in on_value]
    else:
        mapping = _wf._mapping(on_value)
        triggers = sorted(mapping)
        for name, body in mapping.items():
            spec = _wf._mapping(body)
            for key in ("branches", "branches-ignore"):
                branch_filters.extend(f"{name}:{b}" for b in _as_list(spec.get(key)))
            for key in ("paths", "paths-ignore"):
                path_filters.extend(f"{name}:{p}" for p in _as_list(spec.get(key)))

    return {
        "triggers": triggers,
        "branch_filters": sorted(set(branch_filters)),
        "path_filters": sorted(set(path_filters)),
    }


def _secrets_inherit(document: object) -> bool:
    """Detect `secrets: inherit` on a reusable-workflow call.

    A bare `secrets.NAME` scan cannot see this: there is no dot, and it passes
    EVERY repository secret to the called workflow.
    """
    for job in _wf._mapping(_wf._mapping(document).get("jobs")).values():
        if str(_wf._mapping(job).get("secrets", "")).strip() == "inherit":
            return True
    return False


def _scan_text(document: object) -> tuple[bool, list[str]]:
    """Whole-document text scan for context dumps and executed repo paths."""
    blob = json.dumps(document, sort_keys=True, default=str)
    dump = bool(_SECRETS_CONTEXT_DUMP.search(blob))
    return dump, sorted(set(_EXECUTED_PATH.findall(blob)))


def inspect_workflow(path: Path, *, root: Path) -> dict[str, Any]:
    document = _wf.yaml.load(path.read_text(encoding="utf-8"), Loader=_wf._UniqueBaseLoader)
    mapping = _wf._mapping(document)
    rel = path.relative_to(root).as_posix()

    details = _trigger_details(mapping.get(True, mapping.get("on")))
    runs_at_pr_head = bool(_PR_HEAD_TRIGGERS.intersection(details["triggers"]))

    secret_refs = sorted(_wf._secret_names(document))
    inherits = _secrets_inherit(document)
    dump, executed_paths = _scan_text(document)

    permissions = _wf._normalise_permissions(mapping.get("permissions"))
    jobs = _wf._mapping(mapping.get("jobs"))

    action_uses: list[dict[str, str]] = []
    conditions: list[str] = []
    for name, raw_job in jobs.items():
        job = _wf._mapping(raw_job)
        if job.get("if") is not None:
            conditions.append(f"{name}: {job['if']}")
        for raw_step in _wf._sequence(job.get("steps")):
            uses = str(_wf._mapping(raw_step).get("uses", ""))
            if uses:
                action_uses.append({"ref": uses, "pin_state": _pin_state(uses)})

    runs_on_untrusted_event = bool(_UNTRUSTED_EVENT_TRIGGERS.intersection(details["triggers"]))
    agent_action_uses = sorted(
        {a["ref"] for a in action_uses if a["ref"].startswith(_AGENT_ACTION)}
    )
    lane_secret_refs = sorted(_LANE_SECRETS.intersection(secret_refs))

    return {
        "workflow": path.name,
        "path": rel,
        **details,
        "runs_at_pr_head": runs_at_pr_head,
        "runs_on_untrusted_event": runs_on_untrusted_event,
        "job_conditions": sorted(conditions),
        "secret_refs": secret_refs,
        "lane_secret_refs": lane_secret_refs,
        "secrets_inherit": inherits,
        "secrets_context_dump": dump,
        # The criterion, computed rather than asserted.
        "exposed_to_authored_pr": runs_at_pr_head and bool(secret_refs or inherits or dump),
        # The second criterion: untrusted payload next to a lane credential or the agent.
        "agent_action_uses": agent_action_uses,
        "agent_on_untrusted_event": runs_on_untrusted_event
        and bool(agent_action_uses or lane_secret_refs or inherits or dump),
        "permissions": permissions,
        "write_permissions": _wf._write_permissions(permissions),
        "action_uses": action_uses,
        "unsafe_pins": sorted({a["ref"] for a in action_uses if a["pin_state"] != "sha"}),
        "executed_paths": executed_paths,
        # A workflow whose own path filter names its own file re-runs itself on a
        # PR that edits it — the exact "edits that workflow file" case.
        "self_referential_path_filter": any(rel in entry for entry in details["path_filters"]),
        "job_count": len(jobs),
    }


def build_inventory(workflows_dir: Path, *, root: Path) -> dict[str, Any]:
    workflows = [
        inspect_workflow(path, root=root)
        for path in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    ]
    exposed = [w["path"] for w in workflows if w["exposed_to_authored_pr"]]
    return {
        "schema_version": 2,
        "workflows_dir": workflows_dir.relative_to(root).as_posix(),
        "summary": {
            "workflow_count": len(workflows),
            "pr_head_workflows": sorted(w["path"] for w in workflows if w["runs_at_pr_head"]),
            "exposed_to_authored_pr": sorted(exposed),
            "untrusted_event_agent_workflows": sorted(
                w["path"] for w in workflows if w["agent_on_untrusted_event"]
            ),
            "secrets_inherit_workflows": sorted(
                w["path"] for w in workflows if w["secrets_inherit"]
            ),
            "self_referential_path_filters": sorted(
                w["path"] for w in workflows if w["self_referential_path_filter"]
            ),
            "unsafe_pin_workflows": sorted(w["path"] for w in workflows if w["unsafe_pins"]),
            "all_secret_names": sorted({name for w in workflows for name in w["secret_refs"]}),
        },
        "workflows": workflows,
    }


def render_markdown(inventory: dict[str, Any]) -> str:
    """Render the review table FROM the records, so prose cannot drift from data."""
    lines = [
        "| Workflow | PR-head trigger | Secret refs | Exposed | Unsafe pins |",
        "|---|---|---|---|---|",
    ]
    for wf in inventory["workflows"]:
        pr_triggers = sorted(_PR_HEAD_TRIGGERS.intersection(wf["triggers"])) or ["—"]
        secrets = ", ".join(wf["secret_refs"]) or "none"
        if wf["secrets_inherit"]:
            secrets += " +inherit"
        if wf["secrets_context_dump"]:
            secrets += " +context-dump"
        lines.append(
            f"| `{wf['workflow']}` | {' '.join(pr_triggers)} | {secrets} | "
            f"{'**YES**' if wf['exposed_to_authored_pr'] else 'no'} | "
            f"{', '.join(wf['unsafe_pins']) or '—'} |"
        )
    summary = inventory["summary"]
    lines += [
        "",
        f"Workflows: {summary['workflow_count']} · "
        f"PR-head: {len(summary['pr_head_workflows'])} · "
        f"**exposed to an authored PR: {len(summary['exposed_to_authored_pr'])}**",
    ]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workflows-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--format", choices=("json", "md"), default="json")
    parser.add_argument("--compact", action="store_true")
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
    if args.format == "md":
        print(render_markdown(inventory))
    else:
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
