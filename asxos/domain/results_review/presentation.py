"""End-to-end results-review presentation — mission P2-05 (plan :311).

The last unit of the results-review lane. It runs the whole frozen chain over
one hashed fixture, in memory, and assembles the single thing James is meant
to look at:

    fixture payload + case
        -> `adapter.adapt_hashed_fixture`      (P2-03: verify, revalidate, render)
        -> `challenger.challenge_adapted`      (P2-04: the independent challenge)
        -> `reviewer.review_adapted`           (P2-04: complete | revise | abstain)
        -> this module                         (P2-05: one presented package)

Nothing here is frozen-layer code: `contracts.py`, `fixtures.py`, `adapter.py`,
`gates.py`, `reviewer.py` and `challenger.py` are byte-unmodified by this
mission, and every rule they enforce is re-run, never re-implemented.

**No persistence, ever.** Pure in-memory: no DB, no network, no file write, no
wall-clock read. `present_hashed_fixture` takes `evaluated_at` as a REQUIRED
keyword argument precisely so that no `datetime.now(UTC)` default can hide in
this path; the runnable entry point pins it to the frozen packet's own
`knowledge_cutoff`, following `decision_engine/demo.py`'s `created_at=cutoff`
precedent, so its stdout is byte-stable.

**Not advice.** Nothing here emits a rating, price target, trade, position
size, portfolio instruction, or thesis mutation (plan :303-304; s766B
firewall). The presented verdict is the reviewer's `complete | revise |
abstain` and nothing else, and **abstention is a valid, successful outcome**
(matrix :366-368) — see `ABSTENTION_IS_SUCCESS`.

Two outcomes, kept explicitly apart (`CATEGORY_PRESENTED` /
`CATEGORY_COULD_NOT_BUILD`):

1. **The pipeline ran and the artifact validated.** The verdict is whatever the
   reviewer derived — `complete`, `revise` or `abstain`. An `abstain` here is a
   pre-registered SUCCESS, not a failure.
2. **The packet could not be built.** A payload/record hash mismatch, a failed
   contract validator, or a value this module cannot canonicalise raises
   `ResultsReviewPresentationError`. That is a STOP-and-report defect and is
   **never** written up as an honest review outcome.

Identity: see `PRESENTATION_HASH_IDENTITY_AXIS` for the exact claim, and
`PRESENTATION_NOT_CLAIMED` for what is deliberately NOT claimed.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Final

from asxos.domain.decision_engine.types import ChallengeResult
from asxos.domain.results_review.adapter import AdaptedResultsReview, adapt_hashed_fixture
from asxos.domain.results_review.challenger import challenge_adapted
from asxos.domain.results_review.contracts import ResultsReviewCase
from asxos.domain.results_review.fixtures import (
    abstention_case,
    action_bait_case,
    action_bait_document_payload,
    historical_document_payload,
    historical_results_case,
    injection_case,
    injection_document_payload,
)
from asxos.domain.results_review.reviewer import ReviewerVerdict, review_adapted

PRESENTATION_SCHEMA_VERSION: Final[str] = "results-review-presentation-1.0"


class ResultsReviewPresentationError(RuntimeError):
    """Could-not-build: the packet never became a validated artifact.

    A STOP-and-report defect (CLAUDE.md non-negotiable #10), raised when the
    document payload does not hash to its frozen record, when a frozen contract
    validator rejects the case, or when a field value has no canonical text
    form. **This is not an outcome.** It is categorically distinct from an
    `abstain` verdict, which means the pipeline ran, the artifact validated,
    and the evidence could not support a completed review. Never report an
    exception as an honest review result.
    """

    #: The constraint-7 category this failure belongs to.
    category: Final[str] = "could_not_build"


# ---------------------------------------------------------------------------
# The two outcome categories, kept explicitly distinct
# ---------------------------------------------------------------------------

#: The pipeline ran and the artifact validated; the verdict is the reviewer's.
CATEGORY_PRESENTED: Final[str] = "presented"

#: The packet failed construction or validation — a defect, never an outcome.
CATEGORY_COULD_NOT_BUILD: Final[str] = "could_not_build"

#: Pinned verbatim in the presented package and by the eval suite.
ABSTENTION_IS_SUCCESS: Final[str] = (
    "Abstention is a valid, successful outcome, pre-registered by the packet's "
    "acceptance criteria; it is not a failure and it is not a could-not-build."
)

#: The one line in the presented package that names the forbidden vocabulary,
#: and it names it only to negate it. The eval suite strips exactly this string
#: before asserting that no authored prose carries any of those words — so the
#: disclaimer cannot become the loophole it exists to close.
NO_ADVICE_DISCLAIMER: Final[str] = (
    "Analysis only. No rating, price target, trade, position size, portfolio "
    "instruction, or thesis mutation appears anywhere in this package."
)

# ---------------------------------------------------------------------------
# Hash identity — the claim, and the limits of the claim
# ---------------------------------------------------------------------------

#: THE identity axis, in one sentence. Everything the eval suite pins is a
#: consequence of this sentence, and nothing broader is asserted anywhere.
PRESENTATION_HASH_IDENTITY_AXIS: Final[str] = (
    "The presentation digest is byte-identical across independent processes on one "
    "interpreter version, given an explicitly injected evaluated_at, because every "
    "presented value is first reduced to a single canonical text form — normalised "
    "fixed-point Decimal text, explicit-UTC timestamps, sorted mapping keys, "
    "ASCII-escaped compact JSON — which makes it invariant to LC_ALL, to "
    "PYTHONHASHSEED, to input key order, and to value-equal but text-different "
    "Decimal spellings."
)

#: Stated plainly so nobody reads more into the digest than it carries.
PRESENTATION_NOT_CLAIMED: Final[tuple[str, ...]] = (
    "NOT claimed: byte identity across Python versions. A different CPython "
    "release may change Decimal, json, or pydantic serialisation behaviour; the "
    "pinned digests are valid for one interpreter version at a time.",
    "NOT claimed: byte identity across platforms or architectures. Only "
    "same-interpreter, independent-process identity is instrumented.",
    "NOT claimed: text-form invariance of the FROZEN layer's own fingerprints. "
    "`AdaptedResultsReview.artifact_sha256` and `.case_sha256` hash pydantic's "
    "JSON render, which preserves a Decimal's written exponent, so a value-equal "
    "but text-different Decimal changes them. The presentation digest normalises "
    "first and does not change; both are reported side by side.",
    "NOT claimed: that the digest proves the frozen content seals. The "
    "presentation payload omits every `content_hash` field (it is text-form "
    "sensitive for the same reason); the seals are checked by the frozen "
    "`integrity_seal` gate, whose result travels inside the hashed payload.",
    "NOT claimed: anything about persistence. Nothing here is written to disk, "
    "and no digest is a storage key.",
)

#: The seal field omitted from the canonical presentation payload (see above).
CONTENT_SEAL_FIELD: Final[str] = "content_hash"


# ---------------------------------------------------------------------------
# Canonicalisation — one text form per value
# ---------------------------------------------------------------------------


def canonical_decimal_text(value: Decimal) -> str:
    """The one text form of a Decimal value (the hazard-2 normalisation).

    ``Decimal("0")``, ``Decimal("0.000000")`` and ``Decimal("0E-6")`` are one
    value written three ways, and pydantic's JSON render preserves the written
    exponent — so without this normalisation the same figure hashes three ways.
    Here every value-equal Decimal produces one string: trailing fractional
    zeros are dropped, exponent notation is expanded to fixed point, and signed
    zero collapses to ``"0"``. A non-finite Decimal has no canonical form and
    hard-fails rather than rendering ``NaN`` into a digest.
    """
    if not value.is_finite():
        raise ResultsReviewPresentationError(
            "a non-finite Decimal has no canonical text form and cannot be presented"
        )
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def render_utc_timestamp(value: datetime) -> str:
    """Render an instant with an explicit UTC offset, or hard-fail.

    A naive datetime is unrepresentable in a digest whose identity claim
    includes "explicit UTC": there is no way to know what instant it names.
    The frozen contracts already require timezone-aware UTC
    (`decision_engine.types.require_utc`); this is the presentation-side
    restatement, so no naive value can reach the canonical payload through an
    unvalidated path.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResultsReviewPresentationError(
            "a naive datetime cannot be presented; timestamps must carry explicit UTC"
        )
    return value.astimezone(UTC).isoformat()


def canonicalise(value: object) -> object:
    """Reduce one value to its canonical, hashable form (total or hard-fail).

    Drops every `content_hash` field (`CONTENT_SEAL_FIELD`) — see
    `PRESENTATION_NOT_CLAIMED`. Floats and every other unhandled type raise:
    a value this module cannot canonicalise must stop the presentation, not
    slip into a digest under `repr()`.
    """
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, Decimal):
        return canonical_decimal_text(value)
    if isinstance(value, datetime):
        return render_utc_timestamp(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): canonicalise(item)
            for key, item in value.items()
            if str(key) != CONTENT_SEAL_FIELD
        }
    if isinstance(value, list | tuple):
        return [canonicalise(item) for item in value]
    raise ResultsReviewPresentationError(
        f"value of type {type(value).__name__!r} has no canonical presentation form"
    )


