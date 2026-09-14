"""Adversarial tests for evidence `source_uri` rendering in the broker report.

`EvidenceItem.source_uri` is an unrestricted string
(`asxos/domain/decision_engine/types.py:221` — `str`, min_length 1,
max_length 2000) and the report interpolates it into a Markdown link target.
HTML-escaping the value protects the surrounding markup but does nothing about
the scheme a viewer will execute, so linkability is decided by an allowlist.
"""
from __future__ import annotations

from typing import Any

import pytest

from asxos.domain.decision_engine.demo import build_demo_brief
from asxos.domain.decision_engine.renderer import (
    _is_linkable,
    _source,
    render_broker_report,
)
from asxos.domain.decision_engine.types import DecisionCase

# The case is re-sealed rather than re-validated: mutating source_uri breaks the
# content-hash chain by design, so an old hash would fail the test before the
# rendering invariant under test was ever reached.
from tests.test_decision_engine_prototype import _rebuild_case

CUTOFF = build_demo_brief().cases[0].decision.knowledge_cutoff


def _case_with_source_uri(uri: str) -> DecisionCase:
    payload: dict[str, Any] = build_demo_brief().cases[0].model_dump(mode="python")
    payload["evidence"]["items"][0]["source_uri"] = uri
    return _rebuild_case(payload)


ACTIVE_SCHEMES = [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "JAVASCRIPT:alert(1)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "jar:http://evil.test/a!/b",
]


@pytest.mark.parametrize("uri", ACTIVE_SCHEMES)
def test_active_schemes_are_never_linkable(uri: str) -> None:
    assert _is_linkable(uri) is False


@pytest.mark.parametrize("uri", ACTIVE_SCHEMES)
def test_active_schemes_do_not_reach_a_markdown_link_target(uri: str) -> None:
    report = render_broker_report(_case_with_source_uri(uri), evaluated_at=CUTOFF)
    # The value is still shown — suppressing evidence would be worse — but as
    # inert code, never as a link target.
    assert f"]({uri})" not in report
    assert "source `" in report


def test_internal_identifier_schemes_render_inert() -> None:
    for uri in (
        "asxos://theses/1/price_plan",
        "db://themes/big-4-banks",
        "agent://llm/rs_financial_statements",
        "synthetic://market/LOCK.AU",
        "fixture:local",
    ):
        assert _is_linkable(uri) is False


def test_https_and_http_remain_linkable() -> None:
    assert _is_linkable("https://asx.com.au/announcement/1") is True
    assert _is_linkable("http://asx.com.au/announcement/1") is True

    report = render_broker_report(
        _case_with_source_uri("https://asx.com.au/announcement/1"), evaluated_at=CUTOFF
    )
    assert "[source](https://asx.com.au/announcement/1)" in report


@pytest.mark.parametrize(
    "uri",
    [
        "https://ok.test/a)malicious",
        "https://ok.test/a(b",
        "https://ok.test/a b",
        "https://ok.test/a\tb",
        "https://ok.test/a\nb",
        'https://ok.test/a"b',
        "https://ok.test/a<b>",
    ],
)
def test_breakout_characters_disqualify_an_otherwise_approved_scheme(uri: str) -> None:
    # A closing paren would end the link target early and spill the remainder
    # into document text; whitespace and quotes break out the same way.
    assert _is_linkable(uri) is False


def test_scheme_relative_and_bare_values_are_not_linkable() -> None:
    for uri in ("//evil.test/a", "evil.test/a", "/etc/passwd", "?x=1"):
        assert _is_linkable(uri) is False


def test_source_renders_inert_text_for_every_unapproved_scheme() -> None:
    assert _source("javascript:alert(1)") == "source `javascript:alert(1)`"
    assert _source("asxos://theses/1") == "source `asxos://theses/1`"
    assert _source("https://ok.test/a") == "[source](https://ok.test/a)"


def test_shipped_demo_evidence_uses_inert_identifier_sources() -> None:
    # Wiring check on unmodified data: the demo's synthetic:// identifiers must
    # not be presented as followable links.
    report = render_broker_report(build_demo_brief().cases[0], evaluated_at=CUTOFF)
    assert "](synthetic://" not in report
    assert "source `synthetic://" in report


def test_a_backtick_in_an_inert_source_cannot_close_the_code_span_early() -> None:
    # `_source()`'s inert branch wraps the value in a single backtick span:
    # `source `{value}``. A `EvidenceItem.source_uri` value containing a
    # literal backtick would otherwise close that span early and let the
    # remainder re-enter live Markdown as an unchecked `[text](scheme:...)`
    # construct that never passes through `_is_linkable()` — the exact bypass
    # the allowlist above exists to prevent, reached through the "inert"
    # branch instead of the linkable one. No shipped producer emits a
    # backtick today (every source_uri is built from a regex-validated
    # symbol), but the field itself carries no such restriction.
    payload = "a`. [click me](javascript:alert(document.cookie))"
    rendered = _source(payload)
    # The load-bearing property: exactly the two wrapping backticks survive,
    # so the whole payload sits inside one unbroken code span rather than
    # closing early and re-entering live Markdown. The literal substring
    # "](javascript:" is still present, but only as inert text *inside* that
    # one span — safe, and exactly what "escaped" means here.
    assert rendered.count("`") == 2, (
        f"expected exactly the two wrapping backticks, got: {rendered!r}"
    )
    assert rendered == "source `a&#96;. [click me](javascript:alert(document.cookie))`"
    assert rendered.startswith("source `") and rendered.endswith("`")
