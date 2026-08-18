# asxos — Session handoff — 2026-07-18

**Status:** current
**Read priority:** read first (newest handoff; supersedes `session-handoff-2026-07-17.md` on priority)
**Owner:** arbi (`/arbi-close`)
**Session:** 2026-07-17 (continuation) → 2026-07-18 — arbi operating session (attended + James-authorized merges)

---

## STOP — read first (live P0)

**Rule #11 — Model A quarantine STANDS.** Do not use Model A output (signals, candidate
scans, allocator runs, new thesis proposals) as a basis for real-capital decisions. Resolved
against Model A 2026-07-11 (`docs/model-a-decay-analysis-2026-07-11.md`: no usable edge on
19,032 matured signals; conviction inverted at the top). Standing policy for v1_5 — stays in
this block and in `CLAUDE.md` #11 until a *new* model version passes a pre-registered decay
bar (positive, monotonic conviction→21d return) AND earns `approved_for_allocation`.

The product remains the **model-independent moat** (discipline, tax, themes, ETFs, governance).

---

## What shipped this session (all merged to `main`)

Nine PRs merged (main `f89f77f` → `0099756`). CI green (`full-check` + `targeted-ml-tests`)
on every merge; ~1681 tests.

| PR | What | Class |
|---|---|---|
| #55 | Retire dead Treasury RSS feed (RBA-only); `assert_partial_success` 0.5→1.0 (N=1 fail-loud) | ranked-queue #1 (mission) |
| #56 | **ThesisProposal keystone schema** (`asxos/domain/theses/schemas.py`) — broker-report Phase B | broker-report arc |
| #57 | Gate `tax-view`/`tax-action` behind `_require_personal_use()` (R14 firewall) | firewall |
| #58 | Personal-advice firewall amendment — **PROPOSAL doc** ("advise + stage orders") for ratification | governance (proposal only) |
| #50 | Idea-generation lane — `theme --from-agent-run` + sector-screener + first dry run | discovery (prior-session draft) |
| #48 | Dream promotion → approved lessons L8–L16 | **James's own merge** (promotion gate) |
| #59 | **Firewall-gate hardening** — `journal.py` (HIGH R14) + 4 personal-data jobs, shared `require_personal_use_job()` | audit P0 |
| #61 | `theme_dashboard` reads `governed_active_*` views (retired/draft no longer shown as approved) | audit P1 (also closes #50 follow-up #1) |
| #62 | **Redact EODHD/FRED API keys** from `job_runs`/logs/`ingestion_warnings` (source-level fix) | audit P1 (CWE-532) |

**Security + refactoring audit (James-requested):** ran read-only via multi-agent workflow.
Attempt 1 hit the **session spend limit** (3 of 5 agents died); the **re-run completed all 6
lenses, 0 errors** (firewall-coverage, governance/injection, secrets, refactoring, performance,
behaviour-simplification). **P0 empty** (genuine — only `/health` is public, Model A shelved).
Full findings folded into the roadmap backlog below.

---

## The audit backlog — next-session queue (P1 → P2)

**P1 (reversible; execute in order):**
1. **`compute_opportunity_cost`** firewall gate — the one personal-data job #59 didn't cover.
   Needs the in-code `require_personal_use_job()` **paired with** a `render.yaml`
   `ASXOS_PERSONAL_USE=1` env add (the guard alone would break its Saturday cron on deploy).
   → deploy-config change; do via the GitHub-API route, attended.
2. **`compose_brief`** top-level `ASXOS_PERSONAL_USE` gate — self-gates each section at the
   data layer today (not exposed), a defense-in-depth hardening.
3. **Quick-fix queue** (small, safe, behaviour-preserving — batch into one draft PR):
   RSS `title[:500]` cap · `active_theses.py:110` dict-comprehension · `_portfolio_section`
   single-pass (`brief/compose.py:615`) · `upsert_events` comprehension (`regulatory.py:198`) ·
   `defusedxml` swap (`regulatory.py:58`) · `security_master.py:98` → `executemany` ·
   `/health` generic 503 body · dead params (`exit_price`, `theme_id`).
4. **Brief thesis collectors** governance filter (`active_theses`/`watchlist`/`new_ideas`/
   `_discipline_findings` — add `governance_status='approved'` defense-in-depth).
5. **P2 refactors** (behaviour-preserving): `create_*_from_agent_run` guard-preamble ×3 →
   `_load_unacted_run`/`_mark_run_acted`; governance approve/reject skeleton ×7; N+1 cron
   loops (`security_master`, three position/thesis crons, `track_signal_outcomes`).

**P2 — RED ZONE / requires James (draft or decision only; arbi does not enact):**
- **Agent read-only DB role — finish the wiring.** Migration 0039 (`asxos_agent_ro`) is
  **applied** and the `supabase-ro` MCP is **live** (connects as `supabase_read_only_user`).
  The remaining step is repointing the 6 discovery/analysis agents' frontmatter
  (`.claude/agents/*.md`) from `mcp__Supabase__execute_sql` → `mcp__supabase-ro__execute_sql`.
  This is the mechanical fix for `m14_candidate_agent_db_role_scoping` (risk-register R2) and
  **subsumes** the audit's "governance triggers are UPDATE-only → direct-INSERT bypass" gap.
- **`ASXOS_API_TOKEN` bearer is documented but never enforced** (`config.py:39`, empty default;
  `api/main.py` wires only `/health`). Non-exploitable today (no sensitive route) — but
  implement the dependency *before* any portfolio/tax route lands, **or** correct the docs to
  say "currently unenforced." Governor call.
- **Render `curl` allow-pattern trailing `:*` wildcard** (`.claude/settings.json`) — auto-approves
  state-changing Render verbs behind a read-only-looking entry. Tighten or ratify deliberately.
- **`joblib.load` on git-tracked model pickles** (`cache.py:97`) + **`signal.py`/`predict.py`
  advice-exemption doc** — lower-priority hardening/doc decisions.

---

## Pending, requiring James

- **Firewall amendment (#58) enactment.** The proposal is merged; the enacting ~15-file
  RED-ZONE edit (all synchronized circuit-breaker copies together, per red-team) is **gated on
  your explicit go-ahead**. The **model-independent sizer** (unblocks sized-order staging) is
  unbuilt — advice + price/lot staging can ratify before it.
- **`james-inbox.md` standing items** — HUBS concentration policy (ESPP, not conviction), CBA
  thesis #1 fix-or-retire, VGS/VAS holding-lot data (unblocks ETF Slice 2).
- The **P2 RED-ZONE list above** — each is a decision or a RED-ZONE edit only you enact.

---

## State at close

- **Open PRs: 0.** All merged or closed (#60 closed — superseded by this handoff's backlog).
- **main:** `0099756`. **Migrations:** 39 on disk (0039 applied; observed DB count 93,
  `REQUIRED_MIGRATIONS=93`).
- **Tests:** ~1681 collected; local run 1678 passed / 2 xfail. The `test_train_walk_forward`
  failure + 16 collection ERRORs are the documented sandbox lightgbm/joblib gaps — **pass on CI**.
- **Boundaries held:** every code change shipped through a draft PR + review loop; all merges
  were James-authorized ("merge all PRs if green" / "merge all safe to merge"); the dream
  promotion (#48) was James's own click (arbi never self-approves — `arbi-promotion-gate.md`);
  no DB writes, no Render mutations, no migrations, no capital action, rule #11 untouched.

🤖 arbi `/arbi-close` — 2026-07-18