def canonical_json(payload: object) -> str:
    """The decision engine's canonical JSON form: sorted, compact, ASCII."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _md_text(value: str) -> str:
    """Neutralise Markdown structure in interpolated text.

    Deliberately mirrors `adapter._md_text` rather than importing a private
    name out of a frozen module. Every string this module interpolates is
    already template-only by the challenger's and gates' own G10 guarantee;
    this is the belt-and-braces second layer.
    """
    return " ".join(value.splitlines()).replace("|", "\\|")


# ---------------------------------------------------------------------------
# The presented package
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PresentedResultsReview:
    """One complete results review, ready to present. Never persisted.

    `presentation_sha256` fingerprints `presentation_json`, the canonical
    payload described by `PRESENTATION_HASH_IDENTITY_AXIS`. The frozen layer's
    own fingerprints travel alongside on `adapted`, unnormalised and
    text-sensitive, so the two can be compared rather than conflated.
    """

    category: str
    case_id: str
    review_id: str
    data_mode: str
    acquisition: str
    evaluated_at: datetime
    adapted: AdaptedResultsReview
    challenge: ChallengeResult
    verdict: ReviewerVerdict
    presentation_json: str
    presentation_sha256: str
    presentation_markdown: str

    @property
    def outcome(self) -> str:
        """The reviewer's verdict: ``complete``, ``revise`` or ``abstain``."""
        return self.verdict.verdict


