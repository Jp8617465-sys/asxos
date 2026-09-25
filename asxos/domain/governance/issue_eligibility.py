"""Layer 1 of the build loop — deterministic issue eligibility, no model in the loop.

The repository is public: anyone can open an issue, and the build lane runs with a
PAT. So the question "may this issue reach arbi's judgement at all?" is answered
here, in code, from facts the platform vouches for (author login, labels) and from
the issue body's *structure*, never from what the body argues. The model only ever
sees issues this module has already let through, and it can only narrow from there.

Rules, in order — the first failure is the verdict, so the comment names one rule:

1. ``author-not-owner``            → needs-human   the login is not the repository owner
2. ``reserved-label:<l>``          → needs-human   ``capital`` / ``mandate`` / ``needs-human`` / ``hold``
3. ``type-label-missing``          → needs-info    no ``type:*`` label (the form did not run)
4. ``section-missing|unfilled:<s>`` → needs-info   a required form section is absent or still a template
5. ``body-names-reserved-surface`` → needs-human   ``.claude/``, north-star, the personal-use
                                                   invariant, a bare ``.env``, a secret's name
6. ``files-unknown``               → needs-info    "unknown — spike first" is not a scope
7. ``files-noncanonical:<p>``      → needs-info    a glob or a non-repo path is not an executable grant
8. ``files-denied:<p>``            → needs-human   a path the headless lane may never touch
                                                   (``asxos.backlog``'s denied set — AGENTS.md §2/§8)
9. ``depends-open:#n``             → needs-info    a dependency is still open
10. ``provenance-missing|unresolved`` → needs-info  arbi-authored issues must cite where the work
                                                    came from (six forms, ``provenance_ref``)

Identity, stated once: there is no separate arbi login. arbi's issues, comments and
labels appear as the owner. What distinguishes an arbi-authored issue is
:data:`ISSUE_AUTHOR_MARKER` in its body — and that marker is what makes rule 10
apply, so arbi cannot invent work, approve it, and build it without a citation.

Markers are the audit trail the digest reads. They are HTML comments so the human
line beneath them can say anything; parsing tolerates surrounding text.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Final, Literal

from asxos.backlog import _scope_is_canonical, is_denied_path

RULESET_VERSION: Final[str] = "v1"

TYPE_LABELS: Final[frozenset[str]] = frozenset({"type:product", "type:data-infra", "type:research"})
RESERVED_LABELS: Final[frozenset[str]] = frozenset({"capital", "mandate", "needs-human", "hold"})

#: The ``label:`` of every ``required: true`` field in the matching issue form, verbatim.
#: A checkbox group cannot be required as a whole, so ``Migration ordering`` is not here.
REQUIRED_SECTIONS: Final[Mapping[str, tuple[str, ...]]] = {
    "type:product": (
        "Approval tier",
        "Area",
        "Problem / outcome",
        "Files to touch (expected)",
        "Acceptance criteria (Given/When/Then)",
        "Out of scope",
    ),
    "type:data-infra": (
        "Area",
        "Problem / outcome",
        "Files to touch (expected)",
        "Acceptance criteria (Given/When/Then)",
        "Out of scope",
    ),
    "type:research": (
        "Timebox (hours)",
        "Question",
        "Hypothesis (pre-registered — written BEFORE any data is touched)",
        "Success metric and threshold (decided BEFORE seeing results)",
        "Falsification condition",
    ),
}

FILES_SECTION: Final[str] = "Files to touch (expected)"
DEPENDS_SECTION: Final[str] = "Depends on"
PROVENANCE_SECTION: Final[str] = "Provenance"

#: What an unfilled section looks like after GitHub renders the form: the optional-field
#: placeholder, or the ``value:`` template the acceptance field is pre-filled with.
_UNFILLED_TOKENS: Final[tuple[str, ...]] = (
    "_No response_",
    "<state>",
    "<action>",
    "<observable result>",
)

#: Surfaces an issue body may not name (AGENTS.md §2, §8, §13). Naming one routes the
#: issue to James — it is never a reason to edit the body until it passes.
RESERVED_SURFACE_RE: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("claude-dir", re.compile(r"\.claude/")),
    ("north-star", re.compile(r"north-star", re.IGNORECASE)),
    ("personal-use", re.compile(r"ASXOS_PERSONAL_USE|require_personal_use|s766B")),
    ("dotenv", re.compile(r"(?<![\w.])\.env(?![\w.])")),
    (
        "secret-name",
        re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:KEY|TOKEN|SECRET|PASSWORD|PAT)\b"),
    ),
)

ISSUE_AUTHOR_MARKER: Final[str] = "<!-- asxos-issue: v1 by=arbi -->"

_HEADING_RE: Final[re.Pattern[str]] = re.compile(r"^###\s+(?P<label>.+?)\s*$")
_ISSUE_REF_RE: Final[re.Pattern[str]] = re.compile(r"#(\d+)")
_PROVENANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?P<kind>run|decision-log|backlog|roadmap|doc|issue)\s*:\s*(?P<value>\S+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PATH_STRIP: Final[str] = "`'\"(),;:<>[]"
_PATH_SUFFIXES: Final[tuple[str, ...]] = (
    ".py",
    ".yml",
    ".yaml",
    ".md",
    ".sql",
    ".json",
    ".sh",
    ".toml",
    ".txt",
    ".j2",
    ".html",
)

ProvenanceKind = Literal["run", "decision-log", "backlog", "roadmap", "doc", "issue"]
VerdictKind = Literal["eligible", "needs-info", "needs-human", "stripped"]
ReadinessClass = Literal["green", "amber"]


@dataclass(frozen=True)
class IssueRecord:
    number: int
    author_login: str
    labels: frozenset[str]
    title: str
    body: str


@dataclass(frozen=True)
class Verdict:
    verdict: VerdictKind
    rule: str | None
    detail: str

    @property
    def label(self) -> str | None:
        """The label the verdict maps to; ``eligible`` and ``stripped`` map to themselves."""
        return None if self.verdict == "stripped" else self.verdict


@dataclass(frozen=True)
class ProvenanceRef:
    kind: ProvenanceKind
    value: str

    @property
    def text(self) -> str:
        return f"{self.kind}:{self.value}"


@dataclass(frozen=True)
class EligibilityMarker:
    verdict: VerdictKind
    rule: str | None
    issue: int
    body_sha: str
    run_id: str


@dataclass(frozen=True)
class ReadinessMarker:
    cls: ReadinessClass
    rules: str
    issue: int
    body_sha: str
    run_id: str
    date: str


# --- body parsing --------------------------------------------------------------------


def parse_sections(body: str) -> dict[str, str]:
    """``### <label>`` headings → the text beneath each, as GitHub renders an issue form."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group("label")
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def section_is_filled(text: str) -> bool:
    return bool(text.strip()) and not any(tok in text for tok in _UNFILLED_TOKENS)


