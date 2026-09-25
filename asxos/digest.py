"""The daily digest, model-free — AGENTS.md §12 as a job, not a judgement.

Every line here is derived from `gh api` and the checkout: merged PRs and their class
from the search API and the PR body, applied migrations from the canonical
`Applied: <version> · backup run <id>` line (§8) plus `migration-drift`'s last run,
decisions from `docs/product/decision-log.md` rows dated in the window, readied and
declined issues from the Layer 1/2 markers (§8a), what waits on James from labels and
paths, incidents from open `incident` issues and red scheduled runs. Every figure cites a
PR, run, issue or backlog id — an unsourced number is omitted, not guessed (§7).

`Risks` is the one line this module does not write: it is arbi's judgement and the
steward Routine appends it under this comment afterwards. The comment carries a marker,
`<!-- asxos-digest: v1 date=… run=… main=… -->`, so a re-run the same day updates the
comment rather than posting a second one, and the next day's window starts where the
last digest stopped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Final, Protocol

from asxos.autoready import WAITING_ON_JAMES_LABELS, WAITING_ON_JAMES_PATH
from asxos.backlog import click_list
from asxos.backlog import load as load_backlog
from asxos.domain.governance.github_commands import IssueComment
from asxos.domain.governance.issue_eligibility import (
    parse_eligibility_marker,
    parse_readiness_marker,
)
from asxos.secondbrain.contradictions import SCHEDULED_LANES

DIGEST_ISSUE_DEFAULT: Final[int] = 271
DECISION_LOG: Final[str] = "docs/product/decision-log.md"
BACKLOG: Final[str] = "docs/product/backlog.yaml"
SIGNATURE: Final[str] = "— arbi (`asxos/digest.py`, model-free; `Risks` is appended by the steward)"
RED_CONCLUSIONS: Final[frozenset[str]] = frozenset({"failure", "cancelled", "timed_out"})
YOURS_BACKLOG_CAP: Final[int] = 10

_DIGEST_MARKER_RE: Final[re.Pattern[str]] = re.compile(
    r"<!-- asxos-digest: v1 date=(?P<date>\d{4}-\d{2}-\d{2}) run=(?P<run>\S+) main=(?P<main>[0-9a-f]{7,40}) -->"
)
_CLASS_RE: Final[re.Pattern[str]] = re.compile(
    r"\bClass:\s*\**\s*(?P<cls>Green|Amber|Red)\b", re.IGNORECASE
)
_REVERSAL_RE: Final[re.Pattern[str]] = re.compile(
    r"\*{0,2}Reversal\*{0,2}:?\*{0,2}\s*(?P<text>[^\n|]+)", re.IGNORECASE
)
_APPLIED_RE: Final[re.Pattern[str]] = re.compile(
    r"Applied:\s*`?(?P<version>\d{14})`?\s*·\s*backup run\s*`?(?P<run>\d+)`?"
)
_DECISION_RE: Final[re.Pattern[str]] = re.compile(r"^DECISION:\s*(?P<text>.+)$", re.MULTILINE)
_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\| (?P<date>\d{4}-\d{2}-\d{2}) \| (?P<title>[^|]+) \|"
)
#: What counts as a citation (§7): a PR/issue number, a run id, a backlog id, a migration
#: version, or a decision-log row named in §8a's provenance form ``decision-log:<date>``.
#: A bare date is not one — the first dry run of the lane (run 36200780986) refused every
#: ``Decided`` line for exactly that reason.
_CITES_RE: Final[re.Pattern[str]] = re.compile(
    r"#\d+|\brun \d+|\b[A-E]-\d+[a-z]?\b|\b\d{14}\b|\bdecision-log:\d{4}-\d{2}-\d{2}\b"
)


class DigestAPI(Protocol):
    def search_issues(self, query: str) -> list[dict[str, Any]]: ...
    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]: ...
    def comments(self, number: int) -> list[IssueComment]: ...
    def post_comment(self, number: int, body: str) -> int: ...
    def update_comment(self, comment_id: int, body: str) -> None: ...
    def list_pulls(self, *, state: str = "open") -> list[dict[str, Any]]: ...
    def pull_files(self, number: int) -> list[dict[str, Any]]: ...
    def workflow_runs(
        self, workflow_file: str, *, created_since: str | None = None, event: str | None = None
    ) -> list[dict[str, Any]]: ...


# --- marker ------------------------------------------------------------------------------


@dataclass(frozen=True)
class DigestMarker:
    date: str
    run_id: str
    main: str


def digest_marker(*, date: str, run_id: str, main: str) -> str:
    return f"<!-- asxos-digest: v1 date={date} run={run_id} main={main} -->"


def parse_digest_marker(text: str) -> DigestMarker | None:
    m = _DIGEST_MARKER_RE.search(text)
    if m is None:
        return None
    return DigestMarker(date=m.group("date"), run_id=m.group("run"), main=m.group("main"))


def latest_digest(comments: Iterable[IssueComment]) -> tuple[IssueComment, DigestMarker] | None:
    found: tuple[IssueComment, DigestMarker] | None = None
    for comment in comments:
        marker = parse_digest_marker(comment.body)
        if marker is not None:
            found = (comment, marker)
    return found


# --- sections ----------------------------------------------------------------------------


def _title(raw: dict[str, Any]) -> str:
    return str(raw.get("title") or "").strip()


def _class_of(body: str) -> str:
    m = _CLASS_RE.search(body)
    return m.group("cls").capitalize() if m else "unclassed"


def _reversal_of(body: str) -> str | None:
    m = _REVERSAL_RE.search(body)
    return m.group("text").strip() if m else None


def merged_prs(client: DigestAPI, *, slug: str, since: str) -> list[dict[str, Any]]:
    return client.search_issues(f"repo:{slug} is:pr is:merged merged:>={since}")


def merged_lines(prs: Iterable[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for pr in sorted(prs, key=lambda p: int(p["number"])):
        body = str(pr.get("body") or "")
        cls = _class_of(body)
        line = f"#{pr['number']} ({cls}) {_title(pr)}"
        if cls == "Amber":
            reversal = _reversal_of(body)
            line += f" — reversal: {reversal}" if reversal else " — reversal: not stated"
        out.append(line)
    return out


def applied_lines(client: DigestAPI, prs: Iterable[dict[str, Any]], *, since: str) -> list[str]:
    out: list[str] = []
    for pr in sorted(prs, key=lambda p: int(p["number"])):
        for m in _APPLIED_RE.finditer(str(pr.get("body") or "")):
            out.append(f"{m.group('version')} · backup run {m.group('run')} (#{pr['number']})")
    runs = client.workflow_runs("migration-drift.yml", created_since=since)
    if runs:
        newest = max(runs, key=lambda r: int(r.get("id", 0)))
        out.append(
            f"migration-drift run {newest['id']}: {newest.get('conclusion') or 'in progress'}"
        )
    return out


def decided_rows(decision_log: Path, *, since: str) -> list[str]:
    if not decision_log.is_file():
        return []
    out: list[str] = []
    for line in decision_log.read_text(encoding="utf-8").splitlines():
        m = _ROW_RE.match(line)
        if m and m.group("date") >= since:
            title = m.group("title").strip().strip("*").strip()
            out.append(f"decision-log:{m.group('date')} — {title[:140]}")
    return out


def decision_lines_from_prs(prs: Iterable[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for pr in sorted(prs, key=lambda p: int(p["number"])):
        for m in _DECISION_RE.finditer(str(pr.get("body") or "")):
            out.append(f"#{pr['number']}: {m.group('text').strip()[:140]}")
    return out


def readiness_lines(
    client: DigestAPI, *, slug: str, since: str
) -> tuple[list[str], list[str], list[str]]:
    """(readied, declined, stripped) from the §8a markers on issues updated in the window."""
    readied: list[str] = []
    declined: list[str] = []
    stripped: list[str] = []
    for issue in client.search_issues(f"repo:{slug} is:issue updated:>={since}"):
        number = int(issue["number"])
        for comment in client.comments(number):
            marker = parse_readiness_marker(comment.body)
            if marker is not None and marker.date >= since:
                readied.append(f"#{number} ({marker.cls}) {_title(issue)} — run {marker.run_id}")
                continue
            elig = parse_eligibility_marker(comment.body)
            if elig is None:
                continue
            if elig.rule == "readiness-declined":
                declined.append(f"#{number} {_title(issue)} — run {elig.run_id}")
            elif elig.verdict == "stripped":
                stripped.append(f"#{number} `{elig.rule}` — run {elig.run_id}")
    return readied, declined, stripped


def prs_waiting_on_james(client: DigestAPI) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pull in client.list_pulls(state="open"):
        labels = {str(label.get("name", "")) for label in pull.get("labels") or []}
        if labels & WAITING_ON_JAMES_LABELS:
            out.append(pull)
            continue
        files = client.pull_files(int(pull["number"]))
        if any(str(f.get("filename", "")).startswith(WAITING_ON_JAMES_PATH) for f in files):
            out.append(pull)
    return out


def yours_lines(client: DigestAPI, *, backlog: Path) -> list[str]:
    out = [f"#{i['number']} {_title(i)}" for i in client.list_issues(labels=("needs-human",))]
    out += [f"PR #{p['number']} {_title(p)}" for p in prs_waiting_on_james(client)]
    if backlog.is_file():
        for item in click_list(load_backlog(backlog))[:YOURS_BACKLOG_CAP]:
            out.append(f"backlog {item.id} — {item.title[:120]}")
    return out


def incident_lines(client: DigestAPI, *, since: str) -> list[str]:
    out = [f"#{i['number']} {_title(i)}" for i in client.list_issues(labels=("incident",))]
    for lane in SCHEDULED_LANES:
        for run in client.workflow_runs(f"{lane}.yml", created_since=since, event="schedule"):
            if str(run.get("conclusion") or "") in RED_CONCLUSIONS:
                out.append(f"{lane} run {run['id']}: {run['conclusion']}")
    return out


# --- the digest --------------------------------------------------------------------------


@dataclass
class Digest:
    date: str
    since: str
    merged: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    decided: list[str] = field(default_factory=list)
    readied: list[str] = field(default_factory=list)
    declined: list[str] = field(default_factory=list)
    stripped: list[str] = field(default_factory=list)
    yours: list[str] = field(default_factory=list)
    incidents: list[str] = field(default_factory=list)

    def render(self, *, run_id: str, main: str) -> str:
        def section(name: str, items: Sequence[str], empty: str) -> str:
            if not items:
                return f"**{name}** {empty}"
            return f"**{name}**\n" + "\n".join(f"- {item}" for item in items)

        declined = self.declined + [f"stripped {s}" for s in self.stripped]
        parts = [
            digest_marker(date=self.date, run_id=run_id, main=main),
            f"## {self.date}",
            f"_window since {self.since} · main `{main}` · run {run_id}_",
            section("Merged", self.merged, "none"),
            section("Applied", self.applied, "none"),
            section("Decided", self.decided, "none"),
            section("Readied", self.readied, "none"),
            section("Declined", declined, "none"),
            section("Yours", self.yours, "nothing"),
            "**Risks** pending — nightly-steward appends",
            section("Incidents", self.incidents, "none"),
            "",
            SIGNATURE,
        ]
        return "\n\n".join(parts)


def window_start(previous: DigestMarker | None, *, today: date) -> str:
    return previous.date if previous else (today - timedelta(days=1)).isoformat()


def build(
    client: DigestAPI,
    *,
    slug: str,
    today: date,
    previous: DigestMarker | None,
    repo_root: Path,
) -> Digest:
    since = window_start(previous, today=today)
    prs = merged_prs(client, slug=slug, since=since)
    readied, declined, stripped = readiness_lines(client, slug=slug, since=since)
    return Digest(
        date=today.isoformat(),
        since=since,
        merged=merged_lines(prs),
        applied=applied_lines(client, prs, since=since),
        decided=decided_rows(repo_root / DECISION_LOG, since=since) + decision_lines_from_prs(prs),
        readied=readied,
        declined=declined,
        stripped=stripped,
        yours=yours_lines(client, backlog=repo_root / BACKLOG),
        incidents=incident_lines(client, since=since),
    )


def uncited_lines(rendered: str) -> list[str]:
    """Item lines that cite no PR, run, issue, backlog id or migration version — §7's rule."""
    return [
        line
        for line in rendered.splitlines()
        if line.startswith("- ") and not _CITES_RE.search(line)
    ]


def publish(
    client: DigestAPI,
    *,
    issue_number: int,
    digest: Digest,
    run_id: str,
    main: str,
    existing: tuple[IssueComment, DigestMarker] | None,
) -> str:
    """Update today's comment if one exists, else post. Returns ``updated`` or ``posted``."""
    body = digest.render(run_id=run_id, main=main)
    if existing is not None and existing[1].date == digest.date:
        client.update_comment(existing[0].comment_id, body)
        return "updated"
    client.post_comment(issue_number, body)
    return "posted"
