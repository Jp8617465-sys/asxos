"""Eval suite for the presented historical results review (P2-05, plan :311).

The mission is *"present the artifact, reuse/gap report, and eval result to
James"*. This suite is the eval result. It exercises the REAL chain end to end
— `adapt_hashed_fixture` -> `challenge_adapted` -> `review_adapted` ->
`presentation.present_hashed_fixture` — over the frozen fixtures, and pins the
properties that make a presented review trustworthy.

Six families:

1. **End to end** — the whole frozen chain runs in memory, produces JSON and
   Markdown from the same validated artifact, and writes nothing anywhere.
2. **Hash identity** — the digests are pinned as hex constants, the clock is
   injected rather than read, timestamps render explicit UTC, and the digest
   survives independent processes under different `PYTHONHASHSEED` and
   `LC_ALL`. What is NOT claimed is pinned too.
3. **Hazard mutations** — each test mutates a HAZARD (the wall clock, a
   Decimal's text form, input key order), not a field, and asserts the digest
   is unmoved. The frozen layer's own text-sensitive fingerprint is asserted
   to move on hazard 2, which is the observation that makes the guard real.
4. **Abstain versus could-not-build** — the two are categorically distinct: an
   `abstain` verdict is a presented success; a packet that failed construction
   or validation raises and is never written up as an outcome.
5. **Advice boundary** — nothing this module authors carries action, rating,
   memo-verdict or review-state vocabulary, and the artifact section is
   reproduced byte-for-byte from the frozen renderer rather than re-authored.
6. **Frozen-layer boundary** — the presentation adds no gate and re-implements
   none; `data_mode` is explicit and can never be `real`.

Digests are pinned as hex strings only. No artifact body is committed anywhere
in this repo (James's standing no-persist instruction).
"""

from __future__ import annotations

import ast
import inspect
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import pytest

import asxos
from asxos.domain.results_review.contracts import ResultsReviewCase
from asxos.domain.results_review.fixtures import (
    historical_document_payload,
    historical_results_case,
)
from asxos.domain.results_review.gates import GateName
from asxos.domain.results_review.presentation import (
    ABSTENTION_IS_SUCCESS,
    CATEGORY_COULD_NOT_BUILD,
    CATEGORY_PRESENTED,
    CONTENT_SEAL_FIELD,
    FIXTURE_CASES,
    NO_ADVICE_DISCLAIMER,
    PRESENTATION_HASH_IDENTITY_AXIS,
    PRESENTATION_NOT_CLAIMED,
    PresentedResultsReview,
    ResultsReviewPresentationError,
    canonical_decimal_text,
    present_fixture,
    present_hashed_fixture,
    render_utc_timestamp,
)