def _path_tokens(text: str) -> list[str]:
    """Path-shaped tokens from a free-text section: backticked spans first, then bare words."""
    out: list[str] = []
    for raw in re.findall(r"`([^`]+)`", text) + re.split(r"[\s,]+", re.sub(r"`[^`]*`", " ", text)):
        tok = raw.strip().strip(_PATH_STRIP).strip()
        if not tok or tok.startswith("-"):
            continue
        if "/" in tok or tok.startswith(".") or tok.endswith(_PATH_SUFFIXES):
            if tok not in out:
                out.append(tok)
    return out


def files_to_touch(sections: Mapping[str, str]) -> tuple[str, ...] | None:
    """The declared scope, or None when the issue says it does not know it yet."""
    text = sections.get(FILES_SECTION, "")
    if not section_is_filled(text) or "unknown" in text.lower():
        return None
    return tuple(_path_tokens(text))


def depends_on(sections: Mapping[str, str]) -> tuple[int, ...]:
    text = sections.get(DEPENDS_SECTION, "")
    if not section_is_filled(text) or text.strip().lower() == "none":
        return ()
    return tuple(int(n) for n in _ISSUE_REF_RE.findall(text))


def provenance_ref(sections: Mapping[str, str]) -> ProvenanceRef | None:
    """The first ``<kind>:<value>`` line of the Provenance section, if any."""
    text = sections.get(PROVENANCE_SECTION, "")
    if not section_is_filled(text):
        return None
    m = _PROVENANCE_RE.search(text)
    if m is None:
        return None
    kind = m.group("kind").lower()
    return ProvenanceRef(kind=kind, value=m.group("value"))  # type: ignore[arg-type]


def is_arbi_authored(body: str) -> bool:
    return ISSUE_AUTHOR_MARKER in body


def body_sha(body: str) -> str:
    """Twelve hex characters of the stripped body — enough to notice an edit, short enough
    to sit in a marker."""
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:12]


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


# --- the verdict -----------------------------------------------------------------------


