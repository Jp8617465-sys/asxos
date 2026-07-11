# Portfolio outcome ledger — memos → decisions → outcomes

**Status:** current · append-only
**Scope:** every decision-support memo arbi produced, what James decided, and how it turned
out. The learning loop for the portfolio capacity — the analogue of `decision-log.md` for the
infrastructure capacity.
**Last verified:** 2026-07-10
**Owner:** arbi appends a row when it produces a memo and when an outcome is known (P4,
reversible doc write); James records his decision. **Append-only — never delete a row.**
**Superseded by:** N/A

This is where the portfolio capacity *learns whether its memos were worth reading*. A memo
that James declined, or acted on and regretted, is **data** — it reshapes the next memo the
same way `decision-log.md` reshapes the next "one thing." The reward is **not** "# of memos"
or "James agreed with me"; it is: memos that were **model-independent, cited, inside policy,
and useful** — and, over time, whether acting on them beat the XJO benchmark after tax
(`benchmark-performance-analyst`). Agreement-seeking is an anti-goal (`arbi-scorecard.md`
anti-Goodhart): a memo that correctly says "REVIEW — evidence is thin, don't act yet" is a
good memo even though it recommends nothing.

Empty at seed: the P-ladder stands at **P0–P2 attended** today (`arbi-permission-model.md`),
and no P2/P3 memo has been produced-and-logged yet. The first `/pm-review` run that James
chooses to log appends the first row.

---

## Ledger (append below; newest at bottom)

| Date | Rec ref | Type · verdict | Model-independent? | James's decision | Execution note | Outcome (realised vs thesis · did the memo help?) |
|---|---|---|---|---|---|---|
| 2026-07-11 | `rec-2026-07-11-HUBS` | single-position · **REVIEW** | yes — HUBS has 0 Model A signal rows (US equity outside the ASX universe); confirmed | _pending James_ | none — ESPP-locked / non-disposable, monitor-only (thesis_revision #13) | _pending._ Verdict is data-integrity + framework, **not** performance: position ≈ flat (entry US$187.54 in-band → 205.95, +9.8% USD / ~+2% AUD), **not −29%**. The −29%/"stop violated" read was a `cost_base_normal` AUD-base-as-USD misread (→ risk R10). Acq-FX 0.6450 **confirmed vs brokerage statement** (James 2026-07-11). Discipline coverage **confirmed OK** — `check_us_positions` monitors `.NYSE` (breach fired 2026-07-03). Real items: 100% single-name concentration (~10× per-name cap); conviction_level NULL; stop 230 sits above entry 187.54 (mislabeled?); lock-end date still open. |
| 2026-07-11 | `rec-2026-07-11-CBA` | single-position (watchlist) · **REVIEW** | yes — no Model A signal/SHAP read for CBA | _pending James_ | none — `watching`, not held | _pending._ **DATA-BROKEN**: entry/stop/target 42–45/38/60 vs live 168.11 (~4× detached; never < 142 in 18mo) → would spuriously classify ABOVE TARGET. Revisit **14 days overdue** (due 2026-06-27). Rate-cycle idea coherent but not actionable (still watching; `rba_cash_rate` NULL in DB); `big-4-banks` theme holds zero exposure. |

Row shape: date · `recommendation_id` (→ the memo, per `recommendation-schema.md`) · type +
verdict · model-independence assertion (must be `model-independent` while rule #11 stands) ·
James's decision (acted / declined / modified) · what actually executed in his broker (if
anything) · realised outcome vs the thesis and an honest read on whether the memo helped.

## How arbi uses it

- **Read before producing a new memo on the same position** — check whether the last call on
  it held up. A pattern of declined or regretted memos on one name is a signal to change the
  approach, not repeat it.
- **Feeds the portfolio-capacity track record** — sustained useful, in-policy, model-independent
  memos are part of what would justify promoting P3 to standing autonomy
  (`arbi-permission-model.md` §Promotion preconditions). A memo that ever crossed the
  firewall (implied an order, used Model A while quarantined, breached policy) is a hard fail
  that blocks promotion.
- **Never rewritten by a dream** — a dream may summarise this ledger into a lesson, but the
  rows are immutable and outrank the summary.
- **Never a substitute for James's judgement** — the ledger records outcomes; it does not
  earn arbi the right to act on its own memos. That gap (P4 → P6) is permanent.
