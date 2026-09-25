"""Layers 2–3 of the build loop: the label vocabulary, the brakes, the eligibility pass,
and applying arbi's readiness verdicts.

Where this sits. Layer 1 (``asxos.domain.governance.issue_eligibility``) is pure and
decides what may reach arbi at all. This module is the I/O around it, run by the
scheduled ``backlog-roll`` lane in this order:

1. :func:`eligibility_pass` — for every open issue with a ``type:*`` or ``needs-triage``
   label: strip a ``ready`` whose readiness marker no longer matches the body (the
   tamper brake), evaluate Layer 1, reconcile the verdict labels, post one marker
   comment when the verdict or the body changed, and write ``.eligible-issues.json``
   for the readiness step.
2. The readiness step is arbi's judgement, run by the lane's agent step against that
   file. It writes ``.readiness-verdicts.json`` and applies NO labels itself.
3. :func:`apply_readiness` — validates those verdicts against the eligible set (an
   issue the agent did not receive cannot be readied), then applies them under the
   brakes: the halt issue, ``AUTO_READY``, the daily cap, the WIP limit.

The brakes are repository variables, not constants (AGENTS.md §8a). ``AUTO_READY``
unset or anything other than ``on`` means OFF — the loop never arms itself by an
absent variable. WIP counts pull requests *waiting on James* (``needs-human``,
``hold``, or touching ``.claude/``), not every open PR: arbi merges its own Green and
Amber PRs, so "awaiting review" would be the wrong throttle.

Identity: arbi and James share one login. What the digest and the picker can tell
apart is the marker comment this module leaves — a readiness marker means arbi
readied it under these rules; a ``ready`` label with no marker means James applied
it by hand.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, Protocol

from asxos.domain.governance.github_commands import IssueComment
from asxos.domain.governance.issue_eligibility import (
    RESERVED_LABELS,
    RULESET_VERSION,
    TYPE_LABELS,
    IssueRecord,
    Verdict,
    body_sha,
    eligibility_marker,
    evaluate,
    parse_eligibility_marker,
    parse_readiness_marker,
    readiness_marker,
)
from asxos.domain.governance.provenance import RepoProvenance

AUTO_READY_ENV: Final[str] = "AUTO_READY"
DAILY_CAP_ENV: Final[str] = "AUTO_READY_DAILY_CAP"
WIP_LIMIT_ENV: Final[str] = "AUTO_READY_WIP_LIMIT"
DEFAULT_DAILY_CAP: Final[int] = 3
DEFAULT_WIP_LIMIT: Final[int] = 2

ELIGIBLE_FILE: Final[str] = ".eligible-issues.json"
VERDICTS_FILE: Final[str] = ".readiness-verdicts.json"

HALT_LABEL: Final[str] = "routines-halt"
HALT_TITLE_PREFIX: Final[str] = "HALT:"
TRIAGE_LABEL: Final[str] = "needs-triage"
READY_LABEL: Final[str] = "ready"
VERDICT_LABELS: Final[frozenset[str]] = frozenset({"eligible", "needs-info", "needs-human"})
#: Pull requests carrying one of these, or touching one of these paths, are waiting on
#: James: ``.claude/`` is arbi's own permission surface (AGENTS.md §8) and
#: ``docs/ops/routines/`` is the instructions its unattended sessions run under
#: (``_preamble.md`` §2) — arbi drafts both and never merges either.
WAITING_ON_JAMES_LABELS: Final[frozenset[str]] = frozenset({"needs-human", "hold"})
WAITING_ON_JAMES_PATHS: Final[tuple[str, ...]] = (".claude/", "docs/ops/routines/")
SIGNATURE: Final[str] = "— arbi (`asxos/autoready.py`)"

#: name → (colour, description). ``ensure_labels`` creates what is missing, never edits.
LABELS: Final[Mapping[str, tuple[str, str]]] = {
    "ready": ("0e8a16", "Layer 2 passed — the scheduled lane may build this"),
    "eligible": ("c5def5", "Layer 1 passed — awaiting arbi's readiness judgement"),
    "needs-info": (
        "fbca04",
        "Layer 1: a section is missing, a dependency is open, or no provenance",
    ),
    "needs-human": (
        "d93f0b",
        "Layer 1: James's — a reserved label, surface or path, or not the owner",
    ),
    "hold": ("5319e7", "Never picked while present"),
    "capital": ("b60205", "AGENTS.md §2 — James's"),
    "mandate": ("b60205", "AGENTS.md §2 — James's"),
    "incident": ("e11d21", "AGENTS.md §7 — new merges stop until it is fixed"),
    "needs-triage": ("ededed", "Filed from a conversational surface; Layer 1 runs on it"),
}


class IssuesAPI(Protocol):
    """The slice of ``asxos.github_api.GitHubClient`` this module uses — a Protocol so
    tests drive it with an in-memory fake, the way the decisions job's tests do."""

    def owner_login(self) -> str: ...
    def issue(self, number: int) -> dict[str, Any]: ...
    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]: ...
    def comments(self, number: int) -> list[IssueComment]: ...
    def post_comment(self, number: int, body: str) -> int: ...
    def add_labels(self, number: int, labels: Iterable[str]) -> None: ...
    def remove_label(self, number: int, label: str) -> None: ...
    def labels(self) -> list[dict[str, Any]]: ...
    def create_label(self, name: str, color: str, description: str) -> None: ...
    def list_pulls(self, *, state: str = "open") -> list[dict[str, Any]]: ...
    def pull_files(self, number: int) -> list[dict[str, Any]]: ...