def evaluate(
    issue: IssueRecord,
    *,
    owner_login: str,
    open_issues: Collection[int],
    resolve_provenance: Callable[[ProvenanceRef], bool],
) -> Verdict:
    """Apply the rules in order; the first failure is the verdict.

    ``owner_login`` must come from the repository record (``GitHubClient.owner_login``),
    never from the issue. ``open_issues`` is the set of issue numbers still open, so a
    dependency on a closed issue counts as met. ``resolve_provenance`` answers whether a
    citation points at something real (``provenance.RepoProvenance.resolve``).
    """
    if issue.author_login.lower() != owner_login.lower():
        return Verdict("needs-human", "author-not-owner", f"opened by {issue.author_login!r}")

    for label in sorted(issue.labels & RESERVED_LABELS):
        return Verdict("needs-human", f"reserved-label:{label}", f"carries `{label}`")

    types = sorted(issue.labels & TYPE_LABELS)
    if not types:
        return Verdict("needs-info", "type-label-missing", "no `type:*` label — use an issue form")
    if len(types) > 1:
        return Verdict("needs-info", "type-label-ambiguous", f"more than one type: {types}")
    type_label = types[0]

    sections = parse_sections(issue.body)
    for label in REQUIRED_SECTIONS[type_label]:
        if label not in sections:
            return Verdict("needs-info", f"section-missing:{_slug(label)}", f"no `### {label}`")
        if not section_is_filled(sections[label]):
            return Verdict("needs-info", f"section-unfilled:{_slug(label)}", f"`{label}` is empty")

    for name, pattern in RESERVED_SURFACE_RE:
        m = pattern.search(issue.body)
        if m:
            return Verdict(
                "needs-human",
                f"body-names-reserved-surface:{name}",
                f"names {m.group(0)!r} — James's (AGENTS.md §2/§8/§13)",
            )

    if FILES_SECTION in REQUIRED_SECTIONS[type_label]:
        paths = files_to_touch(sections)
        if paths is None:
            return Verdict("needs-info", "files-unknown", "scope is unknown — spike first")
        for path in paths:
            if not _scope_is_canonical(path):
                return Verdict(
                    "needs-info",
                    f"files-noncanonical:{path}",
                    f"{path!r} is not a literal repo path",
                )
            if is_denied_path(path):
                return Verdict(
                    "needs-human",
                    f"files-denied:{path}",
                    f"{path!r} is outside what a lane may touch",
                )

    open_set = set(open_issues)
    for dep in depends_on(sections):
        if dep in open_set:
            return Verdict("needs-info", f"depends-open:#{dep}", f"#{dep} is still open")

    if is_arbi_authored(issue.body):
        ref = provenance_ref(sections)
        if ref is None:
            return Verdict(
                "needs-info",
                "provenance-missing",
                "arbi-authored: cite run/decision-log/backlog/roadmap/doc/issue",
            )
        if not resolve_provenance(ref):
            return Verdict(
                "needs-info", f"provenance-unresolved:{ref.text}", f"{ref.text} does not resolve"
            )

    return Verdict("eligible", None, "all rules pass")


# --- markers -----------------------------------------------------------------------------

_ELIGIBILITY_MARKER_RE: Final[re.Pattern[str]] = re.compile(
    r"<!-- asxos-eligibility: v1 verdict=(?P<verdict>eligible|needs-info|needs-human|stripped)"
    r" rule=(?P<rule>\S+) issue=(?P<issue>\d+) body_sha=(?P<sha>[0-9a-f]{12}) run=(?P<run>\S+) -->"
)
_READINESS_MARKER_RE: Final[re.Pattern[str]] = re.compile(
    r"<!-- asxos-readiness: v1 class=(?P<cls>green|amber) rules=(?P<rules>\S+)"
    r" issue=(?P<issue>\d+) body_sha=(?P<sha>[0-9a-f]{12}) run=(?P<run>\S+)"
    r" date=(?P<date>\d{4}-\d{2}-\d{2}) -->"
)


def _token(value: str) -> str:
    """Markers are whitespace-delimited; a rule id or run id must not break that."""
    return re.sub(r"\s+", "_", value.strip()) or "none"


def eligibility_marker(
    *, verdict: VerdictKind, rule: str | None, issue: int, body_sha: str, run_id: str
) -> str:
    return (
        f"<!-- asxos-eligibility: v1 verdict={verdict} rule={_token(rule or 'none')}"
        f" issue={issue} body_sha={body_sha} run={_token(run_id)} -->"
    )


def parse_eligibility_marker(text: str) -> EligibilityMarker | None:
    m = _ELIGIBILITY_MARKER_RE.search(text)
    if m is None:
        return None
    rule = m.group("rule")
    return EligibilityMarker(
        verdict=m.group("verdict"),  # type: ignore[arg-type]
        rule=None if rule == "none" else rule,
        issue=int(m.group("issue")),
        body_sha=m.group("sha"),
        run_id=m.group("run"),
    )


def readiness_marker(
    *, cls: ReadinessClass, issue: int, body_sha: str, run_id: str, date: str
) -> str:
    return (
        f"<!-- asxos-readiness: v1 class={cls} rules={RULESET_VERSION} issue={issue}"
        f" body_sha={body_sha} run={_token(run_id)} date={date} -->"
    )


def parse_readiness_marker(text: str) -> ReadinessMarker | None:
    m = _READINESS_MARKER_RE.search(text)
    if m is None:
        return None
    return ReadinessMarker(
        cls=m.group("cls"),  # type: ignore[arg-type]
        rules=m.group("rules"),
        issue=int(m.group("issue")),
        body_sha=m.group("sha"),
        run_id=m.group("run"),
        date=m.group("date"),
    )