_REPO_ROOT = Path(asxos.__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Pinned digests (hex strings only — never an artifact body)
# ---------------------------------------------------------------------------

#: `presentation_sha256` per fixture, under the identity axis in
#: `PRESENTATION_HASH_IDENTITY_AXIS`. Valid for one interpreter version.
PINNED_PRESENTATION_SHA256: Final[dict[str, str]] = {
    "historical": "57bc00086edf7752b2ec8d449e68e097e17c554e7709af4246534a1fbac40022",
    "abstention": "6e4ca67138205a72656abdadf2753aff8000996e7488a428e37c81f820df54e9",
    "injection": "7feed9d2e5698901e19c087f1181f6b650e9ebd8d09ffe6209a26efe98059b3b",
    "action-bait": "05aaefa561b04b814c27215d34cc79d7f9e6dfb507f1442cc34779b814fab9ac",
}

#: The FROZEN layer's own fingerprints for the presented historical case.
#: Deliberately pinned separately: these hash pydantic's JSON render and are
#: therefore Decimal-text sensitive (hazard 2 moves them; it does not move the
#: presentation digest).
PINNED_HISTORICAL_ARTIFACT_SHA256: Final[str] = (
    "b10afcf3507fac1e7c561d45c5e005a91d7a1c73253e27dafee1ed356d7dcf5b"
)
PINNED_HISTORICAL_CASE_SHA256: Final[str] = (
    "78e016474c3292f155347af7c623374a55337fe7f5834a55fd8686a11767f171"
)

#: The frozen mechanical gate set, restated so a silently added or dropped gate
#: is a test failure rather than a quiet change of meaning.
EXPECTED_GATES: Final[tuple[GateName, ...]] = (
    "integrity_seal",
    "citation_closure",
    "bridge_reconciliation",
    "delta_arithmetic",
    "cutoff_admissibility",
    "tax_readiness_earned",
    "outcome_gate_consistency",
    "challenge_binding",
)

FIXTURE_NAMES: Final[tuple[str, ...]] = tuple(sorted(FIXTURE_CASES))

_ARTIFACT_SECTION_HEADING: Final[str] = "\n## The artifact\n"


def _authored_prefix(presented: PresentedResultsReview) -> str:
    """Everything this module authors, excluding the frozen artifact render.

    The frozen renderer faithfully reproduces the artifact's own recorded text,
    and two negative-control fixtures deliberately quote action/rating bait
    inside a conflict description. Scoping the vocabulary proofs to the
    authored prefix keeps the claim exact: the PRESENTATION never introduces
    that vocabulary, and it never edits the artifact's own words either (see
    `test_artifact_section_is_the_frozen_render_verbatim`).
    """
    head, separator, _ = presented.presentation_markdown.partition(_ARTIFACT_SECTION_HEADING)
    assert separator, "presented markdown must carry the artifact section"
    return head


def _reseal(value: Any) -> Any:
    """Blank every content seal so pydantic re-seals on revalidation."""
    if isinstance(value, dict):
        return {
            key: ("" if key == CONTENT_SEAL_FIELD else _reseal(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_reseal(item) for item in value]
    return value


def _retexted_historical_case() -> ResultsReviewCase:
    """The historical case with three Decimals rewritten value-equal.

    `182.4` -> `182.400000`, `12.8` -> `12.800000`, `1284.6` -> `1284.600000`.
    Every frozen validator still passes (Decimal equality is value-based, so
    the bridge still reconciles exactly and every delta still equals the frozen
    computation) — only the written text differs.
    """
    dumped = _reseal(historical_results_case().model_dump(mode="json"))
    review = dumped["review"]
    review["metric_deltas"][0]["current_value"] = "1284.600000"
    bridge = review["statutory_underlying_bridges"][0]
    bridge["statutory"] = "182.400000"
    bridge["adjustments"][0]["amount"] = "12.800000"
    return ResultsReviewCase.model_validate(dumped)


def _reversed_keys(value: Any) -> Any:
    """Rebuild every mapping with its keys in reverse insertion order."""
    if isinstance(value, dict):
        return {key: _reversed_keys(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [_reversed_keys(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Family 1 — the end-to-end run
# ---------------------------------------------------------------------------


def test_historical_case_runs_end_to_end_through_the_frozen_chain() -> None:
    presented = present_fixture("historical")

    # The adapter ran: the payload verified against the frozen record and the
    # whole case was revalidated through a JSON round trip.
    assert presented.adapted.case.document.document_sha256 == (
        presented.adapted.case.review.frozen_input.document_sha256
    )
    # The challenger ran, independently, bound to this artifact.
    assert presented.challenge.thesis_version_id == presented.review_id
    assert presented.challenge.independent_of_author is True
    assert presented.challenge.evidence_packet_id == (
        presented.adapted.case.evidence.evidence_packet_id
    )
    # The reviewer ran and emitted the plan-:303 triple, nothing else.
    assert presented.verdict.verdict in {"complete", "revise", "abstain"}
    # Both renders exist and come from the same validated artifact.
    assert presented.adapted.artifact_json.startswith("{")
    assert presented.adapted.artifact_markdown.startswith("# Results review ")
    assert presented.presentation_markdown.startswith("# Results review presented — ")
    assert presented.category == CATEGORY_PRESENTED


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_every_frozen_fixture_presents_a_triple_verdict(name: str) -> None:
    presented = present_fixture(name)
    assert presented.category == CATEGORY_PRESENTED
    assert presented.outcome in {"complete", "revise", "abstain"}
    assert presented.verdict.verdict == presented.outcome


def test_presentation_writes_no_file_anywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-persist proof: the run leaves an empty working directory empty."""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    for name in FIXTURE_NAMES:
        present_fixture(name)
    assert list(workdir.iterdir()) == []


def test_the_presented_verdict_is_the_reviewers_and_is_never_upgraded() -> None:
    """The presentation reports; it never decides."""
    for name in FIXTURE_NAMES:
        presented = present_fixture(name)
        assert presented.outcome == presented.verdict.verdict
        if presented.verdict.challenge_ceiling is not None:
            ranks = {"abstain": 0, "revise": 1, "complete": 2}
            assert ranks[presented.outcome] <= ranks[presented.verdict.challenge_ceiling]


# ---------------------------------------------------------------------------
# Family 2 — hash identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_presentation_digest_matches_its_pinned_constant(name: str) -> None:
    assert present_fixture(name).presentation_sha256 == PINNED_PRESENTATION_SHA256[name]


def test_frozen_layer_digests_match_their_pinned_constants() -> None:
    presented = present_fixture("historical")
    assert presented.adapted.artifact_sha256 == PINNED_HISTORICAL_ARTIFACT_SHA256
    assert presented.adapted.case_sha256 == PINNED_HISTORICAL_CASE_SHA256


def test_evaluated_at_is_a_required_keyword_with_no_clock_default() -> None:
    """The clock is injected, never defaulted to `datetime.now(UTC)`."""
    parameter = inspect.signature(present_hashed_fixture).parameters["evaluated_at"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        present_hashed_fixture(  # type: ignore[call-arg]
            historical_document_payload(), historical_results_case()
        )


def _dotted_name(node: ast.expr) -> str:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def test_no_module_on_the_presentation_path_reads_a_wall_clock() -> None:
    """AST proof that no hidden clock exists on the chain.

    An AST walk, not a text grep: prose that *names* `datetime.now(UTC)` in a
    docstring (this package does, to say it never calls it) must not register
    as a clock read, and a real call must not escape because it was spelled
    differently in source text.
    """
    package = _REPO_ROOT / "asxos" / "domain" / "results_review"
    forbidden_suffixes = (".now", ".utcnow", ".today", ".time", ".monotonic")
    offenders: list[str] = []
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                dotted = _dotted_name(node.func)
                if dotted.endswith(forbidden_suffixes):
                    offenders.append(f"{path.name}:{node.lineno} {dotted}")
    assert offenders == []


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_created_at_and_evaluated_at_are_pinned_to_the_knowledge_cutoff(name: str) -> None:
    """The `demo.py` precedent: `created_at=cutoff`, never a fresh clock read."""
    presented = present_fixture(name)
    cutoff = presented.adapted.case.evidence.knowledge_cutoff
    assert presented.adapted.case.review.created_at == cutoff
    assert presented.adapted.case.evidence.created_at == cutoff
    assert presented.adapted.case.review.tax_assessment_reference.created_at == cutoff
    assert presented.evaluated_at == cutoff


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("0", "0"),
        ("0.000000", "0"),
        ("0E-6", "0"),
        ("-0", "0"),
        ("-0.000000", "0"),
        ("182.4", "182.4"),
        ("182.400000", "182.4"),
        ("1E+2", "100"),
        ("100", "100"),
        ("1284.600000", "1284.6"),
        ("-6.50", "-6.5"),
    ],
)
def test_decimal_text_normalisation_gives_one_form_per_value(
    written: str, expected: str
) -> None:
    assert canonical_decimal_text(Decimal(written)) == expected


def test_decimal_normalisation_is_value_equality_not_text_equality() -> None:
    forms = ["0", "0.000000", "0E-6", "-0"]
    assert len({canonical_decimal_text(Decimal(form)) for form in forms}) == 1
    assert len({str(Decimal(form)) for form in forms}) > 1  # the hazard, shown


def test_non_finite_decimal_cannot_be_presented() -> None:
    with pytest.raises(ResultsReviewPresentationError, match="non-finite"):
        canonical_decimal_text(Decimal("NaN"))


def test_every_presented_timestamp_renders_explicit_utc() -> None:
    presented = present_fixture("historical")
    timestamps = re.findall(r"\d{4}-\d{2}-\d{2}T[\d:.]+(?:[+-]\d{2}:\d{2}|Z)?", presented.presentation_json)
    assert timestamps, "the presented payload must carry timestamps"
    for stamp in timestamps:
        assert stamp.endswith("+00:00"), stamp


def test_a_naive_timestamp_cannot_be_presented() -> None:
    with pytest.raises(ResultsReviewPresentationError, match="explicit UTC"):
        render_utc_timestamp(datetime(2025, 8, 21, 23, 59, 59))
    with pytest.raises(ResultsReviewPresentationError, match="explicit UTC"):
        present_hashed_fixture(
            historical_document_payload(),
            historical_results_case(),
            evaluated_at=datetime(2025, 8, 21, 23, 59, 59),
        )


def test_what_the_digest_does_not_claim_is_stated_plainly() -> None:
    """The limits of the claim are part of the claim."""
    joined = " ".join(PRESENTATION_NOT_CLAIMED)
    assert "across Python versions" in joined
    assert "across platforms" in joined
    assert "content_hash" in joined
    assert "persistence" in joined
    assert "one interpreter version" in PRESENTATION_HASH_IDENTITY_AXIS
    presented = present_fixture("historical")
    for statement in PRESENTATION_NOT_CLAIMED:
        assert statement.replace("\n", " ") in presented.presentation_markdown


_SUBPROCESS_PROOF = """
import locale
import sys

requested = sys.argv[1]
try:
    locale.setlocale(locale.LC_ALL, "")
    effective = locale.setlocale(locale.LC_ALL)
except locale.Error:
    effective = "unavailable:" + requested

from asxos.domain.results_review.presentation import FIXTURE_CASES, present_fixture

parts = ["locale=" + effective, "hashseed=" + str(sys.flags.hash_randomization)]
for name in sorted(FIXTURE_CASES):
    presented = present_fixture(name)
    parts.append(
        name
        + "|"
        + presented.presentation_sha256
        + "|"
        + presented.adapted.artifact_sha256
        + "|"
        + presented.outcome
    )
print(" ".join(parts))
"""


def _run_proof(tmp_path: Path, *, hashseed: str, lc_all: str, tag: str) -> str:
    empty_home = tmp_path / f"home-{tag}"
    empty_home.mkdir()
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_PROOF, lc_all],
        env={
            "HOME": str(empty_home),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(_REPO_ROOT),
            "PYTHONHASHSEED": hashseed,
            "LC_ALL": lc_all,
        },
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, f"proof subprocess failed:\n{result.stderr}"
    return result.stdout.strip()


def test_digests_survive_independent_processes_under_hashseed_and_locale(
    tmp_path: Path,
) -> None:
    """The honest instrument for the identity axis: separate processes.

    Two independent interpreters, different `PYTHONHASHSEED` values and
    different `LC_ALL` settings (each subprocess actually calls
    `locale.setlocale(LC_ALL, "")`, so the locale really takes effect when the
    platform has it). Both must reproduce the pinned digests exactly.
    """
    first = _run_proof(tmp_path, hashseed="0", lc_all="C", tag="c")
    second = _run_proof(tmp_path, hashseed="424242", lc_all="de_DE.UTF-8", tag="de")

    assert "hashseed=0" in first
    assert "hashseed=1" in second  # PYTHONHASHSEED=424242 keeps randomisation on
    for output in (first, second):
        for name, digest in PINNED_PRESENTATION_SHA256.items():
            assert f"{name}|{digest}|" in output
        assert PINNED_HISTORICAL_ARTIFACT_SHA256 in output
    # Same digests, genuinely different locales in effect.
    assert first.split()[0] != second.split()[0]


# ---------------------------------------------------------------------------
# Family 3 — hazard mutations (mutate the HAZARD, not a field)
# ---------------------------------------------------------------------------


def test_hazard_1_reexecuting_at_a_different_wall_clock_changes_nothing() -> None:
    """HAZARD: a hidden `datetime.now(UTC)` read.

    Mutation: run the identical presentation twice at two genuinely different
    real wall-clock instants, with the same injected `evaluated_at`.
    Observation without the guard: any clock read on the path would make the
    two renders differ. Here every byte is identical.
    """
    payload = historical_document_payload()
    stamp = historical_results_case().evidence.knowledge_cutoff
    before = datetime.now(UTC)
    first = present_hashed_fixture(payload, historical_results_case(), evaluated_at=stamp)
    while datetime.now(UTC) == before:  # pragma: no cover - sub-microsecond loop
        pass
    second = present_hashed_fixture(payload, historical_results_case(), evaluated_at=stamp)
    assert datetime.now(UTC) > before, "the real wall clock must have moved"

    assert first.presentation_sha256 == second.presentation_sha256
    assert first.presentation_json == second.presentation_json
    assert first.presentation_markdown == second.presentation_markdown
    assert first.adapted.artifact_sha256 == second.adapted.artifact_sha256


def test_hazard_1b_a_different_injected_clock_moves_one_line_and_no_digest() -> None:
    """HAZARD: a presentation stamp silently entering the identity.

    Mutation: inject an `evaluated_at` one day later. Observation: the digest
    is unmoved (the stamp is not part of what was reviewed), and exactly one
    Markdown line changes — the stamp is visible, not silently dropped.
    """
    payload = historical_document_payload()
    case = historical_results_case()
    stamp = case.evidence.knowledge_cutoff
    first = present_hashed_fixture(payload, case, evaluated_at=stamp)
    second = present_hashed_fixture(payload, case, evaluated_at=stamp + timedelta(days=1))

    assert first.presentation_sha256 == second.presentation_sha256
    assert first.presentation_json == second.presentation_json

    differing = [
        (left, right)
        for left, right in zip(
            first.presentation_markdown.splitlines(),
            second.presentation_markdown.splitlines(),
            strict=True,
        )
        if left != right
    ]
    assert len(differing) == 1
    assert differing[0][0].startswith("- Evaluated at (injected")


def test_hazard_2_value_equal_text_different_decimals_do_not_move_the_digest() -> None:
    """HAZARD: one value written three ways hashing three ways.

    Mutation: rewrite three Decimals value-equal but text-different
    (`182.4` -> `182.400000`, `12.8` -> `12.800000`, `1284.6` ->
    `1284.600000`). Observation: the presentation digest is unmoved, while the
    FROZEN layer's own `artifact_sha256` and `case_sha256` DO move — pydantic's
    JSON render preserves the written exponent. That divergence is the whole
    reason the presentation normalises before hashing, and it is reported, not
    hidden.
    """
    payload = historical_document_payload()
    baseline = present_hashed_fixture(
        payload,
        historical_results_case(),
        evaluated_at=historical_results_case().evidence.knowledge_cutoff,
    )
    retexted_case = _retexted_historical_case()
    variant = present_hashed_fixture(
        payload, retexted_case, evaluated_at=retexted_case.evidence.knowledge_cutoff
    )

    # The values really are equal, and the text really does differ.
    assert (
        retexted_case.review.statutory_underlying_bridges[0].statutory
        == historical_results_case().review.statutory_underlying_bridges[0].statutory
    )
    assert '"182.400000"' in variant.adapted.artifact_json
    assert '"182.400000"' not in baseline.adapted.artifact_json

    # The guard holds.
    assert variant.presentation_sha256 == baseline.presentation_sha256
    assert variant.presentation_json == baseline.presentation_json
    assert variant.outcome == baseline.outcome

    # The observed failure the guard exists for.
    assert variant.adapted.artifact_sha256 != baseline.adapted.artifact_sha256
    assert variant.adapted.case_sha256 != baseline.adapted.case_sha256


def test_hazard_3_reordering_input_keys_does_not_move_any_digest() -> None:
    """HAZARD: mapping iteration order leaking into an identity.

    Mutation: rebuild every mapping in the document payload and in the case
    with its keys in reverse insertion order. Observation: the document hash,
    the frozen artifact digest and the presentation digest are all unmoved —
    canonical JSON sorts keys at every level. Without sorted keys the document
    payload would fail its own frozen hash check outright.
    """
    baseline = present_fixture("historical")
    reordered_payload = _reversed_keys(dict(historical_document_payload()))
    reordered_case = ResultsReviewCase.model_validate(
        _reversed_keys(_reseal(historical_results_case().model_dump(mode="json")))
    )
    assert list(reordered_payload) != list(historical_document_payload())

    variant = present_hashed_fixture(
        reordered_payload,
        reordered_case,
        evaluated_at=reordered_case.evidence.knowledge_cutoff,
    )
    assert variant.adapted.case.document.document_sha256 == (
        baseline.adapted.case.document.document_sha256
    )
    assert variant.presentation_sha256 == baseline.presentation_sha256
    assert variant.adapted.artifact_sha256 == baseline.adapted.artifact_sha256


# ---------------------------------------------------------------------------
# Family 4 — abstain (a success) versus could-not-build (a defect)
# ---------------------------------------------------------------------------


def test_abstention_is_a_presented_success_not_a_failure() -> None:
    """Category (a): the pipeline ran, the artifact validated, verdict abstain."""
    presented = present_fixture("abstention")
    assert presented.category == CATEGORY_PRESENTED
    assert presented.outcome == "abstain"
    assert presented.adapted.case.review.missing_evidence  # the recorded reason
    assert presented.adapted.case.review.tax_assessment_reference.readiness == "unknown"
    assert ABSTENTION_IS_SUCCESS in presented.presentation_markdown
    assert presented.presentation_sha256 == PINNED_PRESENTATION_SHA256["abstention"]


def test_a_tampered_payload_is_a_could_not_build_defect_not_an_outcome() -> None:
    """Category (b): construction failed. STOP and report; never write it up."""
    tampered = dict(historical_document_payload())
    tampered["issuer"] = "Tampered Issuer Ltd"
    with pytest.raises(ResultsReviewPresentationError) as excinfo:
        present_hashed_fixture(
            tampered,
            historical_results_case(),
            evaluated_at=historical_results_case().evidence.knowledge_cutoff,
        )
    assert "could not build" in str(excinfo.value)
    assert excinfo.value.category == CATEGORY_COULD_NOT_BUILD


def test_an_invalid_case_is_a_could_not_build_defect() -> None:
    """Validation failure is the same category as construction failure."""
    dumped = _reseal(historical_results_case().model_dump(mode="json"))
    # Break the frozen bridge reconciliation by a cent: unrepresentable.
    dumped["review"]["statutory_underlying_bridges"][0]["underlying"] = "201.71"
    with pytest.raises(ValueError):
        ResultsReviewCase.model_validate(dumped)


def test_could_not_build_is_categorically_distinct_from_every_verdict() -> None:
    """The two categories can never be read as the same thing."""
    assert CATEGORY_COULD_NOT_BUILD != CATEGORY_PRESENTED
    assert CATEGORY_COULD_NOT_BUILD not in {"complete", "revise", "abstain"}
    assert not hasattr(ResultsReviewPresentationError, "verdict")
    assert not hasattr(ResultsReviewPresentationError, "outcome")
    error = ResultsReviewPresentationError("could not build the results-review packet")
    assert error.category == CATEGORY_COULD_NOT_BUILD
    for verdict_word in ("complete", "revise", "abstain"):
        assert verdict_word not in str(error)


def test_an_unknown_fixture_is_a_could_not_build_defect() -> None:
    with pytest.raises(ResultsReviewPresentationError, match="unknown fixture"):
        present_fixture("not-a-fixture")


# ---------------------------------------------------------------------------
# Family 5 — advice boundary
# ---------------------------------------------------------------------------

#: Action / rating vocabulary that must never be authored by this module.
_ACTION_VOCABULARY: Final[tuple[str, ...]] = (
    "price target",
    "target price",
    "rating",
    "buy",
    "sell",
    "trim the",
    "overweight",
    "underweight",
    "position size",
    "recommend",
    "stop loss",
)

#: The two ruled vocabularies (B.6). Neither may appear in authored prose.
_RULED_VOCABULARIES: Final[tuple[str, ...]] = (
    "GOOD HOLD",
    "EXIT-CANDIDATE",
    "TRIM",
    "ADD",
    "REVIEW",
    "CLEAR",
    "ATTENTION",
    "BLOCKED",
    "EVIDENCE_THIN",
)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_authored_presentation_carries_no_action_vocabulary(name: str) -> None:
    """The only place the vocabulary may appear is inside its own negation."""
    presented = present_fixture(name)
    assert NO_ADVICE_DISCLAIMER in presented.presentation_markdown
    authored = _authored_prefix(presented).replace(NO_ADVICE_DISCLAIMER, "").lower()
    for word in _ACTION_VOCABULARY:
        assert not re.search(rf"\b{re.escape(word)}\b", authored), (
            f"{name}: authored prose contains {word!r}"
        )


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_authored_presentation_uses_neither_ruled_vocabulary(name: str) -> None:
    """B.6: memo verdicts and review states are other altitudes entirely."""
    authored = _authored_prefix(present_fixture(name))
    for word in _RULED_VOCABULARIES:
        assert not re.search(rf"\b{re.escape(word)}\b", authored), (
            f"{name}: authored prose contains the ruled token {word!r}"
        )


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_artifact_section_is_the_frozen_render_verbatim(name: str) -> None:
    """The presentation never re-authors the artifact's own words."""
    presented = present_fixture(name)
    _, _, artifact_section = presented.presentation_markdown.partition(
        _ARTIFACT_SECTION_HEADING
    )
    assert presented.adapted.artifact_markdown.rstrip("\n") in artifact_section


def test_the_presented_scope_statement_addresses_only_the_artifact() -> None:
    for name in FIXTURE_NAMES:
        presented = present_fixture(name)
        assert presented.verdict.scope_statement in presented.presentation_markdown
        assert "artifact" in presented.verdict.scope_statement


# ---------------------------------------------------------------------------
# Family 6 — frozen-layer boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_presentation_adds_no_gate_and_reimplements_none(name: str) -> None:
    presented = present_fixture(name)
    assert tuple(check.gate for check in presented.verdict.checks) == EXPECTED_GATES


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_data_mode_is_explicit_and_a_fixture_is_never_real(name: str) -> None:
    presented = present_fixture(name)
    assert presented.data_mode == "synthetic"
    assert presented.acquisition == "hashed_fixture"
    assert presented.adapted.case.document.data_mode == "synthetic"
    assert "Data mode: **synthetic**" in presented.presentation_markdown


def test_content_seals_are_omitted_from_the_presentation_payload() -> None:
    """Stated in `PRESENTATION_NOT_CLAIMED`, and true."""
    presented = present_fixture("historical")
    assert f'"{CONTENT_SEAL_FIELD}"' not in presented.presentation_json
    # The seals are still checked — by the frozen gate, inside the payload.
    assert '"gate":"integrity_seal"' in presented.presentation_json
    assert presented.verdict.checks[0].gate == "integrity_seal"
    assert presented.verdict.checks[0].passed is True


def test_entry_point_prints_the_presented_review_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from asxos.domain.results_review.presentation import main

    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    assert main(["--case", "historical", "--format", "markdown"]) == 0
    captured = capsys.readouterr().out
    assert "# Results review presented — rrv-resl-fy2025" in captured
    assert f"presentation_sha256={PINNED_PRESENTATION_SHA256['historical']}" in captured
    assert "category=presented" in captured
    assert list(workdir.iterdir()) == []