# --- brakes ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Brakes:
    auto_ready: bool
    daily_cap: int = DEFAULT_DAILY_CAP
    wip_limit: int = DEFAULT_WIP_LIMIT


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit() or int(raw) < 0:
        raise RuntimeError(f"{name} must be a non-negative integer (got {raw!r})")
    return int(raw)


def brakes_from_env(env: Mapping[str, str] | None = None) -> Brakes:
    """``AUTO_READY`` is on only when it says ``on``; unset is off. Caps default 3 / 2."""
    env = os.environ if env is None else env
    return Brakes(
        auto_ready=env.get(AUTO_READY_ENV, "").strip().lower() == "on",
        daily_cap=_int_env(env, DAILY_CAP_ENV, DEFAULT_DAILY_CAP),
        wip_limit=_int_env(env, WIP_LIMIT_ENV, DEFAULT_WIP_LIMIT),
    )


def halted(client: IssuesAPI) -> bool:
    """James's kill switch from a phone (routines preamble §0): an open issue labelled
    ``routines-halt`` or titled ``HALT: …`` stops readiness cold."""
    if client.list_issues(labels=(HALT_LABEL,), state="open"):
        return True
    return any(
        str(issue.get("title", "")).startswith(HALT_TITLE_PREFIX)
        for issue in client.list_issues(state="open")
    )


def ensure_labels(client: IssuesAPI) -> list[str]:
    present = {str(label.get("name", "")) for label in client.labels()}
    created: list[str] = []
    for name, (colour, description) in LABELS.items():
        if name not in present:
            client.create_label(name, colour, description)
            created.append(name)
    return created


# --- records -----------------------------------------------------------------------------


def issue_record(raw: Mapping[str, Any]) -> IssueRecord:
    return IssueRecord(
        number=int(raw["number"]),
        author_login=str((raw.get("user") or {}).get("login") or ""),
        labels=frozenset(str(label.get("name", "")) for label in raw.get("labels") or []),
        title=str(raw.get("title") or ""),
        body=str(raw.get("body") or ""),
    )


def _last_readiness(comments: Sequence[IssueComment]) -> Any:
    found = None
    for comment in comments:
        marker = parse_readiness_marker(comment.body)
        if marker is not None:
            found = marker
    return found


def _last_eligibility(comments: Sequence[IssueComment]) -> Any:
    found = None
    for comment in comments:
        marker = parse_eligibility_marker(comment.body)
        if marker is not None:
            found = marker
    return found


def eligibility_comment(verdict: Verdict, *, issue: int, sha: str, run_id: str) -> str:
    marker = eligibility_marker(
        verdict=verdict.verdict, rule=verdict.rule, issue=issue, body_sha=sha, run_id=run_id
    )
    icon = {"eligible": "✅", "needs-info": "ℹ️", "needs-human": "🧑", "stripped": "↩️"}[
        verdict.verdict
    ]
    rule = f" (`{verdict.rule}`)" if verdict.rule else ""
    return f"{marker}\n{icon} `{verdict.verdict}`{rule} — {verdict.detail}\n\n{SIGNATURE}"


def readiness_comment(
    *,
    cls: Literal["green", "amber"],
    issue: int,
    sha: str,
    run_id: str,
    date: str,
    reasons: Sequence[str],
) -> str:
    marker = readiness_marker(cls=cls, issue=issue, body_sha=sha, run_id=run_id, date=date)
    bullets = "\n".join(f"- {reason}" for reason in reasons)
    return (
        f"{marker}\n✅ `ready` (class {cls}) — Layer 2 by arbi, rules {RULESET_VERSION}:\n"
        f"{bullets}\n\n{SIGNATURE}"
    )


# --- the eligibility pass ----------------------------------------------------------------