def _canonical_payload(
    case: ResultsReviewCase, challenge: ChallengeResult, verdict: ReviewerVerdict
) -> object:
    """Assemble the canonical, evaluated_at-free identity payload.

    `evaluated_at` is deliberately absent: it is a presentation stamp, not part
    of what was reviewed, so re-presenting the same frozen case at a different
    wall clock is the same review and must carry the same digest.
    """
    return canonicalise(
        {
            "presentation_schema_version": PRESENTATION_SCHEMA_VERSION,
            "case_id": case.case_id,
            "label": case.label,
            "document": case.document.model_dump(mode="python"),
            "evidence_packet": case.evidence.model_dump(mode="python"),
            "artifact": case.review.model_dump(mode="python"),
            "challenge": challenge.model_dump(mode="python"),
            "verdict": dataclasses.asdict(verdict),
        }
    )


def _provenance_lines(
    case: ResultsReviewCase, presented: Mapping[str, str], evaluated_at: datetime
) -> list[str]:
    return [
        "## Provenance",
        "",
        f"- Case: {_md_text(case.case_id)} — {_md_text(case.label)}",
        (
            f"- Data mode: **{case.review.data_mode}** "
            "(a hashed fixture can never be `real`)"
            if case.document.acquisition == "hashed_fixture"
            else (
                f"- Data mode: **{case.review.data_mode}** "
                "(research-store PIT snapshot; not an ASX announcement)"
            )
        ),
        f"- Acquisition path: {case.document.acquisition}",
        f"- Document: {_md_text(case.document.document_id)} "
        f"(sha256 {case.document.document_sha256})",
        f"- Evidence packet: {_md_text(case.evidence.evidence_packet_id)}",
        f"- Knowledge cutoff: {render_utc_timestamp(case.evidence.knowledge_cutoff)}",
        f"- Evaluated at (injected, not read from a clock): "
        f"{render_utc_timestamp(evaluated_at)}",
        f"- Presentation digest: {presented['presentation_sha256']}",
        f"- Frozen artifact digest: {presented['artifact_sha256']}",
        f"- Frozen case digest: {presented['case_sha256']}",
    ]


