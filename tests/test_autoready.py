"""asxos/autoready.py — Layers 2–3: the brakes, the eligibility pass, applying verdicts.

Rev 2's fifth acceptance test lives here by name: `test_auto_ready_off_blocks_all`.
Everything runs against an in-memory GitHub, the way the decisions job's tests do.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pytest

from asxos import autoready as ar
from asxos.domain.governance import issue_eligibility as el
from asxos.domain.governance.github_commands import IssueComment

OWNER = "Jp8617465-sys"
RUN = "36196000000"
TODAY = "2026-09-26"


def product_body(
    *,
    files: str = "`asxos/domain/screening/evaluator.py`",
    arbi: bool = False,
    provenance: str | None = None,
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
    if provenance is not None:
        sections.append(("Provenance", provenance))
    parts = [el.ISSUE_AUTHOR_MARKER, ""] if arbi else []
    for label, text in sections:
        parts += [f"### {label}", "", text, ""]
    return "\n".join(parts)


class FakeGitHub:
    """Issues, comments, labels and pulls in memory; every write is recorded."""

    def __init__(self, *, owner: str = OWNER) -> None:
        self._owner = owner
        self.issues: dict[int, dict[str, Any]] = {}
        self.comment_log: dict[int, list[IssueComment]] = {}
        self.pulls: list[dict[str, Any]] = []
        self.pull_file_map: dict[int, list[str]] = {}
        self.label_defs: list[str] = []
        self.writes: list[tuple[str, Any]] = []
        self._next_comment = 100

    # --- fixture builders ---------------------------------------------------------------
    def add_issue(
        self,
        number: int,
        body: str,
        *,
        author: str = OWNER,
        labels: Iterable[str] = ("type:product",),
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

    def add_comment(self, number: int, body: str, *, author: str = OWNER) -> None:
        self._next_comment += 1
        self.comment_log.setdefault(number, []).append(
            IssueComment(comment_id=self._next_comment, author_login=author, body=body)
        )

    def add_pull(
        self, number: int, *, labels: Iterable[str] = (), files: Iterable[str] = ("asxos/x.py",)
    ) -> None:
        self.pulls.append({"number": number, "labels": [{"name": n} for n in labels]})
        self.pull_file_map[number] = list(files)

    def labels_of(self, number: int) -> set[str]:
        return {label["name"] for label in self.issues[number]["labels"]}

    # --- IssuesAPI ---------------------------------------------------------------------------
    def owner_login(self) -> str:
        return self._owner

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

    def post_comment(self, number: int, body: str) -> int:
        self.writes.append(("post_comment", number))
        self.add_comment(number, body)
        return self._next_comment

    def add_labels(self, number: int, labels: Iterable[str]) -> None:
        for name in labels:
            self.writes.append(("add_label", (number, name)))
            if name not in self.labels_of(number):
                self.issues[number]["labels"].append({"name": name})

    def remove_label(self, number: int, label: str) -> None:
        self.writes.append(("remove_label", (number, label)))
        self.issues[number]["labels"] = [
            x for x in self.issues[number]["labels"] if x["name"] != label
        ]

    def labels(self) -> list[dict[str, Any]]:
        return [{"name": n} for n in self.label_defs]

    def create_label(self, name: str, color: str, description: str) -> None:
        self.writes.append(("create_label", name))
        self.label_defs.append(name)

    def list_pulls(self, *, state: str = "open") -> list[dict[str, Any]]:
        return list(self.pulls)

    def pull_files(self, number: int) -> list[dict[str, Any]]:
        return [{"filename": f} for f in self.pull_file_map.get(number, [])]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/product/decision-log.md").write_text(
        "| 2026-09-24 | **rev 2** | x |\n", encoding="utf-8"
    )
    (tmp_path / "docs/product/backlog.yaml").write_text(
        'version: 1\nitems:\n  - id: E-11\n    title: "x"\n    phase: E\n    owner: arbi\n    status: open\n'
        '    depends_on: []\n    route: build\n    paths: ["asxos/x.py"]\n    source: "t"\n',
        encoding="utf-8",
    )
    return tmp_path


def _markers(gh: FakeGitHub, number: int) -> list[Any]:
    return [
        m
        for c in gh.comments(number)
        if (m := el.parse_eligibility_marker(c.body) or el.parse_readiness_marker(c.body))
    ]


# --- brakes --------------------------------------------------------------------------------


def test_auto_ready_off_blocks_all() -> None:
    """Unset, empty, "off", "true" — everything but "on" is off, and off applies nothing."""
    for value in (None, "", "off", "true", "ON "):
        env = {} if value is None else {ar.AUTO_READY_ENV: value}
        brakes = ar.brakes_from_env(env)
        assert brakes.auto_ready is (value == "ON "), value
    gh = FakeGitHub()
    gh.add_issue(7, product_body(), labels=("type:product", "eligible"))
    verdict = ar.ReadinessVerdict(7, "ready", "green", ("AC testable", "one PR", "Green"))
    report = ar.apply_readiness(
        gh,
        verdicts=[verdict],
        eligible={7: el.body_sha(product_body())},
        brakes=ar.Brakes(auto_ready=False),
        run_id=RUN,
        date=TODAY,
    )
    assert report.blocked_by == "AUTO_READY is not on" and report.readied == [] and gh.writes == []


def test_brakes_come_from_env_with_defaults_3_and_2() -> None:
    assert ar.brakes_from_env({ar.AUTO_READY_ENV: "on"}) == ar.Brakes(True, 3, 2)
    assert ar.brakes_from_env(
        {ar.AUTO_READY_ENV: "on", ar.DAILY_CAP_ENV: "5", ar.WIP_LIMIT_ENV: "0"}
    ) == ar.Brakes(True, 5, 0)
    with pytest.raises(RuntimeError, match=ar.DAILY_CAP_ENV):
        ar.brakes_from_env({ar.DAILY_CAP_ENV: "three"})


def test_halt_issue_stops_readiness_by_label_or_title() -> None:
    for labels, title in ((("routines-halt",), "pause"), ((), "HALT: budget")):
        gh = FakeGitHub()
        gh.add_issue(1, "stop", labels=labels, title=title)
        gh.add_issue(7, product_body(), labels=("type:product", "eligible"))
        assert ar.halted(gh)
        verdict = ar.ReadinessVerdict(7, "ready", "green", ("a", "b", "c"))
        report = ar.apply_readiness(
            gh,
            verdicts=[verdict],
            eligible={7: el.body_sha(product_body())},
            brakes=ar.Brakes(True),
            run_id=RUN,
            date=TODAY,
        )
        assert report.blocked_by == "halt" and gh.writes == []


def test_wip_counts_only_prs_waiting_on_james() -> None:
    gh = FakeGitHub()
    gh.add_pull(1)  # an ordinary open PR — arbi merges its own
    gh.add_pull(2, labels=("needs-human",))
    gh.add_pull(3, labels=("hold",))
    gh.add_pull(4, files=(".claude/settings.json", "tests/x.py"))
    gh.add_pull(5, files=("docs/ops/routines/nightly-steward.md",))  # draft-only for arbi
    gh.add_pull(6, files=("docs/ops/README.md",))  # not the routines dir — arbi's to merge
    assert ar.wip_waiting_on_james(gh) == 4


def test_daily_cap_and_wip_limit_refuse_with_the_reason() -> None:
    gh = FakeGitHub()
    body = product_body()
    for n in (7, 8, 9):
        gh.add_issue(n, body, labels=("type:product", "eligible"))
    gh.add_issue(5, body, labels=("type:product", "ready"))
    gh.add_comment(
        5,
        el.readiness_marker(
            cls="green", issue=5, body_sha=el.body_sha(body), run_id="r", date=TODAY
        ),
    )
    assert ar.auto_readied_today(gh, TODAY) == 1
    verdicts = [ar.ReadinessVerdict(n, "ready", "green", ("a", "b", "c")) for n in (7, 8, 9)]
    eligible = {n: el.body_sha(body) for n in (7, 8, 9)}
    report = ar.apply_readiness(
        gh,
        verdicts=verdicts,
        eligible=eligible,
        brakes=ar.Brakes(True, daily_cap=3, wip_limit=2),
        run_id=RUN,
        date=TODAY,
    )
    assert report.readied == [7, 8] and report.refused == {9: "daily cap 3 reached"}

    gh2 = FakeGitHub()
    gh2.add_issue(7, body, labels=("type:product", "eligible"))
    gh2.add_pull(1, labels=("needs-human",))
    gh2.add_pull(2, labels=("hold",))
    report = ar.apply_readiness(
        gh2,
        verdicts=verdicts[:1],
        eligible=eligible,
        brakes=ar.Brakes(True, wip_limit=2),
        run_id=RUN,
        date=TODAY,
    )
    assert report.readied == [] and "WIP limit 2" in report.refused[7]


# --- the eligibility pass ----------------------------------------------------------------


def test_eligibility_pass_labels_markers_and_the_eligible_file(repo: Path, tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add_issue(7, product_body(), labels=("type:product", "needs-triage"))
    gh.add_issue(8, product_body(), author="stranger", labels=("type:product",))
    gh.add_issue(9, product_body(arbi=True, provenance="backlog:E-11"), labels=("type:product",))
    gh.add_issue(10, product_body(arbi=True), labels=("type:product",))
    gh.add_issue(11, "not a form", labels=("bug",))  # no type label, no triage → untouched
    out = tmp_path / ar.ELIGIBLE_FILE
    report = ar.eligibility_pass(gh, run_id=RUN, repo_root=repo, write_to=out)

    assert gh.labels_of(7) == {"type:product", "eligible"}  # needs-triage cleared
    assert gh.labels_of(8) == {"type:product", "needs-human"}
    assert gh.labels_of(9) == {"type:product", "eligible"}
    assert gh.labels_of(10) == {"type:product", "needs-info"}
    assert gh.labels_of(11) == {"bug"} and 11 not in report.verdicts
    assert [m.verdict for m in _markers(gh, 8)] == ["needs-human"]
    assert _markers(gh, 10)[0].rule == "provenance-missing"
    assert report.comments_posted == 4
    written = json.loads(out.read_text(encoding="utf-8"))
    assert [row["number"] for row in written["eligible"]] == [7, 9]
    assert written["eligible"][0]["body_sha"] == el.body_sha(product_body())
    assert written["verdicts"]["8"] == ["needs-human", "author-not-owner"]


def test_rerun_posts_no_duplicate_markers(repo: Path) -> None:
    gh = FakeGitHub()
    gh.add_issue(7, product_body(), labels=("type:product",))
    ar.eligibility_pass(gh, run_id=RUN, repo_root=repo)
    first = len(gh.comments(7))
    second = ar.eligibility_pass(gh, run_id="next-run", repo_root=repo)
    assert len(gh.comments(7)) == first == 1 and second.comments_posted == 0


def test_edit_after_ready_strips_the_label_and_says_so(repo: Path) -> None:
    gh = FakeGitHub()
    old = product_body()
    gh.add_issue(7, product_body(out_of_scope="No UI, no email."), labels=("type:product", "ready"))
    gh.add_comment(
        7,
        el.readiness_marker(
            cls="green", issue=7, body_sha=el.body_sha(old), run_id="r", date=TODAY
        ),
    )
    report = ar.eligibility_pass(gh, run_id=RUN, repo_root=repo)
    assert report.stripped == [7] and "ready" not in gh.labels_of(7)
    stripped = [m for m in _markers(gh, 7) if getattr(m, "verdict", None) == "stripped"]
    assert stripped and stripped[0].rule == "edited-after-ready"
    assert "eligible" in gh.labels_of(7)  # still passes Layer 1; readiness must be re-judged


def test_a_hand_applied_ready_with_no_marker_is_left_alone(repo: Path) -> None:
    """James applied `ready` himself: no readiness marker, so nothing to compare — kept."""
    gh = FakeGitHub()
    gh.add_issue(7, product_body(), labels=("type:product", "ready"))
    report = ar.eligibility_pass(gh, run_id=RUN, repo_root=repo)
    assert report.stripped == [] and "ready" in gh.labels_of(7)
    assert report.eligible[0]["already_ready"] is True


# --- applying verdicts -------------------------------------------------------------------


def test_apply_readiness_readies_and_declines_with_markers() -> None:
    gh = FakeGitHub()
    body = product_body()
    gh.add_issue(7, body, labels=("type:product", "eligible"))
    gh.add_issue(8, body, labels=("type:product", "eligible"))
    verdicts = [
        ar.ReadinessVerdict(
            7, "ready", "amber", ("AC is executable", "one PR", "Amber: workflow edit")
        ),
        ar.ReadinessVerdict(8, "declined", "green", ("AC not testable", "two PRs", "Green")),
    ]
    report = ar.apply_readiness(
        gh,
        verdicts=verdicts,
        eligible={7: el.body_sha(body), 8: el.body_sha(body)},
        brakes=ar.Brakes(True),
        run_id=RUN,
        date=TODAY,
    )
    assert report.readied == [7] and report.declined == [8] and report.refused == {}
    assert gh.labels_of(7) == {"type:product", "ready"}
    assert gh.labels_of(8) == {"type:product", "needs-info"}
    (m7,) = _markers(gh, 7)
    assert m7 == el.ReadinessMarker("amber", el.RULESET_VERSION, 7, el.body_sha(body), RUN, TODAY)
    assert "- AC is executable" in gh.comments(7)[0].body
    (m8,) = _markers(gh, 8)
    assert m8.verdict == "needs-info" and m8.rule == "readiness-declined"


def test_verdict_for_an_issue_outside_the_eligible_set_is_refused() -> None:
    gh = FakeGitHub()
    body = product_body()
    gh.add_issue(7, body, labels=("type:product", "eligible"))
    gh.add_issue(9, body, labels=("type:product",))
    verdicts = [
        ar.ReadinessVerdict(9, "ready", "green", ("a", "b", "c")),
        ar.ReadinessVerdict(7, "ready", "green", ("a", "b", "c")),
    ]
    report = ar.apply_readiness(
        gh,
        verdicts=verdicts,
        eligible={7: "0" * 12},
        brakes=ar.Brakes(True),
        run_id=RUN,
        date=TODAY,
    )
    # 9 was never eligible; 7's sha is from a different body — the agent readied stale text.
    assert report.refused == {9: "not in this run's eligible set"} and report.readied == [7]
    report2 = ar.apply_readiness(
        gh, verdicts=verdicts[:1], eligible={}, brakes=ar.Brakes(True), run_id=RUN, date=TODAY
    )
    assert report2.readied == [] and 9 in report2.refused


def test_load_verdicts_rejects_anything_malformed(tmp_path: Path) -> None:
    path = tmp_path / ar.VERDICTS_FILE
    good = [{"issue": 7, "verdict": "ready", "class": "green", "reasons": ["a", "b", "c"]}]
    path.write_text(json.dumps(good), encoding="utf-8")
    assert ar.load_verdicts(path) == [ar.ReadinessVerdict(7, "ready", "green", ("a", "b", "c"))]
    for bad in (
        {"issue": 7},
        {"issue": "7", "verdict": "ready", "class": "green", "reasons": ["a", "b", "c"]},
        {"issue": 7, "verdict": "ready", "class": "red", "reasons": ["a", "b", "c"]},
        {"issue": 7, "verdict": "ready", "class": "green", "reasons": ["a", "b"]},
        {"issue": 7, "verdict": "maybe", "class": "green", "reasons": ["a", "b", "c"]},
    ):
        path.write_text(json.dumps([bad]), encoding="utf-8")
        with pytest.raises(RuntimeError):
            ar.load_verdicts(path)
    path.write_text(json.dumps({"issue": 7}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected a list"):
        ar.load_verdicts(path)


def test_ensure_labels_creates_only_what_is_missing() -> None:
    gh = FakeGitHub()
    gh.label_defs = ["ready", "bug"]
    created = ar.ensure_labels(gh)
    assert "ready" not in created and set(created) == set(ar.LABELS) - {"ready"}
    assert ar.ensure_labels(gh) == []


def test_eligible_from_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / ar.ELIGIBLE_FILE
    path.write_text(
        json.dumps({"eligible": [{"number": 7, "body_sha": "a" * 12}]}), encoding="utf-8"
    )
    assert ar.eligible_from_file(path) == {7: "a" * 12}
