# Results-review contracts — the P2-02 freeze record

**Status:** current · the freeze record for mission `P2-02` — "Freeze results evidence and
artifact contracts"
**Work order:** `docs/product/finance-capability-matrix-2026-08-13.md` §8 (the eight freeze
items), executed under the `P2` lane of
`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
**Base:** `origin/main @ 5693fc94edb8c698d4767e62404ac0a17cbbceb9` (branch re-frozen from
`d1b8420` after docs-only #109 merged mid-mission; the intervening commit touched none of the
sources cited here — verified by file list)
**Code:** `asxos/domain/results_review/` (`contracts.py`, `fixtures.py`) +
`tests/test_results_review_contracts.py`
**Owner:** arbi maintains the record; James governs any amendment
**Canonical boundary:** `asxos/domain/decision_engine/types.py` (the executable canonical
contract, `target-architecture.md` B.2/B.4) is **unmodified**. Everything here is built beside
it. No `DecisionBrief.mode` widening occurred (B.5's pre-approval requires a real consumer;
this mission has none). No DB write, no migration, no schema applied anywhere.

---

## 1. The eight-item freeze table

| # | §8 item | Status | Where frozen |
|---|---|---|---|
| 1 | Document-acquisition ruling + hashed fixture (G2) | **FROZEN — HASHED FIXTURE** | `contracts.py::AcquisitionPath`, `DOCUMENT_HASH_ALGORITHM`, `SourceDocumentRecord`; fixture in `fixtures.py::historical_results_case()` |
| 2 | Source hierarchy, verbatim and ranked (G5/G6/G8 context) | **FROZEN** | `contracts.py::SOURCE_RANK`, `ADMISSIBLE_SOURCE_CLASSES`, `LOAD_BEARING_SOURCE_CLASSES` |
| 3 | The frozen-input tuple (8 elements) | **FROZEN** | `contracts.py::FrozenInputTuple` (content-addressed) |
| 4 | `known_at` derivation rule (G8) | **FROZEN** | `contracts.py::derive_statement_known_at()` — reuses `derive_knowledge_date()` |
| 5 | Statutory/underlying reconciliation contract (G3) | **FROZEN** | `contracts.py::StatutoryUnderlyingBridge`, `MetricAdjustment`, `MetricDelta.basis` |
| 6 | Trading-calendar source (G6) | **FROZEN (decision only, not implemented)** | `contracts.py::TRADING_CALENDAR_SOURCE` + conventions; forward-looking source **deferred by name** (`p2_deferred_forward_trading_calendar_source`) |
| 7 | `TaxAssessmentReference` producer contract (G7 + G12) | **FROZEN — `unknown` default** | `contracts.py::TAX_ASSESSMENT_PRODUCERS`, `DEFAULT_TAX_READINESS`, `unresolved_tax_assessment_reference()` |
| 8 | Abstention + injection negative-control fixtures (G10) | **FROZEN** | `fixtures.py::abstention_case()`, `injection_case()` |

None silently dropped. Two named deferrals ride on items 6 and item 1 (see §10); each is a
follow-on work order, not a gap in the freeze.

**§7 A3 discharge** (matrix :407-414) is in §3 below.

---

## 2. Item 1 — the acquisition ruling: HASHED FIXTURE (G2, matrix :427-430)

**Ruled: the acquisition path is a manually supplied, content-hashed document fixture.** No
acquisition path for the ASX announcement exists (G2: `parse_json_announcements` is dead
pending an authenticated endpoint, `asxos/ingestion/regulatory.py:11-12,105-106`; migration
`0030` dropped the legacy `asx_announcements` table). Standing up a real feed is not executable
inside any mission and remains James's later decision.

Frozen consequences (matrix :429-430):

- **Fixture identity:** `SourceDocumentRecord` — document id, security identity, document
  kind/period, currency, units scale, verified release timestamp, transcription note.
- **Hash algorithm:** SHA-256 (`DOCUMENT_HASH_ALGORITHM = "sha256"`), computed by
  `hash_document_payload()` over the canonical JSON form of a JSON-native payload
  (sorted keys, compact separators, ASCII — the decision engine's own canonicalization).
  Floats are rejected; figures are decimal strings. Two layers, deliberately distinct:
  `document_sha256` pins the payload; the inherited `content_hash` pins the record.
- **The never-real invariant:** *a fixture can NEVER be labelled `data_mode="real"`* — enforced
  by a validator on `SourceDocumentRecord`, pinned by
  `test_a_fixture_can_never_carry_data_mode_real`. `data_mode` reuses the canonical
  `DataMode = Literal["real", "synthetic"]` **unchanged** (B.3 amendment 2 is a ruled semantic
  split; adding a third value would be a B.4 governor amendment, which this mission does not
  make). A fixture is therefore always `"synthetic"` in the canonical vocabulary, meaning "not
  acquired through a verifiable real acquisition path" — exactly the property B.3's split
  exists to protect (a non-real case can never be mistaken for real evidence).
- **The fixture itself:** ONE historical-style ASX full-year results case,
  `fixtures.py::historical_results_case()`. The issuer is **fictional** ("Results Review
  Fixture Ltd", `RESL.AU`) and every figure is **synthetic**: with no acquisition path (G2), a
  hand-transcription could not be verified against a source inside this mission, and no
  ASX-copyrighted announcement text may be reproduced. The clean payload's pinned digest is
  `cc8914940979501ef288d6a60158ffa41567413dbdd627ce6f4567ed3a8ec8e6`
  (`test_document_hash_is_stable_and_pins_content`).

---

## 3. §7 A3 discharge — which `rs_security_master` column is the identity

**Answer: `rs_security_master.symbol`.**

Verified against the actual DDL, `migrations/0027_research_store.sql:34-48`:

- `symbol TEXT PRIMARY KEY` (vendor-namespaced, e.g. `CBA.AU`) is the table's **only** unique,
  NOT NULL identity column.
- `isin TEXT` (line 42) is nullable and carries **no UNIQUE constraint** — it cannot serve as
  the canonical identity today.
- everything else (`name`, `exchange`, `currency`, `security_type`, GICS fields, dates) is an
  attribute, not an identity.

Frozen binding: `contracts.py::SECURITY_ID_BINDING = "rs_security_master.symbol"`. Every
`security_id` field in this package — and, per B.3 amendment 1, on the canonical
`ThesisVersion` (`types.py:275`) — carries that column's value verbatim; `symbol`/`exchange`
fields remain **display attributes only**. Migrating identity to ISIN or a surrogate key would
require both a migration and a B.4 governor amendment — deferred by name
(`p2_deferred_security_id_column_migration`). Rows affected per the matrix: B5.1, B4.2.

---

## 4. Item 2 — the source hierarchy (matrix :431-435; plan :290-292)

Frozen verbatim from the packet: *"ASX announcement and audited statements first; issuer
presentation second; complete transcript where lawfully available; reconciled ASXOS PIT
records; licensed consensus only when provenance and rights are explicit; news is contextual
and never load-bearing."*

| Rank | Class | Admissible | Load-bearing |
|---|---|---|---|
| 1 | `asx_announcement`, `audited_statements` | yes | yes |
| 2 | `issuer_presentation` | yes | yes |
| 3 | `results_transcript` | yes | yes |
| 4 | `asxos_pit_record` | yes | yes |
| 5 | `licensed_consensus` | **no — out of scope** | no |
| 6 | `news` | yes (contextual) | **never** |

- `licensed_consensus` stays in the ranked hierarchy verbatim but is frozen **out of scope**:
  there is no licensed consensus feed, and `rs_estimates` (B5.6) is explicitly excluded
  (matrix :434-435).
- "Never load-bearing" is schema-enforced, not prose: `MetricAdjustment`, `MetricDelta` and
  `GuidanceChange` reject any `source_class` outside `LOAD_BEARING_SOURCE_CLASSES`
  (`test_non_load_bearing_sources_cannot_carry_an_adjustment`).
- Units/scale rules (G4): every monetary figure in the contracts carries an explicit `currency`
  **and** an explicit `UnitScale` (`ones | thousands | millions | billions`); a delta across
  mixed currencies or scales is unrepresentable. The research store has no scale column today
  (`migrations/0027_research_store.sql:77` carries only `currency`) — the contract freezes the
  rule ahead of any schema.
- `filing_date` is not a release timestamp (G8): `SourceDocumentRecord.release_at` is the
  verified (fixture: declared) release instant, and the schema comment rule is restated in the
  `derive_statement_known_at` docstring. See §6.

---

## 5. Item 3 — the frozen-input tuple (matrix :436-439)

`FrozenInputTuple` (content-addressed) carries **exactly** the eight ruled elements:

1. document identity (`document_id`) **+ hash** (`document_sha256`)
2. `security_id` (§3 — the `rs_security_master.symbol` value)
3. reporting period (`period_end`)
4. `period_type` (`yearly | half_yearly | quarterly`)
5. `currency`
6. **units/scale** (`units_scale`, G4 — no column exists today)
7. `knowledge_cutoff` (UTC datetime)
8. the ASXOS evidence snapshot identity (`evidence_packet_id`)

`test_frozen_input_tuple_carries_exactly_the_eight_elements` pins the field set (plus the
`content_hash` seal). Three of the eight have no DB column today (document hash, units scale,
and the document identity itself) — matrix :438-439 — which is why the tuple is frozen as a
contract, not a table. Note: `half_yearly` reflects the ASX Appendix 4D reality;
`rs_financial_statements.period_type` knows only `yearly | quarterly` (`0027:71`) — mapping is
the P2-03 adapter's concern and involves no `rs_*` schema change in this mission.

---

## 6. Item 4 — the `known_at` derivation rule (G8, matrix :440-442)

Frozen two-branch rule for `EvidenceItem.known_at`:

1. **Document-sourced evidence** (the announcement itself): `known_at` = the document's
   verified `release_at` timestamp. Never `filing_date`, never `report_date` — the schema
   itself warns `filing_date` *"often defaults to period_end"* and `report_date` *"MAY be
   future/scheduled"* (`migrations/0027_research_store.sql:73-76`).
2. **Vendor-dated statement evidence** (`rs_*` rows): `known_at` =
   `derive_statement_known_at()`, which **reuses** the probe-validated PIT guard
   `derive_knowledge_date()` (`asxos/ingestion/financial_statements.py:56-84`, default lag 75
   days) as the single source of truth — the guard drops disclosure dates that defaulted to
   `period_end` and scheduled future dates — then places the instant at the **conservative
   end-of-day** `23:59:59 UTC` (`STATEMENT_KNOWN_AT_UTC_TIME`).

The end-of-day convention errs toward **excluding** same-day vendor-dated evidence rather than
admitting it: under the canonical `known_at <= knowledge_cutoff` gate (`types.py:249-251`), a
row whose knowledge date is the cutoff day is only admissible at a cutoff at or after the end
of that day — pinned by `test_known_at_end_of_day_is_conservative_against_intraday_cutoffs`.
An approximate `known_at` can therefore weaken the no-post-cutoff-evidence gate only toward
abstention, never toward leakage.

---

## 7. Item 5 — statutory/underlying separation, in the schema (G3, matrix :443-445)

Encoded, not prose:

- `StatutoryUnderlyingBridge` holds `statutory` and `underlying` as distinct Decimal fields
  and validates `statutory + Σ(adjustments) == underlying` with **exact** Decimal equality —
  no tolerance (`test_bridge_must_reconcile_exactly`).
- **Every adjustment carries an explanation and an evidence citation** — `MetricAdjustment`
  makes both mandatory non-empty fields, so an unexplained or uncited adjustment is
  *unrepresentable* (`test_every_adjustment_requires_explanation_and_citation`).
- The separation survives to the delta level: `MetricDelta.basis` is
  `Literal["statutory", "underlying"]`, and `delta_pct` must equal the frozen deterministic
  rule `frozen_delta_pct()` (`((current − prior) / prior) × 100`, quantized to 6 dp,
  ROUND_HALF_EVEN) or be `None` when there is no usable prior — a delta can never be an
  invented number (plan required-work item 2: deterministic Decimal logic).
- Guidance (G5 — no guidance store exists): `GuidanceChange.prior` is `None` when no prior
  guidance is recorded — an explicit unknown, never an implied "unchanged".

---

## 8. Item 6 — the trading-calendar source ruling (G6, matrix :446-448)

**Ruled (decision only — implementation is P2-03+, per the mission boundary):** a real
packet's `TradingSessionCalendar` derives from
**`asxos_prices_observed_sessions`** — the distinct `prices.dt` values observed across
ASX-quoted symbols in the repo's own point-in-time price store. A session is a day the ASX
equity market demonstrably traded, evidenced by the same store the review's evidence comes
from. No new dependency is introduced (an `exchange_calendars`-style library would need a
`tech-stack-researcher` consult and is not required for a historical review).

Frozen conventions (`types.py:172-173` fields):

- `calendar_id` = `asx-observed-prices` (`TRADING_CALENDAR_ID_PREFIX`);
- `calendar_version` = ISO date of the latest included session + first 12 hex chars of the
  SHA-256 over the ISO-8601 session list (e.g. `2026-08-14+3f9a0c1d2e4b`);
- each session date maps to the ASX cash-market close, **16:00 Australia/Sydney**, expressed
  in UTC via zoneinfo (AEST/AEDT-aware) — `TRADING_SESSION_CLOSE_LOCAL`.

**Shortfall rule (frozen):** when the calendar runs short of sessions after a historical
cutoff, `TradingSessionCalendar.resolve_expiry` already raises (`types.py:190-194`) and that
hard-fail **stands** — no weekday padding, no graceful fallback (CLAUDE.md non-negotiable
#10). The demo's weekday generator remains labelled "never use this as an exchange calendar";
the fixtures' calendar is likewise fixture-labelled.

**Named limitation → deferral:** this source cannot see FUTURE sessions, so a live-cutoff
packet needs a forward-looking calendar source. Deferred by name:
`p2_deferred_forward_trading_calendar_source`. Honest, because `P2`'s slice reviews a
historical case.

---

## 9. Item 7 — the `TaxAssessmentReference` producer contract (G7 + G12, matrix :449-455)

- **Producer (frozen):** B6.2's aggregator — `asxos.domain.tax.positions.tax_view_individual`
  / `tax_view_smsf` (`TAX_ASSESSMENT_PRODUCERS`) — *"the only sane candidate"*
  (matrix :450-451). Wiring it is a later work order; nothing here calls it.
- **Default (frozen): `readiness="unknown"`, not `"pass"`** (`DEFAULT_TAX_READINESS`). The
  aggregator has never been fed real dividends or realised gains — its only caller hardcodes
  `dividends=[]` and `realised_gains=[]` (`asxos/cli/tax.py:93,99`, G12) — so `pass` would be
  an unearned assertion.
- **The only constructor this package offers** is
  `unresolved_tax_assessment_reference()` → `{applicability: "uncertain",
  readiness: "unknown"}`, a projection of the canonical `TaxAssessmentReference` (§3.1
  path 1). There is deliberately no pass-producer here.
- The teeth stay canonical: non-pass readiness mechanically forbids every action state in
  `DecisionPacket` (`types.py:512-516`). **UNKNOWN is a valid, successful outcome, not a
  failure** (matrix :454-455) — all three fixtures carry it
  (`test_every_fixture_carries_unknown_tax_readiness`).

---

## 10. Item 8 — the negative controls (G10, matrix :456-458)

Both extend the abstention pattern of `demo.py::_blocked_case()` (B4.10) — explicitly named
blocking conditions force the non-action outcome — rather than inventing parallel machinery.
Both are **fixture definitions and contract instances only**; no adapter code.

- **Abstention control** (`fixtures.py::abstention_case()`): the comparative PIT statements
  are absent from the packet; `missing_evidence` names them; the frozen artifact gate
  (`missing_evidence` non-empty → outcome MUST be `abstain`) makes any other outcome
  unrepresentable (`test_missing_evidence_forces_abstention`). Incomplete evidence forces
  abstention (plan acceptance :308).
- **Injection control** (`fixtures.py::injection_case()`): the document payload embeds a
  clearly-labelled adversarial instruction string demanding `readiness="pass"`,
  `outcome="complete"`, a rating and a price target. The test pins that the adversarial
  document **moves nothing**: identical bridges, deltas, guidance and citations to the clean
  case; tax readiness still `unknown`; outcome `abstain` behind an unresolved integrity
  conflict; the demanded rating/price-target strings appear nowhere in the artifact
  (`test_adversarial_document_moves_no_number_and_no_citation`). The adversarial text lives
  in a `speculative`-tier item and can never be load-bearing (§4).

The review artifact itself is fenced by construction: `Contract`'s `extra="forbid"` rejects
any smuggled `price_target`/`rating`/`recommendation_state`/`size_range` field
(`test_artifact_rejects_recommendation_shaped_fields`), and the outcome vocabulary is the
plan's own triple, verbatim: *"Return `complete`, `revise`, or `abstain`; do not return a
rating, price target, trade, or position-size instruction"* (plan :303).

---

## 11. §3.1 path taken by each schema

Per the product object rule (plan :170-181), every new artifact must (1) project an existing
canonical object, (2) extend one through a versioned reviewed contract change, or (3) prove a
consumer requirement existing contracts cannot express.

| Schema | Path | Basis |
|---|---|---|
| `Contract` / `ContentAddressedContract` bases, `DataMode`, `EvidencePacket`, `EvidenceItem`, `TradingSessionCalendar` (fixtures), `TaxAssessmentReference`, `verify_content_hash` | **1 — projection** | Reused unchanged from `types.py`; zero modifications |
| `unresolved_tax_assessment_reference()` | **1 — projection** | Constructs the canonical `TaxAssessmentReference` with the frozen defaults |
| `derive_statement_known_at()` | **1 — projection** | Reuses `derive_knowledge_date()` (`asxos/ingestion/financial_statements.py:56-84`) as the single source of the PIT rule; layering precedent: `asxos/domain/position_monitor/fetcher.py:23` |
| `ResultsReviewArtifact`, `ResultsReviewCase`, `FrozenInputTuple`, `SourceDocumentRecord`, `StatutoryUnderlyingBridge`, `MetricAdjustment`, `MetricDelta`, `GuidanceChange`, `CitedStatement`, `EvidenceConflict` | **3 — proven consumer requirement** | The plan itself authorizes the family: *"The results path may introduce a `ResultsReviewArtifact`, but it is an analysis input to a `ThesisVersion`; it is not a second decision packet and does not mutate a thesis by itself"* (plan :180-181). No canonical object can express a statutory/underlying bridge, a frozen document tuple, or a review outcome; the consumers are `P2-03` (adapter) and `P2-04` (reviewer/challenger), both already work-ordered |

**Path 2 was used zero times.** No existing canonical artifact gained or lost a field; no
ruled table changed; `types.py` is byte-identical to `origin/main`.

**Vocabulary check (B.2 "no fourth definition" / B.6 altitudes):** the artifact's
`complete | revise | abstain` is the plan's ruled return vocabulary for a results review
(:303). It is not a decision state, not a memo verdict (B.3), and not a review state
(P1-04 / B.6) — a fourth *decision* vocabulary is exactly what this package does **not**
create, and `test_outcome_vocabulary_is_the_plan_triple_only` rejects members of the other
vocabularies.

---

## 12. Standing boundaries, quoted

- **Rule #11** (CLAUDE.md, non-negotiable #11, quoted verbatim): *"STANDING (resolved
  2026-07-11): do not use Model A output — signals, candidate scans, allocator runs, or new
  thesis proposals derived from it — as a basis for real capital decisions."* Nothing in this
  package reads a signal, a model, or `resolve_production_model()`; the artifact carries the
  canonical `model_independence: Literal[True]` assertion (B.3 amendment 3).
- **The s766B firewall** (`.claude/rules/portfolio-conventions.md`, "Regulatory firewall",
  quoted verbatim): *"This is the architectural firewall preventing personal-advice outputs
  (under s766B Corporations Act 2001 / the Westpac v ASIC boundary) from being surfaced in a
  multi-user context."* The results-review artifact is evidence and analysis only — no
  recommendation generation (disabled pending Australian legal review), no ratings, no price
  targets, no portfolio instructions, no thesis mutation. Its honest first outcome on real
  inputs is `abstain`, and **abstention is a success** (matrix :366-368).

---

## 13. What was deliberately NOT frozen (matrix :460-476)

- **Any persistence schema.** `P2` writes nothing (plan :310-311). `thesis_evidence` (B9.3)
  remains the eventual destination; the agent→thesis route does not exist (G11).
- **The allocator's re-entry** (B7.5) — parked; `P2` produces analysis, not allocation.
- **Lot selection / forex gain** (B6.4, B6.5) — zero-consumer disposal mechanics.
- **`rs_factor_scores` / quant-lane revival** (B5.5, B5.7) — parked by the repo's own
  consumer test.
- **`portfolio/monitor.py` attribution** (B7.9) — Appendix C's concern at `P7`.
- **The A2 verdict-vocabulary question** — the governor's, owned by `P1-04`'s consequence;
  ruled B.6 (2026-08-13). This package touches neither vocabulary.
- **`DecisionBrief.mode` widening** (B.5) — pre-approved only with a real consumer inside the
  results-review mission; this contracts-freeze mission has no such consumer, so `mode`
  remains `Literal["synthetic_prototype"]`, untouched.

## Deferred by name

| Name | What | Trigger |
|---|---|---|
| `p2_deferred_forward_trading_calendar_source` | A forward-looking session source for live-cutoff packets (§8) | First real, non-historical packet |
| `p2_deferred_security_id_column_migration` | ISIN/surrogate identity for `rs_security_master` (§3) | Requires migration + B.4 governor amendment |
| Real document acquisition path (G2) | Widening `AcquisitionPath` beyond `"hashed_fixture"` | James's decision; a separately authorized work order |

**JAMES_NEEDED items: none.** No freeze required a field change to any existing canonical
artifact.
