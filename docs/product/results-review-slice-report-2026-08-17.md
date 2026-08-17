# Results-review slice — the P2-05 presentation, reuse and gap report

**Status:** current · the completion report for mission `P2-05` — "Present one historical results
review", the final unit of the `P2` results-review lane
**Work order:** `docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
`P2` required work 5-7 and the `:310-311` stop condition — *"present the artifact, reuse/gap report,
and eval result to James"*
**Base:** branched from `claude/p2-04-reviewer-challenger @ 49950d25a711fa8713c492dc14781126216ad85b`
(depth 4: `P2-02` ← `P2-03` ← `P2-04` ← `P2-05`; `P2-02` has since merged to `main` as #113)
**Code:** `asxos/domain/results_review/presentation.py` + `tests/test_results_review_presentation.py`
**Owner:** arbi maintains the record; James governs any amendment
**Frozen boundary:** `contracts.py`, `fixtures.py`, `adapter.py`, `gates.py`, `reviewer.py`,
`challenger.py` and `asxos/domain/decision_engine/types.py` are **byte-unmodified**. Every rule they
enforce is re-run here, never re-implemented.

**This report is not a gap registry.** The registry is
`docs/product/finance-capability-matrix-2026-08-13.md` §6 (rows `G1`-`G12`). Every gap below cites
an existing `G`-row or an already-named deferral by identifier and says only what *this run
observed about it*. No gap identifier is minted here, and no `G`-row's content is restated.

---

## 1. The outcome, stated first and honestly

**The presented historical review returned `complete`.** Not `abstain`.

| | Value |
|---|---|
| Fixture presented | `fixtures.historical_results_case()` (`resl-fy2025-historical`) |
| Reviewer verdict | **`complete`** |
| Derived verdict | `complete` |
| Independent challenge outcome | `pass` (2 findings: 1 `material`, 1 `monitor`; 0 `blocking`) |
| Challenge ceiling imposed | none |
| Mechanical gates | 8 of 8 passed |
| `data_mode` | `synthetic` |
| Tax readiness | `unknown` |
| Presentation digest | `57bc00086edf7752b2ec8d449e68e097e17c554e7709af4246534a1fbac40022` |

### Which of the two categories this fell into

The mission's constraint 7 keeps two things apart that are easy to blur. This run fell into the
**first** one:

- **(a) The pipeline ran and the artifact validated.** The verdict is then whatever the reviewer
  derived — `complete`, `revise`, or `abstain`. This is the category this run landed in, with the
  verdict `complete`. An `abstain` in this category is a **pre-registered success** (plan `:308`;
  matrix `:366-368`), not a failure.
- **(b) The packet failed construction or validation.** That is a **STOP-and-report defect**. It
  raises `ResultsReviewPresentationError` (category `could_not_build`) and is **never** written up
  as an honest review outcome. It did not occur on any of the four frozen fixtures.

The two are mechanically distinct in code (`CATEGORY_PRESENTED` vs `CATEGORY_COULD_NOT_BUILD`, a
verdict value vs a raised exception) and separately test-pinned
(`test_abstention_is_a_presented_success_not_a_failure`,
`test_a_tampered_payload_is_a_could_not_build_defect_not_an_outcome`,
`test_could_not_build_is_categorically_distinct_from_every_verdict`).

### Why `complete` here is not in tension with the matrix's expectation

Matrix §6 predicts that *"the truthful outcome of the first **real** results review is very likely
`abstain` or `revise`, not `complete`"*, resting on `G6`, `G7` and `G12`. That prediction is about a
**real** packet and it stands untouched. This run is a synthetic hashed fixture, and `complete` here
means only what the frozen contracts define it to mean: the artifact is internally complete —
every material claim is cited inside the frozen packet, every bridge reconciles exactly, every delta
equals the frozen computation, no evidence postdates the cutoff, no evidence is recorded as missing,
and the one recorded conflict carries a recorded resolution.

It does **not** mean the tax consequence is resolved. Tax readiness stayed `unknown` (`G7`, `G12`),
and that is by design: the results-review artifact is not a `DecisionPacket`, and it is the
canonical `DecisionPacket` — not this artifact — where a non-pass readiness mechanically forbids
every action state (`asxos/domain/decision_engine/types.py:512-516`). A `complete` results review is
an **analysis input to a `ThesisVersion`** (plan `:180-181`); it authorises nothing.

The other three frozen fixtures returned `abstain`, each for its own recorded reason, and each is
also a success:

| Fixture | Verdict | Challenge | Recorded reason |
|---|---|---|---|
| `abstention_case()` | `abstain` | `abstain` | two named evidence inputs absent |
| `injection_case()` | `abstain` | `abstain` | unresolved integrity conflict (`G10` control) |
| `action_bait_case()` | `abstain` | `abstain` | unresolved integrity conflict (`G10` control) |

---

## 2. `data_mode` and the verdict vocabulary — stated explicitly, not discovered

Two things a reader must not meet by surprise.

**`data_mode` is `synthetic` on every presented artifact, and can never be `real`.** The acquisition
path is `hashed_fixture`, the only value `contracts.AcquisitionPath` admits, and
`SourceDocumentRecord.validate_fixture_never_real` makes a `real`-labelled fixture unrepresentable
(matrix `:427-430`). This is a direct consequence of `G2` being unresolved — see §4. The
all-synthetic-or-all-real non-mixing invariant (matrix `:377-383`) is preserved: nothing in this
mission widens `DecisionBrief.mode`, and every case is synthetic end to end. `data_mode` is printed
in the presented package's Provenance block and pinned by
`test_data_mode_is_explicit_and_a_fixture_is_never_real`.

**The reviewer emits `complete | revise | abstain` — a THIRD vocabulary, and deliberately so.** It
is neither of the two vocabularies ruled in `docs/product/target-architecture.md` **B.6**:

- not the B.3 decision-state / memo-verdict map (`GOOD HOLD` · `ADD` · `TRIM` · `EXIT-CANDIDATE` ·
  `REVIEW`), which answers *"what should James consider doing about this position?"*;
- not the `P1-04` review states (`CLEAR` · `ATTENTION` · `BLOCKED` · `EVIDENCE_THIN`), which answer
  *"can we say anything reliable about this position right now?"*.

B.6's ruling is that those two are **different altitudes, not rivals**, and that no conversion
function between them may be written. The results-review triple is a third altitude again: it
answers *"is this review finished, does it need correction, or must it abstain?"* — a statement
about the **artifact**, not about a position and not about the evidence's usability for a decision.
It is the plan's own ruled vocabulary, quoted verbatim at plan `:303`, and it was frozen into
`contracts.ResultsReviewOutcome` by `P2-02` before B.6 was in view of this lane. No conversion in
either direction exists, and `watch` — a member of the packet's other triple (plan `:105-106`) — is
unrepresentable in reviewer output.

**Flagged for James, not assumed:** three vocabularies now coexist in the repo. B.6 rules two of
them and closes with "no conversion function between them may be written"; the third is authorised
by the plan itself. Nothing here creates a fourth or converts between any of them
(`test_authored_presentation_uses_neither_ruled_vocabulary` pins the negative), but whether B.6
should be extended to name the results-review triple explicitly is a governor question, not a
builder's.

---

## 3. Reuse — what already existed and was used as-is

The `P2` stop condition asks for a reuse report. `P2-05` added one module. Everything else is reuse.

| Reused | From | How |
|---|---|---|
| `adapt_hashed_fixture` | `adapter.py` (P2-03) | the only ingestion path; payload-hash verification + full case revalidation |
| `render_artifact_json` / `render_artifact_markdown` | `adapter.py` (P2-03) | plan item 7's two renders, from the same validated artifact; reproduced **verbatim**, never re-authored |
| `challenge_adapted` | `challenger.py` (P2-04) | plan item 5's independent challenge |
| `review_adapted` | `reviewer.py` (P2-04) | plan item 6's `complete \| revise \| abstain` |
| `evaluate_case` and its 7 gates | `gates.py` (P2-04) | reached through the reviewer; not re-run separately, not re-implemented |
| `ChallengeResult` | `decision_engine/types.py` | the canonical contract, unmodified |
| `created_at = knowledge_cutoff` | `decision_engine/demo.py` | the clock-pinning precedent, applied to `evaluated_at` |
| Markdown structure neutralisation | `adapter._md_text` | deliberately mirrored rather than importing a private name out of a frozen module |
| Scrubbed-env subprocess proof idiom | `tests/test_results_review_import_isolation.py` | reused for the `PYTHONHASHSEED` / `LC_ALL` identity proof |
| The four frozen fixtures | `fixtures.py` (P2-02, extended P2-04) | presented as-is; no new fixture was authored |

**Built new, and only this:** `asxos/domain/results_review/presentation.py` — value canonicalisation
(`canonical_decimal_text`, `render_utc_timestamp`, `canonicalise`), the `evaluated_at`-free identity
payload, the presented package and its Markdown, the two outcome categories, and a runnable entry
point (`python -m asxos.domain.results_review.presentation`).

No new dependency. No DB, no network, no migration, no persistence, no file write.

---

## 4. Gaps — every one cites an existing `G`-row or a named deferral

Referenced, never restated. Read the cited row or deferral for its content.

| Cited | What THIS run observed | Where visible |
|---|---|---|
| `G2` | Still unresolved, and it is what forces `data_mode="synthetic"` on all four presented artifacts. The named deferral is "Real document acquisition path (G2)" in the `P2-02` freeze record §10. | `presented.data_mode`; `test_data_mode_is_explicit_and_a_fixture_is_never_real` |
| `G3` | Present in contract only. The presented bridge reconciles exactly (`182.4 + 12.8 + 6.5 = 201.7`, no tolerance) from fixture values; no store backs it. | `statutory_underlying_bridges` in the presented artifact |
| `G4` | Same shape: scale is carried on every figure by contract, by no column. | `Currency / scale: AUD / millions` in the render |
| `G5` | The presented guidance change carries `prior = None` — an explicit unknown, never an implied "unchanged". | `## Guidance changes` in the render |
| `G6` | Unchanged by this mission. The fixture packets carry the P2-02 fixture calendar, explicitly labelled not-an-exchange-calendar; the real source stays the frozen decision plus the named deferral `p2_deferred_forward_trading_calendar_source`. | `calendar_id="fixture-weekdays-not-an-exchange-calendar"` |
| `G7`, `G12` | Both unchanged. Tax readiness is `unknown` on every presented artifact and the `tax_readiness_earned` gate passes precisely because `unknown` is the honest value. | `Tax readiness: unknown`; gate row in the presented package |
| `G8` | Unchanged. The `known_at` derivation used by the fixture PIT items is the frozen `derive_statement_known_at` rule; this mission neither strengthens nor weakens it. | `cutoff_admissibility` gate |
| `G9` | Closed for the deterministic core by `P2-04` and exercised here end to end: the presented package carries a real canonical `ChallengeResult`. Its two residuals stay named: `p2_deferred_bounded_prompt_shell` and `p2_deferred_challenge_subject_binding` (both recorded in `challenger.py`'s module docstring). | `## Independent challenge` |
| `G10` | Exercised. `P2-05` adds one proof the earlier missions did not have: the vocabulary negative is asserted over the **authored prefix** of the presented package for all four fixtures, and the artifact section is asserted byte-identical to the frozen render — so the presentation can neither introduce action vocabulary nor edit the artifact's own words. | `test_authored_presentation_carries_no_action_vocabulary`, `test_artifact_section_is_the_frozen_render_verbatim` |
| `G11` | Unchanged and load-bearing for what comes next: this mission persists nothing, and the plan's `:310-311` separate work order is where any thesis-revision persistence must be authorised. | nothing written anywhere; `test_presentation_writes_no_file_anywhere` |
| `G1` | Framing only, as the row itself says. The presentation layer is deterministic Python; no runtime plugin or skill is required for it to work. | — |
| `p2_deferred_security_id_column_migration` | Unchanged. `security_id` binds to `rs_security_master.symbol` verbatim (`RESL.AU`), as `P2-02` §3 froze it. | `Security: RESL.AU` in the render |

**No `P2-03` or `P2-04` freeze-record document exists.** Those missions shipped code and tests only
(verified against the branch file list). Their named deferrals therefore live in the module
docstrings cited above — `challenger.py:20-21` and `challenger.py:37-38` — and not in a `docs/`
record. Anyone looking for a `P2-03`/`P2-04` freeze record should look there.

---

## 5. Eval result

`tests/test_results_review_presentation.py` — **33 test functions, 67 collected cases, all passing.**
Six families:

| Family | What it proves |
|---|---|
| 1. End to end | the full frozen chain runs in memory; both renders derive from the same validated artifact; nothing is written to disk |
| 2. Hash identity | digests pinned as hex constants; clock injected not read (AST proof); explicit UTC; independent-process identity under differing `PYTHONHASHSEED` and `LC_ALL` |
| 3. Hazard mutations | three hazards mutated and shown not to move the digest (§6) |
| 4. Abstain vs could-not-build | the two categories are mechanically and semantically distinct |
| 5. Advice boundary | no action, rating, memo-verdict or review-state vocabulary in anything this layer authors |
| 6. Frozen-layer boundary | no gate added, none re-implemented; `data_mode` explicit and never `real` |

Repository checks, as observed on this machine (`ruff 0.7.0`, `mypy 1.11.2`, `pytest 8.3.3`,
CPython 3.12.11):

- `ruff check .` — **clean**.
- `mypy asxos` (strict) — **clean, 167 source files**.
- `pytest tests/ -q` — **2220 passed, 1 skipped, 2 xfailed, 0 failed**.
- `pytest tests/ -q 2>&1 | grep '^ERROR'` — **no output**. This machine's venv carries the ML
  extras, so the documented joblib/lightgbm sandbox collection-error baseline did **not** appear
  here; that baseline is a sandbox-environment property, and CI (`full-check`) remains the real
  gate.

### Identity: the claim, in one sentence

> The presentation digest is byte-identical across independent processes on one interpreter version,
> given an explicitly injected `evaluated_at`, because every presented value is first reduced to a
> single canonical text form — normalised fixed-point Decimal text, explicit-UTC timestamps, sorted
> mapping keys, ASCII-escaped compact JSON — which makes it invariant to `LC_ALL`, to
> `PYTHONHASHSEED`, to input key order, and to value-equal but text-different Decimal spellings.

### What is explicitly NOT claimed

- **Not** byte identity across Python versions. A different CPython release may change `Decimal`,
  `json`, or pydantic serialisation; the pinned digests hold for one interpreter version at a time.
- **Not** byte identity across platforms or architectures. Only same-interpreter, independent-process
  identity is instrumented.
- **Not** text-form invariance of the **frozen** layer's own fingerprints. `artifact_sha256` and
  `case_sha256` hash pydantic's JSON render, which preserves a `Decimal`'s written exponent — see §6
  hazard 2. Both digests are reported side by side rather than conflated.
- **Not** a proof of the frozen content seals. The presentation payload omits every `content_hash`
  field (text-form sensitive for the same reason); the seals are checked by the frozen
  `integrity_seal` gate, whose result travels **inside** the hashed payload.
- **Nothing** about persistence. No digest is a storage key and nothing is written to disk.

These are pinned in code (`PRESENTATION_HASH_IDENTITY_AXIS`, `PRESENTATION_NOT_CLAIMED`) and
asserted by `test_what_the_digest_does_not_claim_is_stated_plainly`, so the limits cannot drift away
from the claim.

---

## 6. Hazard mutations — what was mutated, and what was observed

A hash test that only proves "change a field, the hash changes" is worthless. Each of these mutates
the **hazard** — the mechanism by which two runs of the same review could disagree — and records
what was observed.

### Hazard 1 — a hidden wall-clock read

- **Test:** `test_hazard_1_reexecuting_at_a_different_wall_clock_changes_nothing`
- **Mutation:** run the identical presentation twice at two genuinely different real wall-clock
  instants (the test spins until `datetime.now(UTC)` has advanced and asserts it did), with the same
  injected `evaluated_at`.
- **Observed:** every byte identical — `presentation_json`, `presentation_markdown`,
  `presentation_sha256`, `artifact_sha256`. The failure this catches: any `datetime.now(UTC)`,
  `utcnow()`, `date.today()` or `time.time()` call anywhere on the chain would make the two runs
  differ. `test_no_module_on_the_presentation_path_reads_a_wall_clock` proves the absence
  structurally with an **AST** walk over every module in the package (not a text grep — the package
  docstrings *name* `datetime.now(UTC)` in order to say they never call it, and a grep would have
  reported a false positive there).
- **Companion:** `test_hazard_1b_a_different_injected_clock_moves_one_line_and_no_digest` injects an
  `evaluated_at` one day later. Observed: the digest is unmoved (a presentation stamp is not part of
  what was reviewed) and **exactly one** Markdown line differs — the `Evaluated at` line. The stamp
  is visible, not silently dropped.

### Hazard 2 — one value written several ways

- **Test:** `test_hazard_2_value_equal_text_different_decimals_do_not_move_the_digest`
- **Mutation:** rewrite three `Decimal`s value-equal but text-different — `182.4` → `182.400000`,
  `12.8` → `12.800000`, `1284.6` → `1284.600000` — and revalidate the whole case through the frozen
  contracts (every validator still passes: `Decimal` equality is value-based, so the bridge still
  reconciles exactly and every delta still equals the frozen computation).
- **Observed — and this is the finding:** the presentation digest and `presentation_json` are
  **unmoved**, while the frozen layer's `artifact_sha256` **and** `case_sha256` both **change**.
  Pydantic's JSON render preserves a `Decimal`'s written exponent, so `Decimal("0")`,
  `Decimal("0.000000")` and `Decimal("0E-6")` do not all render one way. Without
  `canonical_decimal_text` normalising first, "stable hashes for identical input" (plan `:308`) would
  have been false for the presented package, and silently so. The test asserts both halves: the
  guard holds, and the thing the guard exists for really does move.
- **Unit coverage:** `test_decimal_text_normalisation_gives_one_form_per_value` (11 written forms
  including `0E-6`, `-0`, `1E+2`) and `test_decimal_normalisation_is_value_equality_not_text_equality`,
  which asserts in the same breath that the raw `str()` forms differ — the hazard shown, not asserted.

### Hazard 3 — mapping iteration order leaking into an identity

- **Test:** `test_hazard_3_reordering_input_keys_does_not_move_any_digest`
- **Mutation:** rebuild every mapping — in the document payload **and** in the whole case — with its
  keys in reverse insertion order, then present it.
- **Observed:** `document_sha256`, `artifact_sha256` and `presentation_sha256` are all unmoved.
  Canonical JSON sorts keys at every level. The failure this catches is immediate and total: without
  sorted keys the reordered payload would not hash to its frozen record at all, and
  `verify_hashed_fixture_payload` would hard-fail the run before any review happened.

### Supporting instrument — independent processes

`test_digests_survive_independent_processes_under_hashseed_and_locale` runs the whole presentation in
two separate interpreters with different `PYTHONHASHSEED` values (`0`, i.e. randomisation off, and
`424242`, randomisation on) and different `LC_ALL` settings (`C` and `de_DE.UTF-8`), each subprocess
actually calling `locale.setlocale(LC_ALL, "")` so the locale really takes effect, in a scrubbed
environment with `HOME` pointed at an empty directory. Both reproduce every pinned digest exactly,
and the test asserts the two locales genuinely differed. A same-process repeat call would not have
been an honest instrument for a cross-process claim; this is.

---

## 7. Recorded for the governor — not blocked, not a new gap

One item would require editing a **frozen** file, so it was not done and is recorded instead.

**The frozen adapter's own fingerprints are `Decimal`-text sensitive.**
`adapter.artifact_output_sha256` / `AdaptedResultsReview.artifact_sha256` / `.case_sha256` hash
pydantic's JSON render, so two value-equal artifacts written with different `Decimal` exponents
produce different fingerprints (§6 hazard 2). `P2-05` did not change that — it normalises inside its
own layer and reports both digests side by side. Making the frozen digests exponent-invariant would
mean editing `adapter.py` (and, because `ContentAddressedContract.content_hash` shares the
canonicalisation, `decision_engine/types.py`), which is outside every constraint this mission
operates under.

Whether that matters is James's call, and it is genuinely arguable both ways: the frozen digests are
fingerprints of an exact serialisation, which is a defensible thing for them to be. It is recorded
here so nobody meets it as a surprise, and it is **not** a `G`-row and not a new gap identifier.

Related, already-tracked, and untouched: the per-element length cap on strings inside tuple fields,
noted in `adapter.render_artifact_markdown`'s docstring as tracked for a contract amendment. `P2-05`
adds no new exposure there — the presented package neutralises Markdown structure in every string it
interpolates, on top of the frozen renderer already doing so.

**JAMES_NEEDED items that blocked work: none.** No mission item required a frozen-file change to
complete.

---

## 8. Boundaries held

- No DB, no network, no migration, no persistence, no file write — `test_presentation_writes_no_file_anywhere`
  runs all four fixtures in an empty working directory and asserts it is still empty.
- No recommendation, rating, price target, size, order, portfolio instruction, or thesis mutation.
- CLAUDE.md rule **#11** (Model A quarantine) untouched — no model output enters this path at all;
  the artifact carries `model_independence=True`.
- s766B personal-advice firewall untouched — the presented verdict addresses the artifact and its
  analysis, and the reviewer's own scope statement travels with it verbatim.
- Decimal-only arithmetic; floats are unrepresentable (`canonicalise` hard-fails on one, as the
  frozen `hash_document_payload` already does).
- No file under `.claude/`, `.github/`, `docs/product/arbi-*.md`, `docs/product/memory/`,
  `roadmap-state.md` or `james-inbox.md` was touched.
