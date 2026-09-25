"""asxos/digest.py — the model-free digest: every line derived, every line cited.

An in-memory GitHub stands in for the API; the decision log and backlog are fixtures.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from asxos import digest as dg
from asxos.domain.governance import issue_eligibility as el
from asxos.domain.governance.github_commands import IssueComment

SLUG = "Jp8617465-sys/asxos"
TODAY = date(2026, 9, 26)


class FakeGitHub:
    def __init__(self) -> None:
        self.searches: dict[str, list[dict[str, Any]]] = {}
        self.issues: list[dict[str, Any]] = []
        self.comment_log: dict[int, list[IssueComment]] = {}
        self.pulls: list[dict[str, Any]] = []
        self.pull_file_map: dict[int, list[str]] = {}
        self.runs: dict[str, list[dict[str, Any]]] = {}
        self.posted: list[tuple[int, str]] = []
        self.updated: list[tuple[int, str]] = []

    def search_issues(self, query: str) -> list[dict[str, Any]]:
        for key, rows in self.searches.items():
            if key in query:
                return rows
        return []

    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]:
        return [
            i
            for i in self.issues
            if set(labels) <= {label["name"] for label in i.get("labels", [])}
        ]

    def comments(self, number: int) -> list[IssueComment]:
        return list(self.comment_log.get(number, []))

    def post_comment(self, number: int, body: str) -> int:
        self.posted.append((number, body))
        return 9000 + len(self.posted)

    def update_comment(self, comment_id: int, body: str) -> None:
        self.updated.append((comment_id, body))

    def list_pulls(self, *, state: str = "open") -> list[dict[str, Any]]:
        return list(self.pulls)

    def pull_files(self, number: int) -> list[dict[str, Any]]:
        return [{"filename": f} for f in self.pull_file_map.get(number, [])]

    def workflow_runs(
        self, workflow_file: str, *, created_since: str | None = None, event: str | None = None
    ) -> list[dict[str, Any]]:
        return list(self.runs.get(workflow_file, []))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/product/decision-log.md").write_text(
        "| date | title | body | status | session |\n|---|---|---|---|---|\n"
        "| 2026-09-24 | **old row** | x | done | s |\n"
        "| 2026-09-26 | **DECISION — Cursor is IDE-only; #367's loosening reverted** | x | **done** | `s` |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/product/backlog.yaml").write_text(
        "version: 1\nitems:\n"
        '  - id: A-20\n    title: "Add secret HC_BACKLOG_URL"\n    phase: A\n    owner: james\n    status: open\n'
        '    depends_on: []\n    route: james\n    paths: []\n    source: "t"\n',
        encoding="utf-8",
    )
    return tmp_path


def _pr(number: int, title: str, body: str) -> dict[str, Any]:
    return {"number": number, "title": title, "body": body}


def _full(repo: Path) -> tuple[FakeGitHub, dg.Digest]:
    gh = FakeGitHub()
    gh.searches["is:pr is:merged"] = [
        _pr(376, "refactor(github): one client", "## Class: Green\n\nOne revert."),
        _pr(
            346,
            "feat(mandate): the mandate layer",
            "**Class: Amber (migration 0062).** x\n\nApplied: 20260926010203 · backup run 36200000001\n\n**Reversal:** forward migration only.\n\nDECISION: apply held for the merge sitting",
        ),
    ]
    gh.searches["is:issue updated:"] = [
        {"number": 7, "title": "Fix the thing"},
        {"number": 8, "title": "Other thing"},
        {"number": 9, "title": "Stale"},
    ]
    gh.comment_log[7] = [
        IssueComment(
            1,
            "x",
            el.readiness_marker(
                cls="green", issue=7, body_sha="a" * 12, run_id="36196000000", date="2026-09-26"
            ),
        )
    ]
    gh.comment_log[8] = [
        IssueComment(
            2,
            "x",
            el.eligibility_marker(
                verdict="needs-info",
                rule="readiness-declined",
                issue=8,
                body_sha="b" * 12,
                run_id="36196000000",
            ),
        )
    ]
    gh.comment_log[9] = [
        IssueComment(
            3,
            "x",
            el.eligibility_marker(
                verdict="stripped",
                rule="ready-actor-not-owner",
                issue=9,
                body_sha="c" * 12,
                run_id="36196000000",
            ),
        )
    ]
    gh.issues = [
        {"number": 353, "title": "A-22 proof 2", "labels": [{"name": "needs-human"}]},
        {"number": 327, "title": "pipeline-health red", "labels": [{"name": "incident"}]},
    ]
    gh.pulls = [
        {"number": 380, "title": "feat(hooks): A-22", "labels": []},
        {"number": 383, "title": "docs(agents)", "labels": []},
        {"number": 387, "title": "docs(routines): steward", "labels": []},
    ]
    gh.pull_file_map = {
        380: [".claude/settings.json"],
        383: ["AGENTS.md"],
        387: ["docs/ops/routines/nightly-steward.md"],
    }
    gh.runs = {
        "migration-drift.yml": [
            {"id": 36200000010, "conclusion": "success"},
            {"id": 36200000005, "conclusion": "failure"},
        ],
        "daily-brief.yml": [
            {"id": 36200000020, "conclusion": "failure"},
            {"id": 36200000021, "conclusion": "success"},
        ],
    }
    built = dg.build(gh, slug=SLUG, today=TODAY, previous=None, repo_root=repo)
    return gh, built


def test_every_section_is_derived_and_cited(repo: Path) -> None:
    _gh, built = _full(repo)
    assert built.since == "2026-09-25"
    assert built.merged == [
        "#346 (Amber) feat(mandate): the mandate layer — reversal: forward migration only.",
        "#376 (Green) refactor(github): one client",
    ]
    assert built.applied == [
        "20260926010203 · backup run 36200000001 (#346)",
        "migration-drift run 36200000010: success",
    ]
    assert built.decided == [
        "2026-09-26 — DECISION — Cursor is IDE-only; #367's loosening reverted",
        "#346: apply held for the merge sitting",
    ]
    assert built.readied == ["#7 (green) Fix the thing — run 36196000000"]
    assert built.declined == ["#8 Other thing — run 36196000000"]
    assert built.stripped == ["#9 `ready-actor-not-owner` — run 36196000000"]
    assert built.yours == [
        "#353 A-22 proof 2",
        "PR #380 feat(hooks): A-22",
        "PR #387 docs(routines): steward",
        "backlog A-20 — Add secret HC_BACKLOG_URL",
    ]
    # A red scheduled run of any lane is an incident — migration-drift's earlier failure included.
    assert built.incidents == [
        "#327 pipeline-health red",
        "daily-brief run 36200000020: failure",
        "migration-drift run 36200000005: failure",
    ]
    rendered = built.render(run_id="r1", main="58f85ec")
    assert dg.uncited_lines(rendered) == []
    assert rendered.startswith(dg.digest_marker(date="2026-09-26", run_id="r1", main="58f85ec"))
    assert "**Risks** pending — nightly-steward appends" in rendered
    assert "- stripped #9 `ready-actor-not-owner` — run 36196000000" in rendered


def test_empty_window_renders_none_and_nothing(repo: Path) -> None:
    gh = FakeGitHub()
    built = dg.build(gh, slug=SLUG, today=TODAY, previous=None, repo_root=repo)
    rendered = built.render(run_id="r", main="abc1234")
    assert "**Merged** none" in rendered and "**Yours**\n- backlog A-20" in rendered
    assert "**Incidents** none" in rendered and dg.uncited_lines(rendered) == []


def test_window_starts_at_the_previous_digest_and_marker_round_trips() -> None:
    previous = dg.parse_digest_marker(
        dg.digest_marker(date="2026-09-24", run_id="r0", main="abc1234")
    )
    assert previous == dg.DigestMarker("2026-09-24", "r0", "abc1234")
    assert dg.window_start(previous, today=TODAY) == "2026-09-24"
    assert dg.window_start(None, today=TODAY) == "2026-09-25"
    comments = [
        IssueComment(1, "x", "hello"),
        IssueComment(
            2,
            "x",
            f"{dg.digest_marker(date='2026-09-25', run_id='r1', main='abc1234')}\n## 2026-09-25",
        ),
    ]
    found = dg.latest_digest(comments)
    assert found is not None and found[0].comment_id == 2 and found[1].date == "2026-09-25"


def test_publish_updates_todays_comment_and_posts_otherwise(repo: Path) -> None:
    gh, built = _full(repo)
    todays = (IssueComment(42, "x", "old"), dg.DigestMarker("2026-09-26", "r0", "abc1234"))
    assert (
        dg.publish(gh, issue_number=271, digest=built, run_id="r1", main="abc1234", existing=todays)
        == "updated"
    )
    assert gh.updated[0][0] == 42 and gh.posted == []
    yesterdays = (IssueComment(41, "x", "old"), dg.DigestMarker("2026-09-25", "r0", "abc1234"))
    assert (
        dg.publish(
            gh, issue_number=271, digest=built, run_id="r1", main="abc1234", existing=yesterdays
        )
        == "posted"
    )
    assert gh.posted[0][0] == 271 and "## 2026-09-26" in gh.posted[0][1]


def test_class_and_reversal_parsing_tolerates_the_bodies_arbi_writes() -> None:
    assert dg.merged_lines([_pr(1, "t", "## Class: Green\n\nOne revert.")]) == ["#1 (Green) t"]
    assert dg.merged_lines(
        [_pr(2, "t", "**Class: Amber (workflow).** x\n\nREVERSAL: one revert, no data.")]
    ) == ["#2 (Amber) t — reversal: one revert, no data."]
    assert dg.merged_lines([_pr(3, "t", "Class: Amber")]) == ["#3 (Amber) t — reversal: not stated"]
    assert dg.merged_lines([_pr(4, "t", "no class here")]) == ["#4 (unclassed) t"]


def test_uncited_lines_catches_a_bare_claim() -> None:
    rendered = "**Merged**\n- something happened\n- #12 fine\n\n**Yours** nothing"
    assert dg.uncited_lines(rendered) == ["- something happened"]
