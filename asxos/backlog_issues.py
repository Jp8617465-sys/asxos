"""Layer 4 of the build loop — the picker: which `ready` issues may this fire build.

Successor to ``asxos/backlog.py``'s YAML picker. The queue is GitHub Issues now
(AGENTS.md §11 — live work state belongs to Issues); ``docs/product/backlog.yaml`` is the
archive and a provenance target, and ``asxos.backlog`` stays the authority for the denied
path set and the overlap rule, both reused here unchanged.

A ``ready`` label is not trusted by itself. At pickup, for every open ``ready`` issue:

1. **Who applied it.** The latest ``labeled ready`` timeline event's actor must be the
   repository owner (James and arbi share that login). A label from any other actor —
   the Cursor GitHub App, a collaborator with triage rights — is stripped:
   ``ready-actor-not-owner``. No event at all is ``ready-actor-unknown``.
2. **What it was applied to.** If a readiness marker exists (arbi readied it), its
   ``body_sha`` must match the current body: ``edited-after-ready`` otherwise.
   No marker means James applied it by hand; his ``ready`` is his explicit ask.
3. **Layer 1 again, now.** ``evaluate`` re-runs against the current checkout and the
   current set of open issues — a dependency opened since, a path newly denied, a
   reserved label added: ``eligibility-failed:<rule>``.

Any strip removes the label and leaves a ``stripped`` marker naming the rule, so the
digest can list it. What survives is ranked — James's hand-readied first, then Green
before Amber, then the issue more open issues depend on, then the lower number — and
picked one at a time, skipping anything whose declared paths overlap an earlier pick
(independent branches only; stacking needs a force-push the guard denies). ``hold``
always blocks. Only ``type:product`` is buildable: ``data-infra`` names ``migrations/``
and is refused by the denied set; ``research`` is attended by definition.

Exit codes mirror the old picker: 0 picked at least one · 2 schema/GitHub error ·
3 nothing to build.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

from asxos.backlog import paths_overlap
from asxos.clock import today
from asxos.domain.governance.github_commands import IssueComment
from asxos.domain.governance.issue_eligibility import (
    IssueRecord,
    Verdict,
    body_sha,
    depends_on,
    eligibility_marker,
    evaluate,
    files_to_touch,
    parse_readiness_marker,
    parse_sections,
)
from asxos.domain.governance.provenance import RepoProvenance

READY_LABEL: Final[str] = "ready"
HOLD_LABEL: Final[str] = "hold"
BUILDABLE_TYPES: Final[frozenset[str]] = frozenset({"type:product"})
SIGNATURE: Final[str] = "— arbi (`asxos/backlog_issues.py`)"
PICK_FILE: Final[str] = "backlog-pick.json"


class PickerAPI(Protocol):
    def owner_login(self) -> str: ...
    def issue(self, number: int) -> dict[str, Any]: ...
    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]: ...
    def comments(self, number: int) -> list[IssueComment]: ...
    def timeline(self, number: int) -> list[dict[str, Any]]: ...
    def post_comment(self, number: int, body: str) -> int: ...
    def remove_label(self, number: int, label: str) -> None: ...


@dataclass(frozen=True)
class Candidate:
    number: int
    title: str
    body_sha: str
    paths: tuple[str, ...]
    cls: str  # "james" (hand-readied, no marker) | "green" | "amber"
    depends_on: tuple[int, ...]
    open_dependents: int

    def as_dict(self, *, branch: str) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "body_sha": self.body_sha,
            "paths": list(self.paths),
            "class": self.cls,
            "depends_on": list(self.depends_on),
            "open_dependents": self.open_dependents,
            "branch": branch,
        }


@dataclass(frozen=True)
class Strip:
    rule: str
    detail: str


# --- Layer 4 -----------------------------------------------------------------------------


def ready_actor(timeline: Iterable[Mapping[str, Any]]) -> str | None:
    """The login that applied the latest ``ready`` label, from the timeline API."""
    actor: str | None = None
    for event in timeline:
        if event.get("event") != "labeled":
            continue
        if str((event.get("label") or {}).get("name", "")) != READY_LABEL:
            continue
        actor = str((event.get("actor") or {}).get("login") or "") or None
    return actor


def last_readiness_marker(comments: Iterable[IssueComment]) -> Any:
    found = None
    for comment in comments:
        marker = parse_readiness_marker(comment.body)
        if marker is not None:
            found = marker
    return found


def accept_ready(
    record: IssueRecord,
    *,
    timeline: Sequence[Mapping[str, Any]],
    comments: Sequence[IssueComment],
    owner_login: str,
    open_issues: Collection[int],
    resolve_provenance: Any,
) -> Strip | None:
    """None when the label may be trusted; otherwise the rule that strips it."""
    actor = ready_actor(timeline)
    if actor is None:
        return Strip("ready-actor-unknown", "no `labeled ready` event on the timeline")
    if actor.lower() != owner_login.lower():
        return Strip("ready-actor-not-owner", f"`ready` was applied by {actor!r}")
    sha = body_sha(record.body)
    marker = last_readiness_marker(comments)
    if marker is not None and marker.body_sha != sha:
        return Strip("edited-after-ready", "the body changed after arbi readied it")
    verdict: Verdict = evaluate(
        record,
        owner_login=owner_login,
        open_issues=open_issues,
        resolve_provenance=resolve_provenance,
    )
    if verdict.verdict != "eligible":
        return Strip(f"eligibility-failed:{verdict.rule}", verdict.detail)
    return None


# --- ranking and picking -------------------------------------------------------------


_CLASS_ORDER: Final[dict[str, int]] = {"james": 0, "green": 1, "amber": 2}


def rank_key(candidate: Candidate) -> tuple[int, int, int]:
    return (_CLASS_ORDER.get(candidate.cls, 3), -candidate.open_dependents, candidate.number)


def pick(
    candidates: Sequence[Candidate], max_items: int
) -> tuple[list[Candidate], list[Candidate]]:
    """``(picked, skipped_for_overlap)`` in rank order."""
    picked: list[Candidate] = []
    skipped: list[Candidate] = []
    for candidate in sorted(candidates, key=rank_key):
        if len(picked) >= max_items:
            break
        if any(paths_overlap(candidate.paths, p.paths) for p in picked):
            skipped.append(candidate)
            continue
        picked.append(candidate)
    return picked, skipped


def branch_name(number: int, date: Any) -> str:
    return f"claude/issue-{number}-{date.strftime('%Y%m%d')}"


# --- the run -----------------------------------------------------------------------------


def _record(raw: Mapping[str, Any]) -> IssueRecord:
    return IssueRecord(
        number=int(raw["number"]),
        author_login=str((raw.get("user") or {}).get("login") or ""),
        labels=frozenset(str(label.get("name", "")) for label in raw.get("labels") or []),
        title=str(raw.get("title") or ""),
        body=str(raw.get("body") or ""),
    )


def run(client: PickerAPI, *, repo_root: Path, max_items: int, run_id: str) -> dict[str, Any]:
    owner = client.owner_login()
    open_raw = client.list_issues(state="open")
    open_records = {int(raw["number"]): _record(raw) for raw in open_raw}
    open_numbers = set(open_records)
    dependents: dict[int, int] = dict.fromkeys(open_numbers, 0)
    for record in open_records.values():
        for dep in depends_on(parse_sections(record.body)):
            if dep in dependents:
                dependents[dep] += 1

    def parent_author(number: int) -> str | None:
        if number in open_records:
            return open_records[number].author_login
        try:
            return str((client.issue(number).get("user") or {}).get("login") or "")
        except Exception:  # an unreadable parent is "unresolved", not a crash
            return None

    provenance = RepoProvenance(root=repo_root, owner_login=owner, parent_author=parent_author)

    candidates: list[Candidate] = []
    stripped: list[dict[str, Any]] = []
    held: list[int] = []
    for number, record in sorted(open_records.items()):
        if READY_LABEL not in record.labels:
            continue
        if HOLD_LABEL in record.labels:
            held.append(number)
            continue
        comments = client.comments(number)
        strip = accept_ready(
            record,
            timeline=client.timeline(number),
            comments=comments,
            owner_login=owner,
            open_issues=open_numbers,
            resolve_provenance=provenance.resolve,
        )
        if strip is not None:
            client.remove_label(number, READY_LABEL)
            marker = eligibility_marker(
                verdict="stripped",
                rule=strip.rule,
                issue=number,
                body_sha=body_sha(record.body),
                run_id=run_id,
            )
            client.post_comment(
                number,
                f"{marker}\n↩️ `ready` removed (`{strip.rule}`) — {strip.detail}\n\n{SIGNATURE}",
            )
            stripped.append({"number": number, "rule": strip.rule})
            continue
        if not (record.labels & BUILDABLE_TYPES):
            continue
        sections = parse_sections(record.body)
        paths = files_to_touch(sections) or ()
        marker = last_readiness_marker(comments)
        candidates.append(
            Candidate(
                number=number,
                title=record.title,
                body_sha=body_sha(record.body),
                paths=tuple(paths),
                cls="james" if marker is None else str(marker.cls),
                depends_on=depends_on(sections),
                open_dependents=dependents.get(number, 0),
            )
        )

    picked, skipped = pick(candidates, max_items)
    date = today()
    return {
        "generated": date.isoformat(),
        "run_id": run_id,
        "owner": owner,
        "ready": len(candidates) + len(stripped) + len(held),
        "eligible": len(candidates),
        "held": held,
        "stripped": stripped,
        "picked": [c.as_dict(branch=branch_name(c.number, date)) for c in picked],
        "skipped_overlap": [c.number for c in skipped],
    }


# --- CLI ---------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env

    ap = argparse.ArgumentParser(
        prog="issue_next", description="Pick the next ready issues this fire may build (Layer 4)."
    )
    ap.add_argument("--max", type=int, default=1, dest="max_items")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--out", type=Path, default=Path(PICK_FILE))
    ns = ap.parse_args(argv)
    if not 1 <= ns.max_items <= 3:
        print("issue_next: --max must be between 1 and 3", file=sys.stderr)
        return 2
    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        print("issue_next: GH_TOKEN or ARBI_GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    client = GitHubClient(token=token, ref=repo_ref_from_env())
    try:
        report = run(
            client,
            repo_root=ns.root,
            max_items=ns.max_items,
            run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        )
    except GitHubUnavailable as exc:
        print(f"issue_next: GitHub unavailable: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2)
    ns.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["picked"] else 3
