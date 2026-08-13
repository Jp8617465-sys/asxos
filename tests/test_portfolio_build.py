"""
Hard-fail invariants for PortfolioService.build() (plan H.1 CRITICAL-3 / -5).

These guards were previously untested. The non-convergent-waterfall hard-fail
is covered in test_portfolio_constraints.py; here we cover the build()-level
gates: no active profile, the contamination-isolation model gate, and the
candidate source.

Ordering note: the model gate (Section 4.4 Step B) runs BEFORE candidates are
loaded and MUST keep doing so — it is rule #11's mechanical enforcement point
(manifest E1), and it has to outlive the signals query it originally existed to
filter. `test_model_gate_runs_before_the_candidate_source` pins that order
directly rather than leaving it to a comment. Tests that exercise a later gate
must route the model_versions query to a single approved row so the flow reaches
the gate under test.
"""
from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from asxos.domain.portfolio import candidates
from asxos.domain.portfolio.build import PortfolioService
from asxos.domain.portfolio.candidates import (
    CandidateSourceUnavailable,
    load_allocation_candidates,
)

_BUILD_DATE = date(2026, 6, 1)
_ONE_APPROVED_MODEL = [{"model": "model_a", "version": "v1_5"}]


def _build_conn(monkeypatch, model_versions_rows):
    """A conn whose ``model_versions`` gate returns ``model_versions_rows``.

    Also activates a profile: Step 1 of build() is the no-active-profile
    hard-fail, which would short-circuit before any later gate under test fires.

    Every other query returns []. A generic catch-all row would instead crash on
    a missing key (e.g. the universe read wants ``r["is_active"]``) before the
    gate under test is reached.
    """

    async def _active_profile(conn):
        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _active_profile)

    async def _fetch(query, *args, **kwargs):
        if "model_versions" in query:
            return model_versions_rows
        return []

    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


@pytest.mark.asyncio
async def test_build_no_active_profile_raises(monkeypatch) -> None:
    # plan H.1 CRITICAL-5: hard-fail (not a warning) when no profile is active.
    async def _no_profile(conn):        return None

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _no_profile)
    with pytest.raises(RuntimeError, match="no active profile"):
        await PortfolioService().build(AsyncMock())


