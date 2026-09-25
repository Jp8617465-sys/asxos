"""asxos/backlog_issues.py — Layer 4: who applied `ready`, to what, and does it still pass.

The picker trusts no label by itself. Every strip rule is exercised here, then ranking,
overlap, hold, and the report shape the lane reads.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from asxos import backlog_issues as bi
from asxos.domain.governance import issue_eligibility as el
from asxos.domain.governance.github_commands import IssueComment

OWNER = "Jp8617465-sys"
RUN = "36196000001"


def product_body(
    *,
    files: str = "`asxos/domain/screening/evaluator.py`",
    depends: str | None = None,
    out_of_scope: str = "No UI.",
) -> str:
    sections = [
        ("Approval tier", "L2"),
        ("Area", "pipeline"),
        (
            "Problem / outcome",
            "Screens cannot be trusted because backtests use post-revision prices.",
        ),
        ("Files to touch (expected)", files),
        (
            "Acceptance criteria (Given/When/Then)",
            "Given a rule\nWhen it runs\nThen the screen passes",
        ),
        ("Out of scope", out_of_scope),
    ]
    if depends is not None:
        sections.append(("Depends on", depends))
    parts: list[str] = []
    for label, text in sections:
        parts += [f"### {label}", "", text, ""]
    return "\n".join(parts)


class FakeGitHub:
    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comment_log: dict[int, list[IssueComment]] = {}
        self.timelines: dict[int, list[dict[str, Any]]] = {}
        self.writes: list[tuple[str, Any]] = []
        self._next = 500

    def add(
        self,
        number: int,
        body: str,
        *,
        labels: Iterable[str] = ("type:product", "ready"),
        author: str = OWNER,
        ready_by: str | None = OWNER,
        title: str = "t",
    ) -> None:
        self.issues[number] = {
            "number": number,
            "user": {"login": author},
            "labels": [{"name": n} for n in labels],
            "title": title,
            "body": body,
        }
        self.comment_log.setdefault(number, [])
        self.timelines[number] = (
            []
            if ready_by is None
            else [{"event": "labeled", "label": {"name": "ready"}, "actor": {"login": ready_by}}]
        )

    def readied(self, number: int, *, cls: str = "green", sha: str | None = None) -> None:
        sha = sha or el.body_sha(self.issues[number]["body"])
        self._next += 1
        self.comment_log[number].append(
            IssueComment(
                self._next,
                OWNER,
                el.readiness_marker(
                    cls=cls, issue=number, body_sha=sha, run_id="r", date="2026-09-25"
                ),
            )
        )  # type: ignore[arg-type]

    def labels_of(self, number: int) -> set[str]:
        return {label["name"] for label in self.issues[number]["labels"]}

    # PickerAPI
    def owner_login(self) -> str:
        return OWNER

    def issue(self, number: int) -> dict[str, Any]:
        return self.issues[number]

    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]:
        return [
            i
            for i in self.issues.values()
            if set(labels) <= {label["name"] for label in i["labels"]}
        ]

    def comments(self, number: int) -> list[IssueComment]:
        return list(self.comment_log.get(number, []))

    def timeline(self, number: int) -> list[dict[str, Any]]:
        return list(self.timelines.get(number, []))

    def post_comment(self, number: int, body: str) -> int:
        self.writes.append(("post_comment", number))
        self._next += 1
        self.comment_log[number].append(IssueComment(self._next, OWNER, body))
        return self._next

    def remove_label(self, number: int, label: str) -> None:
        self.writes.append(("remove_label", (number, label)))
        self.issues[number]["labels"] = [
            x for x in self.issues[number]["labels"] if x["name"] != label
        ]


def _run(gh: FakeGitHub, tmp_path: Path, *, max_items: int = 1) -> dict[str, Any]:
    (tmp_path / "docs/product").mkdir(parents=True, exist_ok=True)
    return bi.run(gh, repo_root=tmp_path, max_items=max_items, run_id=RUN)


def _stripped_rules(gh: FakeGitHub, number: int) -> list[str]:
    return [
        m.rule
        for c in gh.comments(number)
        if (m := el.parse_eligibility_marker(c.body)) and m.verdict == "stripped"
    ]


# --- the strip rules -------------------------------------------------------------------


def test_ready_applied_by_non_owner_actor_is_stripped(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, product_body(), ready_by="cursor[bot]")
    report = _run(gh, tmp_path)
    assert report["picked"] == [] and report["stripped"] == [
        {"number": 7, "rule": "ready-actor-not-owner"}
    ]
    assert "ready" not in gh.labels_of(7) and _stripped_rules(gh, 7) == ["ready-actor-not-owner"]


def test_ready_with_no_labeled_event_is_stripped(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, product_body(), ready_by=None)
    assert _run(gh, tmp_path)["stripped"] == [{"number": 7, "rule": "ready-actor-unknown"}]


def test_edit_after_ready_strips_at_pickup(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, product_body(out_of_scope="No UI, no email."))
    gh.readied(7, sha=el.body_sha(product_body()))  # arbi readied the old body
    assert _run(gh, tmp_path)["stripped"] == [{"number": 7, "rule": "edited-after-ready"}]


def test_eligibility_reruns_at_pickup(tmp_path: Path) -> None:
    """A dependency that was closed when readied has been reopened since."""
    gh = FakeGitHub()
    gh.add(7, product_body(depends="#3"))
    gh.readied(7)
    gh.add(3, product_body(), labels=("type:product",), ready_by=None)
    report = _run(gh, tmp_path)
    assert report["stripped"] == [{"number": 7, "rule": "eligibility-failed:depends-open:#3"}]
    gh2 = FakeGitHub()
    gh2.add(7, product_body(), labels=("type:product", "ready", "hold"))
    assert _run(gh2, tmp_path)["held"] == [7]


# --- ranking, overlap, buildability ---------------------------------------------------


def test_hand_readied_by_james_ranks_first_then_green_then_amber_then_dependents(
    tmp_path: Path,
) -> None:
    gh = FakeGitHub()
    gh.add(10, product_body(files="`asxos/a.py`"))
    gh.readied(10, cls="amber")
    gh.add(11, product_body(files="`asxos/b.py`"))
    gh.readied(11, cls="green")
    gh.add(12, product_body(files="`asxos/c.py`"))  # James by hand: no marker
    gh.add(13, product_body(files="`asxos/d.py`"))
    gh.readied(13, cls="green")
    gh.add(
        20,
        product_body(files="`asxos/e.py`", depends="#13"),
        labels=("type:product",),
        ready_by=None,
    )
    report = _run(gh, tmp_path, max_items=3)
    assert [p["number"] for p in report["picked"]] == [12, 13, 11]
    assert [p["class"] for p in report["picked"]] == ["james", "green", "green"]
    assert report["picked"][1]["open_dependents"] == 1
    assert report["eligible"] == 4 and report["skipped_overlap"] == []


def test_overlap_skips_later_pick_and_max_is_honoured(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, product_body(files="`asxos/domain/screening/`"))
    gh.add(8, product_body(files="`asxos/domain/screening/evaluator.py`"))
    gh.add(9, product_body(files="`jobs/x.py`"))
    report = _run(gh, tmp_path, max_items=2)
    assert [p["number"] for p in report["picked"]] == [7, 9] and report["skipped_overlap"] == [8]
    assert [p["number"] for p in _run(gh, tmp_path, max_items=1)["picked"]] == [7]


def test_research_is_never_buildable_and_data_infra_hits_the_denied_set(tmp_path: Path) -> None:
    gh = FakeGitHub()
    research = "### Timebox (hours)\n\n4\n\n### Question\n\nq\n\n### Hypothesis (pre-registered — written BEFORE any data is touched)\n\nh\n\n### Success metric and threshold (decided BEFORE seeing results)\n\ns\n\n### Falsification condition\n\nf\n"
    gh.add(7, research, labels=("type:research", "ready"))
    gh.add(8, product_body(files="`migrations/0063_x.sql`"), labels=("type:data-infra", "ready"))
    report = _run(gh, tmp_path, max_items=3)
    assert report["picked"] == []
    assert report["stripped"] == [
        {"number": 8, "rule": "eligibility-failed:files-denied:migrations/0063_x.sql"}
    ]
    assert "ready" in gh.labels_of(7)  # research passes Layer 1 but is attended, not built


def test_report_shape_and_branch_name(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, product_body(), title="Fix the thing")
    with patch.object(bi, "today", lambda: date(2026, 9, 26)):
        report = _run(gh, tmp_path)
    (picked,) = report["picked"]
    assert picked == {
        "number": 7,
        "title": "Fix the thing",
        "body_sha": el.body_sha(product_body()),
        "paths": ["asxos/domain/screening/evaluator.py"],
        "class": "james",
        "depends_on": [],
        "open_dependents": 0,
        "branch": "claude/issue-7-20260926",
    }
    assert report["generated"] == "2026-09-26" and report["ready"] == 1
    json.dumps(report)


def test_main_validates_max_and_exits_3_when_nothing_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert bi.main(["--max", "4"]) == 2
    monkeypatch.setenv("GH_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "Jp8617465-sys/asxos")
    gh = FakeGitHub()
    with patch("asxos.github_api.GitHubClient", lambda **kw: gh):
        rc = bi.main(["--max", "1", "--root", str(tmp_path), "--out", str(tmp_path / "pick.json")])
    assert rc == 3
    assert json.loads((tmp_path / "pick.json").read_text(encoding="utf-8"))["picked"] == []
