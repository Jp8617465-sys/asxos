"""Layer 1 of the build loop — asxos/domain/governance/issue_eligibility.py and provenance.py.

The five acceptance tests rev 2 named are here by name: a stranger-authored issue never
reaches `ready`, a reserved label never does, an arbi-authored issue without provenance is
ineligible, an edit changes the body hash the strip rule keys on, and (in
tests/test_autoready.py) `AUTO_READY` off blocks everything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from asxos.domain.governance import issue_eligibility as el
from asxos.domain.governance.provenance import RepoProvenance, heading_slug

OWNER = "Jp8617465-sys"
GOOD_FILES = "`asxos/domain/screening/evaluator.py`\n`tests/test_screening_evaluator.py`"


def product_body(
    *,
    tier: str = "L2",
    area: str = "pipeline",
    problem: str = "Screens cannot be trusted because backtests use post-revision prices.",
    files: str = GOOD_FILES,
    acceptance: str = "Given a rule\nWhen it runs\nThen the screen passes",
    out_of_scope: str = "No UI.",
    depends: str | None = None,
    provenance: str | None = None,
    arbi: bool = False,
    drop: str | None = None,
) -> str:
    """A product form as GitHub renders it after submission."""
    sections = [
        ("Approval tier", tier),
        ("Area", area),
        ("Problem / outcome", problem),
        ("Files to touch (expected)", files),
        ("Acceptance criteria (Given/When/Then)", acceptance),
        ("Out of scope", out_of_scope),
    ]
    if depends is not None:
        sections.append(("Depends on", depends))
    if provenance is not None:
        sections.append(("Provenance", provenance))
    sections.append(("Definition of done", "- [ ] `make check` green\n- [ ] PR merged"))
    parts = [el.ISSUE_AUTHOR_MARKER, ""] if arbi else []
    for label, text in sections:
        if label == drop:
            continue
        parts += [f"### {label}", "", text, ""]
    return "\n".join(parts)


def issue(
    body: str, *, author: str = OWNER, labels: tuple[str, ...] = ("type:product",), number: int = 7
) -> el.IssueRecord:
    return el.IssueRecord(
        number=number, author_login=author, labels=frozenset(labels), title="t", body=body
    )


def verdict(
    rec: el.IssueRecord, *, open_issues: tuple[int, ...] = (), resolves: bool = True
) -> el.Verdict:
    return el.evaluate(
        rec, owner_login=OWNER, open_issues=open_issues, resolve_provenance=lambda ref: resolves
    )


# --- the named acceptance tests ---------------------------------------------------------


def test_stranger_authored_is_never_eligible() -> None:
    perfect = product_body()
    v = verdict(issue(perfect, author="stranger", labels=("type:product", "ready")))
    assert v.verdict == "needs-human" and v.rule == "author-not-owner"
    # Case differences in a login are not a different person.
    assert verdict(issue(perfect, author=OWNER.upper())).verdict == "eligible"


@pytest.mark.parametrize("label", sorted(el.RESERVED_LABELS))
def test_reserved_label_is_never_eligible(label: str) -> None:
    v = verdict(issue(product_body(), labels=("type:product", label)))
    assert v.verdict == "needs-human" and v.rule == f"reserved-label:{label}"


def test_arbi_authored_without_provenance_is_ineligible() -> None:
    v = verdict(issue(product_body(arbi=True)))
    assert v.verdict == "needs-info" and v.rule == "provenance-missing"
    v = verdict(issue(product_body(arbi=True, provenance="backlog:E-99")), resolves=False)
    assert v.verdict == "needs-info" and v.rule == "provenance-unresolved:backlog:E-99"
    assert (
        verdict(issue(product_body(arbi=True, provenance="backlog:E-11")), resolves=True).verdict
        == "eligible"
    )


def test_james_authored_needs_no_provenance() -> None:
    assert verdict(issue(product_body()), resolves=False).verdict == "eligible"


def test_edit_after_ready_changes_body_sha() -> None:
    before = el.body_sha(product_body())
    after = el.body_sha(product_body(out_of_scope="No UI, and no email."))
    assert before != after and len(before) == 12
    assert el.body_sha("x\n") == el.body_sha("  x  ")  # surrounding whitespace is not an edit


# --- the rest of the rule table ---------------------------------------------------------


def test_type_label_missing_or_ambiguous_is_needs_info() -> None:
    v = verdict(issue(product_body(), labels=()))
    assert v.verdict == "needs-info" and v.rule == "type-label-missing"
    v = verdict(issue(product_body(), labels=("type:product", "type:research")))
    assert v.rule == "type-label-ambiguous"


def test_required_sections_are_read_from_a_rendered_form() -> None:
    assert verdict(issue(product_body())).verdict == "eligible"
    v = verdict(issue(product_body(drop="Out of scope")))
    assert v.verdict == "needs-info" and v.rule == "section-missing:out-of-scope"
    v = verdict(issue(product_body(problem="_No response_")))
    assert v.rule == "section-unfilled:problem-outcome"
    template = "Given <state>\nWhen <action>\nThen <observable result>"
    v = verdict(issue(product_body(acceptance=template)))
    assert v.rule == "section-unfilled:acceptance-criteria-given-when-then"


def test_required_sections_match_each_form() -> None:
    assert set(el.REQUIRED_SECTIONS) == el.TYPE_LABELS
    assert el.FILES_SECTION in el.REQUIRED_SECTIONS["type:product"]
    assert el.FILES_SECTION in el.REQUIRED_SECTIONS["type:data-infra"]
    assert el.FILES_SECTION not in el.REQUIRED_SECTIONS["type:research"]


def test_unknown_scope_is_a_spike_not_a_build() -> None:
    v = verdict(issue(product_body(files="unknown — spike first")))
    assert v.verdict == "needs-info" and v.rule == "files-unknown"


def test_a_denied_path_routes_to_james_and_a_glob_asks_for_a_literal_path() -> None:
    v = verdict(
        issue(product_body(files="`migrations/0063_sleeves.sql`\n`asxos/domain/sleeves/nav.py`"))
    )
    assert v.verdict == "needs-human" and v.rule == "files-denied:migrations/0063_sleeves.sql"
    v = verdict(issue(product_body(files="asxos/domain/**")))
    assert v.verdict == "needs-info" and v.rule == "files-noncanonical:asxos/domain/**"


def test_files_tokens_are_read_from_prose_and_lists() -> None:
    sections = el.parse_sections(
        product_body(
            files="- `asxos/a.py` (new)\n- tests/test_a.py, and docs/product/x.md\n- the CLI"
        )
    )
    assert el.files_to_touch(sections) == ("asxos/a.py", "tests/test_a.py", "docs/product/x.md")


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("edit `.claude/settings.json`", "claude-dir"),
        ("amend docs/product/north-star.md", "north-star"),
        ("relax ASXOS_PERSONAL_USE for the job", "personal-use"),
        ("read the .env first", "dotenv"),
        ("rotate EODHD_API_KEY", "secret-name"),
        ("paste ARBI_GITHUB_TOKEN", "secret-name"),
    ],
)
def test_naming_a_reserved_surface_routes_to_james(text: str, name: str) -> None:
    v = verdict(issue(product_body(out_of_scope=text)))
    assert v.verdict == "needs-human" and v.rule == f"body-names-reserved-surface:{name}"


@pytest.mark.parametrize("text", ["see .env.example", "set HC_BACKLOG_URL", "the environment"])
def test_near_misses_are_not_reserved_surfaces(text: str) -> None:
    assert verdict(issue(product_body(out_of_scope=text))).verdict == "eligible"


def test_a_reserved_path_in_files_is_caught_as_a_surface_before_the_denied_set() -> None:
    v = verdict(issue(product_body(files="`.claude/hooks/secrets-guard.sh`")))
    assert v.rule == "body-names-reserved-surface:claude-dir"


def test_an_open_dependency_blocks_and_a_closed_one_does_not() -> None:
    body = product_body(depends="#12, #34")
    v = verdict(issue(body), open_issues=(34,))
    assert v.verdict == "needs-info" and v.rule == "depends-open:#34"
    assert verdict(issue(body), open_issues=(99,)).verdict == "eligible"
    assert el.depends_on(el.parse_sections(product_body(depends="none"))) == ()
    assert el.depends_on(el.parse_sections(product_body(depends="_No response_"))) == ()


def test_the_first_failing_rule_is_the_verdict() -> None:
    v = verdict(
        issue(product_body(files="unknown"), author="stranger", labels=("type:product", "hold"))
    )
    assert v.rule == "author-not-owner"
    v = verdict(issue(product_body(files="unknown"), labels=("type:product", "hold")))
    assert v.rule == "reserved-label:hold"


def test_provenance_ref_reads_the_six_forms() -> None:
    for kind, value in [
        ("run", "35793753686"),
        ("decision-log", "2026-09-24"),
        ("backlog", "E-11"),
        ("roadmap", "A-51"),
        ("doc", "docs/product/plan.md#the-shape"),
        ("issue", "#289"),
    ]:
        ref = el.provenance_ref(el.parse_sections(product_body(provenance=f"{kind}: {value}")))
        assert ref == el.ProvenanceRef(kind=kind, value=value) and ref.text == f"{kind}:{value}"  # type: ignore[arg-type]
    assert el.provenance_ref(el.parse_sections(product_body(provenance="my gut"))) is None


# --- markers -----------------------------------------------------------------------------


def test_eligibility_marker_round_trips_inside_prose() -> None:
    marker = el.eligibility_marker(
        verdict="needs-human",
        rule="files-denied:migrations/0063 x.sql",
        issue=7,
        body_sha="a" * 12,
        run_id="123",
    )
    body = f"{marker}\n❌ needs-human — `migrations/…` is outside what a lane may touch\n\n— arbi"
    parsed = el.parse_eligibility_marker(body)
    assert parsed == el.EligibilityMarker(
        "needs-human", "files-denied:migrations/0063_x.sql", 7, "a" * 12, "123"
    )
    ok = el.eligibility_marker(
        verdict="eligible", rule=None, issue=7, body_sha="b" * 12, run_id="r"
    )
    assert el.parse_eligibility_marker(ok).rule is None  # type: ignore[union-attr]
    assert el.parse_eligibility_marker("no marker here") is None


def test_readiness_marker_round_trips_and_carries_the_ruleset_version() -> None:
    marker = el.readiness_marker(
        cls="amber", issue=7, body_sha="c" * 12, run_id="123", date="2026-09-25"
    )
    assert f"rules={el.RULESET_VERSION}" in marker
    parsed = el.parse_readiness_marker(f"{marker}\n- AC testable\n- one PR\n- Amber (workflow)")
    assert parsed == el.ReadinessMarker(
        "amber", el.RULESET_VERSION, 7, "c" * 12, "123", "2026-09-25"
    )
    assert (
        el.parse_readiness_marker(
            el.eligibility_marker(
                verdict="eligible", rule=None, issue=1, body_sha="d" * 12, run_id="1"
            )
        )
        is None
    )


# --- provenance resolvers ---------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/proposals").mkdir(parents=True)
    (tmp_path / "docs/product/decision-log.md").write_text(
        "| date | decision |\n|---|---|\n| 2026-09-24 | **rev 2 adopted** | one revert |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/product/backlog.yaml").write_text(
        "version: 1\nupdated: 2026-09-24\nitems:\n"
        '  - id: E-11\n    title: "x"\n    phase: E\n    owner: arbi\n    status: open\n'
        '    depends_on: []\n    route: build\n    paths: ["asxos/x.py"]\n    source: "t"\n',
        encoding="utf-8",
    )
    (tmp_path / "docs/product/roadmap-state.md").write_text(
        "## Ranked queue\n\n#1 A-51 → #2 E-20\n", encoding="utf-8"
    )
    (tmp_path / "docs/proposals/plan.md").write_text(
        "# Plan\n\n## The shape\n\ntext\n\n### M. The mandate layer — the first PR\n",
        encoding="utf-8",
    )
    return tmp_path


def _ref(kind: str, value: str) -> el.ProvenanceRef:
    return el.ProvenanceRef(kind=kind, value=value)  # type: ignore[arg-type]


def test_provenance_resolves_each_form_against_the_checkout(repo: Path) -> None:
    prov = RepoProvenance(
        root=repo, owner_login=OWNER, parent_author=lambda n: OWNER if n == 289 else "stranger"
    )
    assert prov.resolve(_ref("run", "35793753686")) and not prov.resolve(_ref("run", "abc"))
    assert prov.resolve(_ref("decision-log", "2026-09-24")) and not prov.resolve(
        _ref("decision-log", "2026-09-25")
    )
    assert prov.resolve(_ref("backlog", "E-11")) and not prov.resolve(_ref("backlog", "E-12"))
    assert prov.resolve(_ref("roadmap", "A-51")) and not prov.resolve(_ref("roadmap", "A-5"))
    assert prov.resolve(_ref("doc", "docs/proposals/plan.md#the-shape"))
    assert prov.resolve(_ref("doc", "docs/proposals/plan.md#m-the-mandate-layer-the-first-pr"))
    assert prov.resolve(_ref("doc", "docs/proposals/plan.md")) and not prov.resolve(
        _ref("doc", "docs/proposals/plan.md#nope")
    )
    assert prov.resolve(_ref("issue", "#289")) and not prov.resolve(_ref("issue", "#290"))


def test_provenance_doc_form_stays_inside_the_two_doc_roots(repo: Path) -> None:
    (repo / "AGENTS.md").write_text("# a\n", encoding="utf-8")
    prov = RepoProvenance(root=repo, owner_login=OWNER)
    assert not prov.resolve(_ref("doc", "AGENTS.md"))
    assert not prov.resolve(_ref("doc", "docs/product/../../AGENTS.md"))
    assert not prov.resolve(_ref("doc", "docs/product/missing.md"))
    assert not prov.resolve(_ref("issue", "#289"))  # no parent_author callback → unresolved


def test_heading_slug_matches_github_anchors() -> None:
    assert heading_slug("M. The mandate layer — the first PR") == "m-the-mandate-layer-the-first-pr"
    assert heading_slug("`asx mandate` approve|reject") == "asx-mandate-approvereject"
    assert heading_slug("  Verification (end to end) ") == "verification-end-to-end"