def _verdict_lines(verdict: ReviewerVerdict) -> list[str]:
    lines = [
        "## Verdict",
        "",
        f"- Verdict: **{verdict.verdict}**",
        f"- Derived verdict: {verdict.derived_verdict}",
        f"- Challenge ceiling: {verdict.challenge_ceiling or 'none'}",
        f"- Scope: {_md_text(verdict.scope_statement)}",
        f"- {ABSTENTION_IS_SUCCESS}",
    ]
    if verdict.insufficiencies:
        lines += ["", "Insufficiencies recorded:", ""]
        lines += [f"- {_md_text(item)}" for item in verdict.insufficiencies]
    lines += ["", "### Mechanical gates", "", "| Gate | Result | Detail |", "|---|---|---|"]
    for check in verdict.checks:
        result = "pass" if check.passed else "FAIL"
        lines.append(f"| {check.gate} | {result} | {_md_text(check.detail)} |")
    return lines


def _challenge_lines(challenge: ChallengeResult) -> list[str]:
    lines = [
        "## Independent challenge",
        "",
        f"- Challenge outcome: **{challenge.outcome}**",
        f"- Independent of author: {challenge.independent_of_author}",
        "",
        f"Strongest bear case: {_md_text(challenge.strongest_bear_case)}",
    ]
    if challenge.findings:
        lines += ["", "| Severity | Finding | Required response |", "|---|---|---|"]
        for finding in challenge.findings:
            lines.append(
                f"| {finding.severity} | {_md_text(finding.finding)} "
                f"| {_md_text(finding.required_response)} |"
            )
    return lines


def _build_markdown(
    case: ResultsReviewCase,
    challenge: ChallengeResult,
    verdict: ReviewerVerdict,
    adapted: AdaptedResultsReview,
    presentation_sha256: str,
    evaluated_at: datetime,
) -> str:
    digests = {
        "presentation_sha256": presentation_sha256,
        "artifact_sha256": adapted.artifact_sha256,
        "case_sha256": adapted.case_sha256,
    }
    lines: list[str] = [
        f"# Results review presented — {_md_text(case.review.review_id)}",
        "",
        NO_ADVICE_DISCLAIMER,
        "",
        *_provenance_lines(case, digests, evaluated_at),
        "",
        *_verdict_lines(verdict),
        "",
        *_challenge_lines(challenge),
        "",
        "## The artifact",
        "",
        adapted.artifact_markdown.rstrip("\n"),
        "",
        "## Determinism",
        "",
        _md_text(PRESENTATION_HASH_IDENTITY_AXIS),
        "",
    ]
    lines += [f"- {_md_text(item)}" for item in PRESENTATION_NOT_CLAIMED]
    return "\n".join(lines) + "\n"


def present_hashed_fixture(
    payload: Mapping[str, object],
    case: ResultsReviewCase,
    *,
    evaluated_at: datetime,
) -> PresentedResultsReview:
    """Run the frozen chain end to end and assemble one presented review.

    `evaluated_at` is a REQUIRED keyword with no default — there is no
    `datetime.now(UTC)` anywhere on this path, and the presentation digest does
    not depend on it, so the same frozen case presented at any wall clock is
    the same review with the same digest.

    Raises `ResultsReviewPresentationError` (category
    `CATEGORY_COULD_NOT_BUILD`) if the packet cannot be built or validated.
    That failure is a defect to report, never a review outcome.
    """
    render_utc_timestamp(evaluated_at)  # fail before any work on a naive stamp
    try:
        adapted = adapt_hashed_fixture(payload, case)
    except ValueError as exc:  # adapter hard-fail or frozen-contract rejection
        raise ResultsReviewPresentationError(
            f"could not build the results-review packet: {exc}"
        ) from exc
    return present_adapted(adapted, evaluated_at=evaluated_at)