@pytest.mark.asyncio
async def test_build_no_approved_model_raises(monkeypatch) -> None:
    # Section 4.4 Step B: zero active+approved_for_allocation rows is a
    # configuration invariant violation — hard-fail before ever touching signals.
    conn = _build_conn(monkeypatch, [])

    with pytest.raises(RuntimeError, match="approved_for_allocation"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_multiple_approved_models_raises(monkeypatch) -> None:
    # Multi-sleeve blending is out of v1 scope (portfolio-conventions.md) —
    # more than one eligible model is a hard-fail, not a silent arbitrary pick.
    two_models = [
        {"model": "model_a", "version": "v1_5"},
        {"model": "factor_sleeve", "version": "v1_0"},
    ]
    conn = _build_conn(monkeypatch, two_models)

    with pytest.raises(RuntimeError, match="multiple models"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


# ---------------------------------------------------------------------------
# Candidate source (manifest A1/A2) — explicit unavailable, never a fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_candidate_source_unavailable_raises(monkeypatch) -> None:
    """With an approved model present, build() still refuses — loudly.

    This is what replaced the "no signals" / "stale signals" hard-fails: the
    Model A candidate feed is gone and nothing was substituted for it, so the
    allocator declares the source unavailable rather than allocating from an
    empty or assumed candidate set (packet P1 required-work item 5).
    """
    conn = _build_conn(monkeypatch, _ONE_APPROVED_MODEL)

    with pytest.raises(CandidateSourceUnavailable) as exc:
        await PortfolioService().build(conn, as_of=_BUILD_DATE)
    # Names the approved model it was gated on, so the message is diagnosable.
    assert "model_a" in str(exc.value)


@pytest.mark.asyncio
async def test_candidate_source_unavailable_is_a_runtime_error() -> None:
    """Distinctly named, but still a RuntimeError.

    Every existing caller and test guards on RuntimeError; narrowing the base
    class would silently stop catching the allocator's refusal to run.
    """
    assert issubclass(CandidateSourceUnavailable, RuntimeError)
    with pytest.raises(RuntimeError):
        await load_allocation_candidates(
            AsyncMock(), approved_model="whatever", build_date=_BUILD_DATE
        )


@pytest.mark.asyncio
async def test_candidate_source_never_returns_a_fallback_set() -> None:
    """It must raise, not return `([], date)` — an empty list would flow into
    allocate() and surface as the generic "empty buy universe" error, which
    reads like a data problem rather than an unwired source.

    This test is also the tripwire for the recency debt. Manifest A2 says to
    "re-anchor the same hard-fail shape onto the replacement candidate source",
    and the retired >2-day staleness gate (plan H.1 CRITICAL-3) has no owner
    until that source exists. Whoever wires one turns this test red, and must
    land the recency assertion in candidates.py at the same time — anchored on
    the evidence's own date, never on `build_date`, which would make the check a
    permanent no-op.
    """
    for as_of in (None, _BUILD_DATE):
        with pytest.raises(CandidateSourceUnavailable):
            await load_allocation_candidates(
                AsyncMock(),
                approved_model="model_a",
                build_date=_BUILD_DATE,
                as_of=as_of,
            )


@pytest.mark.asyncio
async def test_model_gate_runs_before_the_candidate_source(monkeypatch) -> None:
    """Ordering, asserted rather than commented (manifest E1 must stay first).

    With 0 approved models AND an unavailable candidate source, the failure must
    be the approval gate's. If a future candidate source were wired in above the
    gate, this test goes red — which is the point: the gate's whole value is that
    nothing reaches allocation while approval is revoked.
    """
    conn = _build_conn(monkeypatch, [])

    with pytest.raises(RuntimeError) as exc:
        await PortfolioService().build(conn, as_of=_BUILD_DATE)
    assert not isinstance(exc.value, CandidateSourceUnavailable)
    assert "approved_for_allocation" in str(exc.value)


def test_candidates_module_is_model_independent() -> None:
    """A source-level contract on the seam itself (manifest T6's pattern).

    `test_build_issues_no_signals_query` below inspects the queries `build()`
    actually issued — but it is self-disarming: the day a real candidate source
    returns rows, its `pytest.raises(CandidateSourceUnavailable)` fails, the test
    gets rewritten, and its `FROM signals` / `prob_up` / `shap_factors`
    assertions can quietly leave with it. This one survives that rewrite, which
    is the point — `candidates.py` is the file a replacement source lands in, and
    it sits directly on the capital path.
    """
    source = Path(candidates.__file__).read_text()
    import_lines = [
        line
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    banned = ("production_gate", "domain.models", "domain.signals", "brief.shap")
    for line in import_lines:
        for token in banned:
            assert token not in line, f"model-dependent import: {line}"

    # No `signals` SQL in the executable code. Docstrings are stripped first —
    # this module's prose deliberately quotes the retired
    # `SELECT … FROM signals WHERE model = $1` to say what was removed, and a
    # naive text scan would trip on the explanation rather than a regression.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ) and ast.get_docstring(node) is not None:
            node.body = node.body[1:]
    code = ast.unparse(tree)
    for token in ("FROM signals", "from signals", "WHERE model"):
        assert token.lower() not in code.lower(), (
            f"{token!r} reappeared in the candidate seam's executable code"
        )


@pytest.mark.asyncio
async def test_build_issues_no_signals_query(monkeypatch) -> None:
    """Adversarial: no `FROM signals` read survives anywhere in build()."""
    conn = _build_conn(monkeypatch, _ONE_APPROVED_MODEL)

    with pytest.raises(CandidateSourceUnavailable):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)

    for call in conn.fetch.await_args_list:
        query = " ".join(str(call.args[0]).split())
        assert "FROM signals" not in query
        assert "prob_up" not in query
        assert "shap_factors" not in query
