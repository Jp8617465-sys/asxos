"""Layer 2 — the bounded, template-only shell for the three LLM jobs (ADR D12/D13).

Until an LLM sits behind it, every sentence here is a template filled with
code-generated counts and figures from the `ChallengeInput`; no author or
document text is ever interpolated (results-review G10 defence). The three
jobs, and what this slice does for each:

1. `strongest_bear_case` — informed pass (D13). Composed from the Layer-1
   state: which register rules fired, the recorded bear scenario, the
   falsifier count. It is a steelman of the *evidence against*, not advice.
2. Outside view — blind pass (D13). Until Slice 4/5 it may only flag the
   ABSENCE of a base-rate justification (ADR §10.4). It never asserts a base
   rate, so its text carries no percentage figure by construction.
3. Falsifiability — one `monitor` finding per invalidation condition that
   carries no measurable quantity or date (field-populated is Layer 1;
   measurable is the judgement this shell can make mechanically).

`admit_llm_finding` is the one door future LLM output will use: it refuses
an unevidenced finding, refuses recommendation verbs, and caps severity at
`material` — under D14 only a ratified-register breach or a certain
data-integrity failure earns `blocking`, and an LLM can establish neither.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Final, Literal

from asxos.domain.decision_engine.challenge.rules import (
    ChallengeInput,
    RuleOutcome,
    is_measurable,
)
from asxos.domain.decision_engine.types import ChallengeFinding

_RECOMMENDATION_VERBS: Final = re.compile(
    r"\b(buy|sell|accumulate|overweight|underweight|go long|go short|exit now|"
    r"take profit|price target|target price|top pick|strong (?:buy|sell)|recommend\w*|"
    r"initiate|add to|trim|reduce|increase|short the|outperform|underperform|"
    r"overvalued|undervalued|fair value|upside|downside)\b",
    re.IGNORECASE,
)
_INVISIBLE_RE: Final = re.compile(r"[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]")
# Cyrillic / Greek letters that render as Latin ones. NFKC does not fold these
# (they are distinct letters, not compatibility forms), so they are mapped
# explicitly before the verb screen runs.
_CONFUSABLES: Final[dict[int, str]] = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u0456": "i", "\u0455": "s", "\u0458": "j", "\u04bb": "h", "\u0501": "d", "\u051b": "q", "\u051d": "w",
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K", "\u041c": "M", "\u041d": "H", "\u041e": "O",
    "\u0420": "P", "\u0421": "C", "\u0422": "T", "\u0425": "X", "\u0405": "S", "\u0406": "I", "\u0408": "J",
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03c5": "y", "\u03b9": "i", "\u0391": "A", "\u0392": "B",
    "\u0395": "E", "\u0397": "H", "\u0399": "I", "\u039a": "K", "\u039c": "M", "\u039d": "N", "\u039f": "O",
    "\u03a1": "P", "\u03a4": "T", "\u03a5": "Y", "\u03a7": "X", "\u0396": "Z",
})
_PERCENT_FIGURE_RE: Final = re.compile(r"\d+(?:\.\d+)?\s*%")

OUTSIDE_VIEW_ABSENCE_TEXT: Final[str] = (
    "No base-rate justification is recorded for this thesis: nothing cites how often "
    "comparable theses have resolved as described. (Outside-view pass, Slice 2.5: flags "
    "absence only; asserts no base rate.)"
)
OUTSIDE_VIEW_REQUIRED_RESPONSE: Final[str] = (
    "Record a base-rate reference for the thesis class, citing evidence, before it is re-challenged."
)


class BoundaryError(ValueError):
    """LLM text that the challenge layer refuses to admit."""


def strongest_bear_case(x: ChallengeInput, outcomes: tuple[RuleOutcome, ...]) -> str:
    fired = [o.rule for o in outcomes if o.finding is not None and o.finding.severity == "blocking"]
    material = [o.rule for o in outcomes if o.finding is not None and o.finding.severity == "material"]
    not_evaluated = [o.rule for o in outcomes if not o.evaluated]
    sentences: list[str] = []
    if fired:
        sentences.append(
            f"{len(fired)} ratified-register or data-integrity rule(s) fail pro-forma "
            f"({', '.join(fired)}); the proposal cannot stand as sized."
        )
    else:
        sentences.append("No ratified-register rule fails pro-forma; the strongest challenge is diagnostic.")
    if material:
        sentences.append(f"{len(material)} material concern(s) require a recorded response ({', '.join(material)}).")
    if x.target_price is not None and x.reference_price is not None and x.last_close is not None:
        sentences.append(
            f"Against a last close of {x.last_close}, the plan's reference price is {x.reference_price} "
            f"and its target {x.target_price}; the bear reading is that the plan, not the price, has moved."
        )
    n_cond = len([c for c in x.invalidation_conditions if c.strip()])
    if n_cond:
        n_meas = len([c for c in x.invalidation_conditions if is_measurable(c)])
        sentences.append(
            f"{n_cond} invalidation condition(s) are recorded, {n_meas} of them measurable; the "
            "unmeasurable remainder cannot falsify the thesis in time."
        )
    else:
        sentences.append("No invalidation condition is recorded; nothing on file can falsify the thesis.")
    if not_evaluated:
        sentences.append(f"{len(not_evaluated)} rule(s) could not be evaluated for lack of a measurement ({', '.join(not_evaluated)}).")
    return " ".join(sentences)


def outside_view(x: ChallengeInput) -> tuple[ChallengeFinding, ...]:
    """Blind pass: position, data and falsifiable claims only — never the narrative."""
    if x.base_rate_evidence_ids:
        return ()
    return (
        ChallengeFinding(
            severity="material",
            finding=OUTSIDE_VIEW_ABSENCE_TEXT,
            required_response=OUTSIDE_VIEW_REQUIRED_RESPONSE,
            evidence_ids=(x.thesis_evidence_id,),
        ),
    )


def falsifiability(x: ChallengeInput) -> tuple[ChallengeFinding, ...]:
    out: list[ChallengeFinding] = []
    for idx, cond in enumerate(x.invalidation_conditions):
        if cond.strip() and not is_measurable(cond):
            out.append(
                ChallengeFinding(
                    severity="monitor",
                    finding=f"Invalidation condition {idx + 1} carries no measurable quantity or date.",
                    required_response="Restate the condition with a threshold or a date so it can be falsified.",
                    evidence_ids=(x.thesis_evidence_id,),
                )
            )
    return tuple(out)


def normalise_llm_text(text: str) -> str:
    """NFKC-fold and strip zero-width characters so a homoglyph or an invisible
    join cannot carry a recommendation verb past the regex."""
    return _INVISIBLE_RE.sub("", unicodedata.normalize("NFKC", text)).translate(_CONFUSABLES)


def admit_llm_finding(
    *,
    text: str,
    required_response: str,
    evidence_ids: tuple[str, ...],
    severity: Literal["material", "monitor"],
    known_evidence_ids: frozenset[str] | None = None,
) -> ChallengeFinding:
    """The single door for LLM-authored findings. Refuses what D12/D13/D14 forbid:
    no evidence, a citation outside the packet (when the packet's ids are
    supplied), a recommendation verb, a percentage figure (an asserted base
    rate), or a blocking severity."""
    if not evidence_ids:
        raise BoundaryError("an LLM finding must cite at least one evidence id")
    if known_evidence_ids is not None:
        unknown = sorted(set(evidence_ids) - known_evidence_ids)
        if unknown:
            raise BoundaryError(f"LLM finding cites evidence outside the packet: {unknown}")
    cleaned = tuple(normalise_llm_text(c) for c in (text, required_response))
    for candidate in cleaned:
        if not candidate.strip():
            raise BoundaryError("an LLM finding cannot be empty")
        m = _RECOMMENDATION_VERBS.search(candidate)
        if m:
            raise BoundaryError(f"LLM finding reads as a recommendation ({m.group(0)!r})")
        if not text_carries_no_percentage(candidate):
            raise BoundaryError("an LLM finding may not assert a percentage figure (D13: no base rate before Slice 5)")
    if severity not in ("material", "monitor"):
        raise BoundaryError("an LLM finding cannot be blocking (D14)")
    return ChallengeFinding(
        severity=severity, finding=cleaned[0], required_response=cleaned[1], evidence_ids=evidence_ids[:100]
    )


def readmit(finding: ChallengeFinding, *, known_evidence_ids: frozenset[str] | None = None) -> ChallengeFinding:
    """Re-run the door on a finding handed in as a bare contract, so the door
    cannot be bypassed by constructing `ChallengeFinding` directly."""
    if finding.severity == "blocking":
        raise BoundaryError("an LLM finding cannot be blocking (D14)")
    return admit_llm_finding(
        text=finding.finding, required_response=finding.required_response,
        evidence_ids=finding.evidence_ids, severity=finding.severity, known_evidence_ids=known_evidence_ids,
    )


def text_carries_no_percentage(text: str) -> bool:
    return _PERCENT_FIGURE_RE.search(text) is None
