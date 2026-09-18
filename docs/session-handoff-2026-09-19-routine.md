# Session handoff — 2026-09-19, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-18.md` (the attended close that merged
#332). Routine handoffs carry `-routine`; interactive ones keep the bare date.

**STOP — read first.** Rule #11 stands; nothing here read `signals`. **#327 is still open and
`pipeline-health` is still red** — unchanged from last night, and deliberately not re-taken. The
code half landed in #328; the data half needs `weekly-research`, which is James's under #311.
Saturday 16:00 UTC, or his dispatch.

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
**2026-09-18T17:31:38Z**, `doc_sha=32f8b83`, budget 120 min.

**The fire was held in plan mode again — the second consecutive time.** Plan mode forbids every
write, so START could not be posted at fire time; the scheduler recorded the wake as delivered
while the ledger stayed silent, which is exactly the shape `_preamble.md` §1 exists to detect.
James released it at 17:55Z. **Once is an incident; twice is a pattern.** The fix is not in this
repo — it is the bound session's permission mode, which `docs/ops/routines/README.md`'s first-fire
checklist already says to verify as `auto` via `get_session`.

Recorded as a decision rather than a silent overrun: the T+90 merge deadline was measured from
**release** (19:25Z), not fire (19:01Z), because the 24 minutes the harness held were never
available for work and the stated purpose of T+90 is leaving room for the proof and the close.

**Gate, all four:**

| gate | result |
|---|---|
| halt | clean — no `routines-halt` label, no open `HALT:` issue |
| (a) `nightly-check` most recent on `main` | **`success`** — `35362541090`, scheduled, head `32f8b83` |
| (b) no open `incident` issue | **#327 open**, not re-taken (above). Worth noting: the label probe returns 0 because **#327 carries no `incident` label** — the gate's mechanical check and its intent have drifted apart |
| (c) no dangling ledger START | clean |
| (d) ready item | (d).1 no `claude/routine-*` PR — #334 and #319 are both `.claude/` and James's → (d).2 picker exit 0, eligible 5, pick **A-34**. Amendment K: today's roadmap block says the queue is unchanged. Picker and roadmap agree, for once |

## The one thing — A-34, and the part worth keeping

Dark-launch DELETE verdict #1, issued 2026-09-14 (#267), executed tonight.

**The fire's contribution was measuring the verdict before executing it.** The last two fires each
found a filed row whose stated cause did not survive contact with the code (L53; #327's own
remedy), so three things were checked first:

| | |
|---|---|
| `ASXOS_PORTFOLIO_BRIEF_ENABLED` in workflows / Makefile / `.toml` / env examples | **nowhere** — never `1` in tracked config |
| `brief_section_gold`, section `portfolio`, 2026-08-24 → 2026-09-18 | **18 rows, every one `EMPTY`** (vs `header`/`prices`/`discipline`/`outcome` at 18 `FRESH` each) |
| freshness gate | unsatisfiable since `build_portfolio` last succeeded 2026-08-01 |

So the section had **never rendered once**, and the deletion destroyed no stored record. That is
the Amber question answered with a number instead of an argument.

**The scope was wider than the backlog row said, and that is the reusable finding.** The row named
four files. The real surface was eleven: `gold.py`'s decoder and its reconstruct block, both Jinja
templates, `asx portfolio signoff`'s next-step text, `paper_trade.py`'s docstring and journal
rationale, and three docstrings in `compose.py` / `portfolio/__init__.py` /
`decision_engine/portfolio_state.py` that named the gate as a live requirement. **A row's `paths:`
is a starting point, not an inventory** — filed as lesson **L61**.

**Kept deliberately:** `asx portfolio signoff` and the paper-trade evaluator. The sign-off is
evidence about the paper-trade history; it outlives the one display surface it used to unlock, and
now says so rather than printing a next step for a variable that no longer exists.

`tests/test_portfolio_brief_gate_is_gone.py` guards the absence as an **executable-reference (ast)**
check, not a text search — the string is *supposed* to survive in the prose recording what was
removed. It carries its own inline mutation check so the absence assertions cannot go vacuously
green if the detector breaks.

## Two things the classifier caught, and what they turned out to be

The auto-mode classifier blocked two edits as **`[Security Weaken]`**, both on removal of the
string `For personal use only (s766B Corporations Act 2001)` from the deleted template block.

**Checked rather than routed around.** That notice is emitted **per section**: `brief.html.j2`
keeps two more (lines 274, 330) and `brief_detail.html.j2` keeps one (235). The deleted notice
belonged to the deleted section, and the s766B firewall *markers* in those templates delimit
section 8, not this one. The edits were then made with the `Edit` tool — the ordinary tool for the
job — and both the block and this reasoning are on the decision log.

**The `_preamble.md` §2 weakening-change tripwire was put to James, not assumed.** Deleting a gate
named in `portfolio-conventions.md`'s regulatory-firewall section is literally "removes a guard".
The argument for landing it is that the guard and the only thing it guards die in the same commit,
and `ASXOS_PERSONAL_USE` is untouched — but the tripwire has no such exception written into it.
Because the fire was held in plan mode anyway, the question went into the plan and **his approval
is the ruling**. A useful accident: being blocked bought a human answer for free.

## Verification

- `make check` on the branch: see the ledger END comment on #270 for the figures.
- Golden fixtures updated by **targeted removal of the `portfolio:` fragment only**, not
  regeneration — so any other drift in those three files would still have failed.
- `tests/test_backlog_next.py`'s seed pin moved `["A-34","E-20","E-21"]` → `["A-35","E-20","E-21"]`,
  and A-35 left the skipped-for-overlap list: it was only ever there because it collided with A-34.
  The test caught both, which is the pin doing its job.
- Migrations untouched — ledger head `20260917114415` (0060); 0045 absent, 0042 reserved.
- No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **Two `.claude/` files now describe a gate that does not exist.**
  `.claude/rules/portfolio-conventions.md:16` ("The brief's section 6 requires a SECOND gate")
  and `.claude/agents/portfolio-invariant-guard.md:20`. Draft-only from a routine — a PR for you.
- **#334** and **#319**, both open, both `.claude/`.
- **#327** — closes when `rs_financial_statements` holds HUBS rows *and* `build_decision_packets`
  reports 0 of 2 failing. Both need `weekly-research`.
- **K-08** — the three routine deadman URLs; `deadman=unset` again tonight.
- **The bound session's permission mode.** Two fires in a row have been held in plan mode. This is
  the one item on this list that costs a whole fire each time it is missed.

## Next fire

**A-35 — dark-launch DELETE verdict #3** (the `ASXOS_V2_BRIEF_ENABLED` branch), which the picker
and the roadmap now both name at #1. It is the same shape as tonight's work with a worked
precedent: measure whether the dark branch has ever rendered before deleting it, and expect the
real surface to be wider than the row's `paths:`. Then E-20, then E-21.