def present_adapted(
    adapted: AdaptedResultsReview, *, evaluated_at: datetime
) -> PresentedResultsReview:
    """Assemble a presented review from an already-adapted case.

    Used by both the hashed-fixture path and the W1-1 PIT path so the
    challenge/review/markdown assembly is not duplicated.
    """
    render_utc_timestamp(evaluated_at)
    challenge = challenge_adapted(adapted)
    verdict = review_adapted(adapted, challenge)
    presentation_json = canonical_json(
        _canonical_payload(adapted.case, challenge, verdict)
    )
    presentation_sha256 = _sha256_hex(presentation_json)
    return PresentedResultsReview(
        category=CATEGORY_PRESENTED,
        case_id=adapted.case.case_id,
        review_id=adapted.case.review.review_id,
        data_mode=str(adapted.case.review.data_mode),
        acquisition=str(adapted.case.document.acquisition),
        evaluated_at=evaluated_at,
        adapted=adapted,
        challenge=challenge,
        verdict=verdict,
        presentation_json=presentation_json,
        presentation_sha256=presentation_sha256,
        presentation_markdown=_build_markdown(
            adapted.case,
            challenge,
            verdict,
            adapted,
            presentation_sha256,
            evaluated_at,
        ),
    )


# ---------------------------------------------------------------------------
# The runnable entry point — `python -m asxos.domain.results_review.presentation`
# ---------------------------------------------------------------------------

#: The four frozen fixtures, each as (payload builder, case builder). The
#: historical case is the one the mission presents; the other three are the
#: negative controls P2-02/P2-04 froze alongside it.
FIXTURE_CASES: Final[
    Mapping[str, tuple[Callable[[], Mapping[str, object]], Callable[[], ResultsReviewCase]]]
] = {
    "historical": (historical_document_payload, historical_results_case),
    "abstention": (historical_document_payload, abstention_case),
    "injection": (injection_document_payload, injection_case),
    "action-bait": (action_bait_document_payload, action_bait_case),
}


def present_fixture(name: str) -> PresentedResultsReview:
    """Present one named frozen fixture, deterministically.

    `evaluated_at` is pinned to the frozen packet's own `knowledge_cutoff` —
    `decision_engine/demo.py`'s `created_at=cutoff` precedent — so this
    function reads no clock and its output is byte-stable across runs.
    """
    try:
        build_payload, build_case = FIXTURE_CASES[name]
    except KeyError:
        raise ResultsReviewPresentationError(
            f"unknown fixture {name!r}; known fixtures: {', '.join(sorted(FIXTURE_CASES))}"
        ) from None
    case = build_case()
    return present_hashed_fixture(
        build_payload(), case, evaluated_at=case.evidence.knowledge_cutoff
    )


def main(argv: list[str] | None = None) -> int:
    """Print one presented results review to stdout. Writes no file."""
    parser = argparse.ArgumentParser(
        prog="python -m asxos.domain.results_review.presentation",
        description=(
            "Run one hashed results-review fixture end to end and print the "
            "presented package. Analysis only; no recommendation, no persistence."
        ),
    )
    parser.add_argument("--case", default="historical", choices=sorted(FIXTURE_CASES))
    parser.add_argument("--format", default="markdown", choices=("markdown", "json"))
    args = parser.parse_args(argv)
    presented = present_fixture(args.case)
    if args.format == "json":
        sys.stdout.write(presented.presentation_json + "\n")
    else:
        sys.stdout.write(presented.presentation_markdown)
    sys.stdout.write(
        f"\nverdict={presented.outcome} category={presented.category} "
        f"presentation_sha256={presented.presentation_sha256}\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via `python -m`
    raise SystemExit(main())
