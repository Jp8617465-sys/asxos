# James's inbox — the decisions only the governor can make

**Status:** current · living queue
**Scope:** the single place for decisions reserved to James (governor), not arbi (controller) —
capital, merge approval, migration approval, policy/conviction, broker execution. arbi surfaces
these; it never decides them.
**Last verified:** 2026-07-11
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
| **CBA thesis #1 — fix or retire** | Policy/conviction: the recorded entry/stop/target (42/45/38/60) is ~4× detached from live ~168 (CBA never traded < 142 in 18 months) and would spuriously classify ABOVE TARGET. Only James can say whether the rate-cycle idea still holds or the row should die. | Either (a) the **correct entry / stop / target** for CBA at today's ~168 level, or (b) an explicit **retire** — arbi records either via `asx thesis` and clears the 14-day-overdue revisit (due 2026-06-27). Not held (`watching`), so no capital moves either way. |
| **VGS.AU / VAS.AU holding-lot data** — real positions not yet recorded | Capital + broker execution: the actual quantities, cost bases, and acquisition dates are facts only James holds (from his brokerage statement); arbi cannot fabricate lots that drive CGT and portfolio math. | Per lot: **quantity · cost base · acquisition date** (and acquisition FX if not AUD — see risk R10). Then ETF Slice 2 can record the real passive positions and the multi-instrument product runs on true holdings, not placeholders. Records to `holding_lots`. |

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
