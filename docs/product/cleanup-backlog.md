# arbi cleanup backlog — roadmap + repo

**Status:** current
**Scope:** the prioritised cleanup work surfaced by the 2026-07-10 arbi scan (`wf_f54323f5-d7d`)
**Owner:** arbi tracks; work dispatched via `/arbi-run`; irreversible items need James
**Superseded by:** N/A

Every item is file-cited and tagged **[REV]** (reversible — arbi can do via `/arbi-run` +
review loop) or **[GATED]** (irreversible / boundary / precondition — needs James). Work
top-down; check items off in this file as they land.

---

## Roadmap / docs cleanup (6 — all reversible)

| # | Item | Tag | Owner |
|---|---|---|---|
| RM1 | Ground `roadmap-state.md` with a live `/arbi` wake — replace "Last wake snapshot: not yet established" with live-probed reality; split the collapsed "blocked at the foundation" row (the V2 thesis/brief layer is BUILT+dark-launched, not unbuilt) | [REV] | arbi (`/arbi`) |
| RM2 | Re-status the 4 `docs/strategy/` V2 + M-THESIS docs — their "What's missing" lists describe now-built code (`asxos/domain/{theses,themes,regime,underlyings,brief}/`); banner them "built, dark-launched, release-blocked" | [REV] | technical-writer |
| RM3 | Namespace the PR-numbering collision — `executable-roadmap` PR1-8 vs `roadmap-state` Kernel PR1-10 both use "PR 2"/"PR 7"; rename to EXEC-PR / KERNEL-PR | [REV] | technical-writer |
| RM4 | Re-status `executable-roadmap-2026-07-04.md` as historical/partly-superseded — its "read first" header is stale and it omits the entire arbi layer | [REV] | technical-writer |
| RM5 | Refresh `docs/README.md` — bump "Last verified"; add an authoritative-source row for the `docs/strategy/` V2 specs | [REV] | technical-writer |
| RM6 | Collapse the triplicated Phase 0-2b "Done" narrative (backlog == roadmap-state == handoff) to one authoritative list; give non-slug deferrals a central home beside the 7 `m14_candidate_` slugs | [REV] | technical-writer |

## Repo / code cleanup (10)

| # | Item | Tag | Owner |
|---|---|---|---|
| R1 | Tighten rule #11 wording (`CLAUDE.md:25`, handoff) — "candidate scans" implies a durable blocked component; glob shows none (one-off ad-hoc scan). **Boundary edit — arbi drafts, James approves** | [GATED] | technical-writer → James |
| R2 | Add a reliability-vs-approval caveat (`portfolio-conventions.md`, `roadmap-state.md`) — `approved_for_allocation` verifies deliberate approval, NOT reliability, so it does NOT enforce rule #11 | [REV] | technical-writer |
| R3 | **R9 fix** — make the brief's Model A driver line best-effort so 0 approved models skips the cosmetic line instead of hard-failing (`compose.py:190`, `active_theses.py:72-92`); revoking approval today hides ALL thesis cards | [REV] (code+review) | backend-architect |
| R4 | Label `compute_opportunity_cost`'s signal-driven ranking non-authoritative under rule #11 (or suppress while disputed) — the midpoint fallback already exists (`:60-66`) | [REV] (code+review) | backend-architect |
| R5 | Extract one shared CGT 30-day boundary helper — duplicated across `positions.py:91/:185`, `compose.py:317`, `tax_operational.py:38` | [REV] (code+review) | refactoring-expert |
| R6 | Consolidate the dual regime source onto the independent `market_context_current.regime_label` — V1 reads Model A `signals.regime` (`compose.py:204`), a display-only Model A leak | [REV] (code+review) | backend-architect |
| ~~R7~~ | ~~Audit orphaned non-`.AU`/`.US` thesis rows (e.g. HUBS.NYSE) — discipline-coverage hole~~ — **RESOLVED (audit done 2026-07-11):** no hole. `check_us_positions.py` matches all `FOREIGN_SUFFIXES` via `foreign_symbol_sql` and is scheduled (`render.yaml:643`); `check_au_positions.py` handles `%.AU`. Between them all live theses are covered — the HUBS breach fired 2026-07-03. See cleanup RC5 | [REV] done | arbi (verify) |
| R8 | Schedule `m14_candidate_agent_db_role_scoping` before Phase 2c — a read-only Postgres role for agent MCP sessions; prompt-only SELECT is exploitable adjacent to governed tables (also the Managed Agents §5 precondition) | [GATED] (security precondition) | security-engineer |
| R9 | Resolve the two parallel brief trees (`asxos/brief` V1 live vs `asxos/domain/brief` V2 dark) — pick ship-or-abandon, delete the loser; the composer keeps both via a runtime fallback (`composer.py:89-98`). Architectural — decide first | [GATED] (architectural) | system-architect → James |
| R10 | Batch the P3 DB tidy-ups as one migration — drop `archive_dropped_20260628`, orphaned trigger functions, `public.schema_migrations` | [GATED] (irreversible migration) | backend-architect → James |

