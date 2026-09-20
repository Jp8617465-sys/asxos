# Session handoff — 2026-09-20, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-19-routine.md`. Routine handoffs
carry `-routine`; interactive ones keep the bare date.

**STOP — read first.** Rule #11 stands; nothing here read `signals`. **#327 is now labelled
`incident`**, which means **tomorrow's gate (b) will fail on it and force it as the one thing.**
That is deliberate. Its substance is settled — the vendor does not serve the data — and what is
left is a watchdog-semantics design question filed as **E-30**, not a code fix. Read E-30 before
touching `check_cron_health`.

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
**2026-09-20T17:31:09Z**, `doc_sha=66b0273`, budget 120 min.

**The first of five fires not held in plan mode.** START posted at 17:32:46Z, T+2, and the fire
ran inside budget as a direct result. The four before it were held 24 min, 5 h, 2 min (plus a
3.5 h suspension mid-fire), and released only by James noticing. Nothing in the repo changed to
achieve this; the standing item is still his.

**Gate:**

| gate | result |
|---|---|
| halt | clean — 0 `routines-halt`, 0 `HALT:`-titled among 11 open issues |
| (a) `nightly-check` on `main` | **`success`** — `35519499213`, scheduled, head `66b0273` |
| (b) no open `incident` issue | **passed as written, and that was the bug.** 0 labelled — while **#327 sat open and unlabelled**. Fixed tonight by labelling it |
| (c) no dangling ledger START | clean — `weekly-security` START 12:01:56 / END 12:08:40 matched |
| (d) ready item | (d).1 six open PRs, **none on `claude/routine-*`** → (d).2 picker exit 0, eligible 6, pick **A-35**. Amendment K: the capability-audit block says the head is "unchanged — A-35 → E-20 → E-21". Agreed |

## The one thing — A-35

Dark-launch DELETE verdict #3 (issued 2026-09-14), executed. Gone: the
`ASXOS_V2_BRIEF_ENABLED` branch in `composer.py`, `render_v2_html()`, the frozen
`_archive/brief_v2.html.j2` and its README, `tests/test_brief_v2_caveat.py`.

**Measured before deleting**, per the A-34 precedent — the flag was set in **no** workflow,
Makefile, `.toml` or env example, so the V2 template **never rendered once**. The ten collectors
are untouched and still in production, exactly as the verdict required.

**The branch was removed, not defaulted off.** An `if` that always takes the same arm is still a
gate someone can flip; the point of the verdict was to remove the choice. A test asserts the
`ast` of `composer.py` contains no read of the name.

### The surface was wider than the row's `paths:` — second consecutive night (L61)

Three things the row did not name, and one correction:

1. **The frozen template *and its README*.** That README said the copy existed *only* while the
   dark renderer could load it. Leaving it would be an archive nothing can render.
2. **`tests/test_domain_purity.py`'s shrink-only allow-list.** Removing the `jinja2` import made
   `renderer.py`'s entry stale, and **that gate fails in both directions by design** — it caught
   it. The mechanism working, not a nuisance.
3. **A dead `import os`**, which only `ruff` found after the branch went.
4. **`renderer.py` claimed `render_html` was "used by `jobs/compose_brief.py`".** It is not —
   that job imports the identically-named function from `asxos.brief.compose`. The domain one
   has **no production caller at all**. Corrected in the module rather than left to mislead.

## #327 — labelled, and my remedy withdrawn

**The detector was lying.** #327 has been open and unlabelled since 2026-09-17, so
`list_issues(labels=["incident"])` returned 0 and gate (b) reported clean over an open incident
on every fire since. Now labelled.

**And the remedy I proposed for it last night is withdrawn.** I wrote "make `build_decision_case`
report rather than raise". On inspection that runs straight into **CLAUDE.md #10** — *no graceful
warnings in infra code, fail loudly* — and the builder **already** reports loudly; the DEGRADED
note *is* the report. The real defect is that `check_cron_health` has exactly one state for
"degraded" and no way to say "known, permanent, already triaged", so it pages nightly on a
condition nobody can fix and trains its reader to ignore it.

Filed as **E-30**, `route=attended`, because the design choice is real: an acknowledge/suppress
mechanism can hide a genuine regression behind a stale acknowledgement, so it needs an
expiry-and-re-raise rule — closer to the dark-launch expiry discipline than to a mute button.

**Catching this before shipping it is the useful part.** Softening a hard-fail because it is
inconvenient is how watchdogs die.

## Verification

- `make check`: **4785 passed / 19 skipped**, ruff clean, mypy clean on 238 source files.
- `tests/test_v2_brief_gate_is_gone.py` **mutation-verified**: reintroducing the gate turns 2 of
  its 6 red; reverting restores green. The detector itself has an inline probe so the absence
  assertions cannot pass vacuously.
- Picker seed re-pinned `["A-35","E-20","E-21"]` → `["A-51","E-20","E-21"]`, and A-51 **left the
  skipped list by promotion**, not by being dropped — it was only ever skipped for overlapping
  A-35. The pin caught both halves.
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **The permission mode.** Tonight worked, but nothing changed to make it work. Five fires, four
  held. `get_session` still reports `plan`/seq 844 and cannot diagnose it either way.
- **C-13** — still the single highest-value item in the repo and still arbi-impossible. The
  ruling-ready proposal has been on `main` since 2026-09-07.
- **#342**, **#334**, **#319** — all `.claude/`, all drafted for you.
- **K-08** — `deadman=unset` again.

## Next fire

**Gate (b) will now fail on #327** and hand it over as the one thing. The right response is
**E-30's design question**, not a code change to the builder — read E-30 first. If you judge
that attended-only (it is `route=attended`), fall through to **A-51**, then E-20, then E-21.
