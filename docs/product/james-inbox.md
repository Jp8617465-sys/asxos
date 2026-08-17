# James's inbox — the decisions only the governor can make

**Status:** current · living queue
**Scope:** the single place for decisions reserved to James (governor), not arbi (controller) —
capital, merge approval, migration approval, policy/conviction, broker execution. arbi surfaces
these; it never decides them.
**Last verified:** 2026-08-17 (two open dark-launch expiry rows appended; the three 2026-07
rows are unchanged and remain as the audit record)
**Owner:** arbi appends open items (I2, command-invoked) and marks them resolved once James rules;
James is the only one who closes a row by deciding. Append-only — never delete a resolved row.
**Superseded by:** N/A

Everything else arbi can sequence, draft, or dispatch inside its permission ladder
(`arbi-permission-model.md`). The five classes below are the ones that **only James** can settle,
because they commit real capital, cross an irreversible or governed boundary, or encode a value
judgement arbi has no standing to make:

| Class | Why it's James's | Examples |
|---|---|---|
| **Capital** | arbi never touches real money (firewall + rule #11). | position sizing, deploy/hold, cash floor changes |
| **Merge approval** | CODEOWNER review is the poisoning firewall; arbi never self-approves (`arbi-promotion-gate.md`). | any PR to `main`, dream promotions |
| **Migration approval** | schema is canonical + irreversible; applied via Supabase MCP, not by arbi. | new `migrations/*.sql`, backfills |
| **Policy / conviction** | value judgements (risk appetite, conviction numbers) are governor inputs, not derivable. | `conviction_level`, risk tolerance, quarantine calls |
| **Broker execution** | s766B firewall — the system never places or implies an order. | every real trade, ESPP disposal timing |

---

## Open items (arbi is blocked or best-effort-degraded until James rules)

| Item | Why it's James's | What arbi needs to proceed |
|---|---|---|
| ✅ **RESOLVED 2026-07-13 — HUBS concentration policy** (was: reframed 2026-07-12) | Policy/conviction. HUBS is **ESPP/employer stock** (James works at HubSpot); ruled as a **single-employer concentration ceiling**, not a 1–5 conviction (a rating is a category error for comp he didn't choose — `conviction_level` correctly stays NULL for HUBS). | **DECISION (James, 2026-07-13): soft-flag at 10% of investable capital, hard trim-trigger at 20%.** Employer-stock ceiling (matches the per-name cap; income↔wealth correlation argues for a tight leash). HUBS is currently **locked/unsellable**, so act by diluting with new capital and trim toward 10% when the window opens. **Enforcement DEFERRED to the roadmap** ("build later when it matters" — James): the ESPP marker + `employer_concentration_cap_pct` + the 10/20 flag fold into the `security_kind` enum build (`m14_candidate_security_kind_enum` / new `m14_candidate_espp_employer_concentration`). Live position at decision: 24 sh ≈ 7,175 AUD, **+2.8% AUD** (not the false −29%), **100% of portfolio** (sole holding, locked). Basis: portfolio-coherence-reviewer analysis 2026-07-13. |
| ⚙️ **RULED 2026-07-16 — CBA thesis #1: automate stale-thesis hygiene** (was: fix or retire) | James, 2026-07-16: "unsure why cba thesis is still a thing — it should be automated." Ruling read: a 4×-price-detached `watching` thesis should never sit in his inbox waiting for manual numbers — the discipline system should detect price-detachment and auto-move the row to a terminal/review state. | **Two actions:** (1) build the automation — a deterministic `price_detached` discipline check (entry/stop/target vs live price beyond a sanity band → auto-flag, and for `watching` rows auto-propose retire after N days unanswered); model-independent, evidence-only, same lane as `discipline.py`. Backlogged as the next discipline-evaluator increment. (2) The CBA #1 row itself: retire is the implied direction (not held, `watching`, no capital); executing the status write awaits a one-word confirm or lands as the automation's first live action. |
| ✅ **RESOLVED 2026-07-16 — VGS.AU / VAS.AU: NOT HELD; ETF Slice 2 proceeds without James data** (was: holding-lot data needed) | James, 2026-07-16: he does **not** hold VGS/VAS — they were named to exercise how non-equity instruments (ETFs) are treated end-to-end, not as real positions. The prior framing ("real positions not yet recorded") was wrong. | Nothing from James. ETF Slice 2 reframes to **clearly-marked demo/paper lots** (paper-trade lane or a flagged demo fixture — never `holding_lots`, which stays real-capital-only) exercising the full non-equity path: `security_kind='etf'`, kind-aware ingestion (Slice 2a, merged), ETF screening criteria (proposal 2026-07-12), CGT/distribution treatment. Unblocked — buildable now. |
| ⏳ **OPEN — dark surface #1, portfolio brief: expires 2026-08-31, needs a fresh verdict.** Decide by **2026-08-28**. | Capital-adjacent + policy. `dark-launch-exit-plan.md` gives the flip owner as **James**: the gate is `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` + `ASXOS_PERSONAL_USE=1`, and the surface's own re-scope condition is "model-independent cards + 4wk sign-off". arbi cannot flip a personal-advice-firewall gate. | One of **SHIP / DELETE / KEEP-DARK** with a new expiry. Per `dark-launch-exit-plan.md:152-159` an expired KEEP-DARK re-raises automatically and must earn a fresh verdict, not silently roll over. If KEEP-DARK: name the new date and what must be true by then. **Process note: this row is 5 vets overdue** — the expiry was surfaced by four consecutive `arbi-red-team` vets (2026-08-13 → 2026-08-17) and carried forward each time without being written here, which is the defect the file's own rule exists to prevent. |
| ⏳ **OPEN — dark surface #4, paper-trade evaluator: expires 2026-08-31, needs a fresh verdict.** Decide by **2026-08-28**. | Capital-adjacent. Flip owner **James**; the gate is "start the 4wk run", which `dark-launch-exit-plan.md:133` records as James's because it commits to a capital-adjacent evaluation. Re-raises together with surface #1. | One of **SHIP (start the 4wk run) / DELETE / KEEP-DARK** with a new expiry. Note the coupling: surface #1's own re-scope condition includes a 4wk sign-off, so a KEEP-DARK here likely forces a KEEP-DARK there — rule them together rather than separately. |

---

## How arbi uses it

- **Surface open rows every wake** in the brief's "Decisions needed from James" line — these are
  the items that gate real progress and that arbi *cannot* self-serve, distinct from the ranked
  next-action queue arbi can drive itself.
- **Never act as if a row is resolved** until James rules. A blocked capital/policy item stays
  blocked; arbi degrades best-effort around it (e.g. skips the conviction check) rather than
  guessing.
- **Close by deciding, not by deleting.** When James rules, mark the row resolved with the date
  and the decision, and cross-reference where it landed (`decision-log.md` /
  `portfolio-outcome-ledger.md` / the migration). Keep the row for audit.