## Portfolio-review findings (2026-07-11 `/pm-review` HUBS + CBA)

Surfaced by the first live P2 review (5 model-independent analysis agents, adversarially
reconciled). Cited in `portfolio-outcome-ledger.md` (2026-07-11) and risk-register R10/R11.

| # | Item | Tag | Owner |
|---|---|---|---|
| RC1 | **Disambiguate `cost_base_normal` currency** (risk R10) — it holds the AUD tax base for foreign lots but reads like a native cost; 2/5 agents misread HUBS as −29%. Add a `cost_base_ccy` marker or split `_aud`/`_usd`. HUBS acq-FX (0.6450) **confirmed vs brokerage statement 2026-07-11** — not an error; only the labeling remains. Interim [REV] doc note **DONE** (`portfolio-conventions.md`); clean fix is a migration | [GATED] (schema/migration) | backend-architect → James |
| RC2 | **Fix or retire CBA.AU thesis #1 price ladder** — entry/stop/target 42–45/38/60 vs live 168.11 (~4× detached, never < 142 in 18mo); would spuriously classify ABOVE TARGET. Correcting the levels is a governed thesis revision (service + `governance_events`) | [GATED] (governed-table write) | backend-architect → James |
| RC3 | **Repair `market_context_current` feed gaps** — `rba_cash_rate` NULL (the bank rate-cycle thesis's own trigger isn't populated) + ingest 404s: iron ore `IRON.COMM`, `VIX.US`, `AUCBCNTO` (400) | [REV] (code+review) | backend-architect |
| RC4 | **Backfill `conviction_level`** (risk R11) — NULL on all 13 theses disables the conviction-vs-size check portfolio-wide; consider requiring it on `enter_thesis()` | [GATED] (data backfill) + [REV] (guard) | backend-architect → James |
| ~~RC5~~ | ~~Suffix-aware discipline coverage~~ — **RESOLVED / not-a-bug (verified 2026-07-11):** `jobs/check_us_positions.py` already covers every foreign suffix via `foreign_symbol_sql` (`.US/.NYSE/.NASDAQ/.AMEX`, HUBS.NYSE named in its docstring) and **is scheduled** (`render.yaml:643`) — that is how the HUBS stop breach auto-fired 2026-07-03. No coverage hole; the earlier assumption (and R7) was stale. Residual (minor, not coverage): the thesis-construction oddity (stop 230 *above* entry 187.54 — is 230 a stop or a mislabeled level?) and benchmark-appropriateness (XJO wrong for a single USD tech name) — both thesis-data items, folded into the HUBS outcome-ledger row | [REV] done | arbi (verify) |

## Suggested execution order

1. **Now, arbi-dispatchable (reversible docs):** RM2–RM6, R2 → one `/arbi-run` pass to
   `technical-writer`. RM1 = a live `/arbi`.
2. **Code fixes (specialist + review loop):** R3 (the R9 trap) first — it's the one with a
   live failure mode — then R4, R6, R5, R7.
3. **Gated / James's call:** R1 (rule #11 wording draft), R8 (DB role scoping — also unblocks
   Managed Agents + Phase 2c), R9 (dual brief trees decision), R10 (DB migration). R1's
   wording and R8 both intersect the Model A P0.

Note: none of this is the P0. **The single highest-leverage action remains the Model A decay
check** (`the_one_thing`, scan `wf_f54323f5-d7d`) — this backlog is the cleanup that rides
alongside it.