@dataclass
class EligibilityReport:
    run_id: str
    owner: str
    eligible: list[dict[str, Any]] = field(default_factory=list)
    verdicts: dict[int, Verdict] = field(default_factory=dict)
    stripped: list[int] = field(default_factory=list)
    comments_posted: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "owner": self.owner,
            "eligible": self.eligible,
            "stripped": self.stripped,
            "comments_posted": self.comments_posted,
            "verdicts": {str(n): [v.verdict, v.rule] for n, v in self.verdicts.items()},
        }


def _reconcile_labels(
    client: IssuesAPI, number: int, have: frozenset[str], want: str | None
) -> None:
    for label in sorted((have & VERDICT_LABELS) - ({want} if want else set())):
        client.remove_label(number, label)
    if want and want not in have:
        client.add_labels(number, [want])
    if TRIAGE_LABEL in have:
        client.remove_label(number, TRIAGE_LABEL)


def eligibility_pass(
    client: IssuesAPI,
    *,
    run_id: str,
    repo_root: Path,
    write_to: Path | None = None,
) -> EligibilityReport:
    """Layer 1 over every open issue that asked for it, with the tamper brake first."""
    owner = client.owner_login()
    raw_issues = client.list_issues(state="open")
    records = [issue_record(raw) for raw in raw_issues]
    open_numbers = {record.number for record in records}
    authors = {record.number: record.author_login for record in records}

    def parent_author(number: int) -> str | None:
        if number in authors:
            return authors[number]
        try:
            return str((client.issue(number).get("user") or {}).get("login") or "")
        except Exception:  # an unreadable parent is "unresolved", not a crash
            return None

    provenance = RepoProvenance(root=repo_root, owner_login=owner, parent_author=parent_author)
    report = EligibilityReport(run_id=run_id, owner=owner)

    for record in records:
        if not (record.labels & TYPE_LABELS) and TRIAGE_LABEL not in record.labels:
            continue
        comments = client.comments(record.number)
        sha = body_sha(record.body)
        labels = record.labels

        if READY_LABEL in labels:
            marker = _last_readiness(comments)
            if marker is not None and marker.body_sha != sha:
                client.remove_label(record.number, READY_LABEL)
                labels = labels - {READY_LABEL}
                stripped = Verdict(
                    "stripped", "edited-after-ready", "the body changed after it was readied"
                )
                client.post_comment(
                    record.number,
                    eligibility_comment(stripped, issue=record.number, sha=sha, run_id=run_id),
                )
                report.comments_posted += 1
                report.stripped.append(record.number)

        verdict = evaluate(
            record,
            owner_login=owner,
            open_issues=open_numbers,
            resolve_provenance=provenance.resolve,
        )
        report.verdicts[record.number] = verdict
        _reconcile_labels(client, record.number, labels, verdict.label)

        last = _last_eligibility(comments)
        changed = (
            last is None
            or last.verdict != verdict.verdict
            or last.rule != verdict.rule
            or last.body_sha != sha
        )
        if changed:
            client.post_comment(
                record.number,
                eligibility_comment(verdict, issue=record.number, sha=sha, run_id=run_id),
            )
            report.comments_posted += 1

        if verdict.verdict == "eligible":
            report.eligible.append(
                {
                    "number": record.number,
                    "title": record.title,
                    "body_sha": sha,
                    "labels": sorted(labels),
                    "already_ready": READY_LABEL in labels,
                }
            )

    if write_to is not None:
        write_to.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return report


# --- the brakes' inputs ------------------------------------------------------------------


def wip_waiting_on_james(client: IssuesAPI) -> int:
    """Open PRs James has to act on: ``needs-human``/``hold``, or a path only he merges."""
    count = 0
    for pull in client.list_pulls(state="open"):
        labels = {str(label.get("name", "")) for label in pull.get("labels") or []}
        if labels & WAITING_ON_JAMES_LABELS:
            count += 1
            continue
        files = client.pull_files(int(pull["number"]))
        if any(str(f.get("filename", "")).startswith(WAITING_ON_JAMES_PATHS) for f in files):
            count += 1
    return count


def auto_readied_today(client: IssuesAPI, date: str) -> int:
    """Readiness markers dated ``date`` on issues that still carry ``ready``."""
    count = 0
    for raw in client.list_issues(labels=(READY_LABEL,), state="open"):
        marker = _last_readiness(client.comments(int(raw["number"])))
        if marker is not None and marker.date == date:
            count += 1
    return count


# --- applying arbi's verdicts ------------------------------------------------------------


@dataclass(frozen=True)
class ReadinessVerdict:
    issue: int
    verdict: Literal["ready", "declined"]
    cls: Literal["green", "amber"]
    reasons: tuple[str, str, str]


def load_verdicts(path: Path) -> list[ReadinessVerdict]:
    """The agent's file, validated strictly — a malformed verdict is a failed run, never a guess."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError(f"{path.name}: expected a list of verdicts")
    out: list[ReadinessVerdict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {"issue", "verdict", "class", "reasons"}:
            raise RuntimeError(f"{path.name}[{i}]: keys must be issue, verdict, class, reasons")
        if not isinstance(item["issue"], int) or item["verdict"] not in ("ready", "declined"):
            raise RuntimeError(f"{path.name}[{i}]: bad issue or verdict")
        if item["class"] not in ("green", "amber"):
            raise RuntimeError(
                f"{path.name}[{i}]: class must be green or amber (Red is never readied)"
            )
        reasons = item["reasons"]
        if not (
            isinstance(reasons, list)
            and len(reasons) == 3
            and all(isinstance(r, str) and r.strip() for r in reasons)
        ):
            raise RuntimeError(f"{path.name}[{i}]: reasons must be three non-empty strings")
        out.append(ReadinessVerdict(item["issue"], item["verdict"], item["class"], tuple(reasons)))
    return out


@dataclass
class AppliedReport:
    readied: list[int] = field(default_factory=list)
    declined: list[int] = field(default_factory=list)
    refused: dict[int, str] = field(default_factory=dict)
    blocked_by: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "readied": self.readied,
            "declined": self.declined,
            "refused": {str(k): v for k, v in self.refused.items()},
            "blocked_by": self.blocked_by,
        }


def apply_readiness(
    client: IssuesAPI,
    *,
    verdicts: Sequence[ReadinessVerdict],
    eligible: Mapping[int, str],
    brakes: Brakes,
    run_id: str,
    date: str,
    is_halted: Callable[[IssuesAPI], bool] = halted,
) -> AppliedReport:
    """Apply verdicts under the brakes. Order: halt → ``AUTO_READY`` → per-verdict cap/WIP.

    ``eligible`` maps issue number → body_sha from this run's eligibility pass; a verdict
    for anything else is refused — the agent can only say yes to what Layer 1 handed it.
    """
    report = AppliedReport()
    if is_halted(client):
        report.blocked_by = "halt"
        return report
    if not brakes.auto_ready:
        report.blocked_by = f"{AUTO_READY_ENV} is not on"
        return report

    readied_today = auto_readied_today(client, date)
    wip = wip_waiting_on_james(client)
    for verdict in verdicts:
        sha = eligible.get(verdict.issue)
        if sha is None:
            report.refused[verdict.issue] = "not in this run's eligible set"
            continue
        if verdict.verdict == "declined":
            declined = Verdict("needs-info", "readiness-declined", "; ".join(verdict.reasons))
            _reconcile_labels(client, verdict.issue, frozenset({"eligible"}), "needs-info")
            client.post_comment(
                verdict.issue,
                eligibility_comment(declined, issue=verdict.issue, sha=sha, run_id=run_id),
            )
            report.declined.append(verdict.issue)
            continue
        if readied_today + len(report.readied) >= brakes.daily_cap:
            report.refused[verdict.issue] = f"daily cap {brakes.daily_cap} reached"
            continue
        if wip >= brakes.wip_limit:
            report.refused[verdict.issue] = (
                f"WIP limit {brakes.wip_limit}: {wip} PR(s) waiting on James"
            )
            continue
        client.add_labels(verdict.issue, [READY_LABEL])
        client.remove_label(verdict.issue, "eligible")
        client.post_comment(
            verdict.issue,
            readiness_comment(
                cls=verdict.cls,
                issue=verdict.issue,
                sha=sha,
                run_id=run_id,
                date=date,
                reasons=verdict.reasons,
            ),
        )
        report.readied.append(verdict.issue)
    return report


def eligible_from_file(path: Path) -> dict[int, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["number"]): str(row["body_sha"]) for row in data.get("eligible", [])}


__all__ = [
    "AUTO_READY_ENV",
    "DAILY_CAP_ENV",
    "ELIGIBLE_FILE",
    "LABELS",
    "RESERVED_LABELS",
    "VERDICTS_FILE",
    "WIP_LIMIT_ENV",
    "AppliedReport",
    "Brakes",
    "EligibilityReport",
    "IssuesAPI",
    "ReadinessVerdict",
    "apply_readiness",
    "auto_readied_today",
    "brakes_from_env",
    "eligibility_pass",
    "eligible_from_file",
    "ensure_labels",
    "halted",
    "issue_record",
    "load_verdicts",
    "wip_waiting_on_james",
]
