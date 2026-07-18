# Personal-Advice Firewall — Amendment for Single-User Direct Advice + Order Staging

**Status:** proposed — DRAFT for James's ratification (a boundary change to a non-negotiable; per
`arbi-constitution.md` §reserved authorities, arbi may only draft this, never self-enact it)
**Scope:** redefines the s766B personal-advice firewall for the single-user reality. Does NOT
touch rule #11 (Model A quarantine — a separate axis), the no-autonomous-execution line, or the
single-user/no-distribution constraint.
**Last verified:** 2026-07-18 (wording checked against the cited files this session)
**Owner:** arbi drafts; James ratifies by merging the authority-file PR this doc specifies
**Superseded by:** N/A

---

## 1. What James decided (the grant this amendment implements — no broader)

James (governor), 2026-07-18: *"I do want it to be personal advice for just me."* Scope chosen via
AskUserQuestion: **"Advise + stage orders"** —

- The system gives **direct, tailored personal advice** to James: a real recommendation
  (buy / hold / trim / exit) reasoned to his situation and objectives, with conviction — not a
  hedged "here's evidence, you decide" summary.
- The system may **stage specific orders** — sizes, prices, tax-lot selections — prepared up to
  the broker's door, for James to review.
- James **reviews and places every order himself.** Autonomous execution was explicitly NOT
  chosen (it was offered as a separate option and declined for now).

This amendment implements exactly that grant and nothing beyond it. Anything wider (the system
placing trades / touching a broker) remains out and would need its own, separate governor
decision with its own guardrails.

## 2. Key finding — this is a reconciliation, not a teardown

The north star's firewall is **already drawn at execution, not advice.** `north-star.md`
non-negotiable #2 verbatim: *"The firewall is **execution, not analysis** — it never places an
order, moves capital, or represents itself as licensed advice … arbi allocates on paper; James
acts in reality."* And the P-ladder (`arbi-permission-model.md`) already produces **allocation
memos** — "the gap between the best memo (P4) and one dollar moving (P6) is James reading it."

So the constitution's boundary already permits direct decision-support James acts on. What
actually contradicts the grant is the **surfaces over-hedging against that boundary** — most
sharply `pm-review.md`: *"never give personal financial advice … even for a single user"* and
*"no 'you should buy/sell N shares'."* That is stricter than the north star requires. This
amendment reconciles the surfaces to the boundary and adds the one genuinely new element
(order staging), keeping every safety line intact.

## 3. The boundary after this amendment (canonical)

| Capability | After amendment |
|---|---|
| Direct, tailored advice to James (buy/hold/trim/exit **as a recommendation**, reasoned to his situation, with conviction) | **IN** — new |
| Staging specific orders (sizes, prices, tax-lot picks) prepared to the broker's door | **IN** — new |
| System places an order / moves real capital / touches a broker | **OUT** — unchanged. James reviews and places every trade. P6 stays: no execution tool is ever mounted. |
| Surfaced / distributed to / represented to anyone but James | **OUT** — unchanged. Single-user; `ASXOS_PERSONAL_USE` gate stays and is now load-bearing for exactly this. |
| Represents itself as licensed / AFSL advice | **OUT** — unchanged. Not licensed; single-user self-advice needs no licence. |
| Model A signal/score/rank as a *basis* for a recommendation | **OUT** — unchanged (rule #11 standing; separate axis, untouched by this amendment). |

The one-line reframe: the firewall protects against **executing** and against **multi-user /
distributed / licensed-representation** advice — NOT against the single authorized user
receiving direct advice and staged orders he places himself.

## 4. Exact before/after per authority file (the ratifiable change)

Each of these is a RED ZONE authority file — the edits land via the GitHub-API draft-PR route,
never a local edit, per the established pattern. This doc is the rationale that rides with them.

### 4.1 `docs/product/north-star.md` — non-negotiable #2
- **Keep** the "execution, not analysis" line verbatim (it already draws the right boundary).
- **Add**, after "allocation memos James reads and acts on": *"For the single authorized user,
  the system speaks in the register of direct personal advice — a recommendation with
  conviction, and staged orders (size, price, tax-lot) prepared for James to review and place.
  The firewall is that James executes every order himself (P6, no broker tool is ever mounted),
  that nothing is surfaced to or represented to any other person, and that nothing represents
  itself as licensed advice. Advice to the one user is inside the line; execution and any
  second recipient are outside it."*

### 4.2 `.claude/commands/pm-review.md` — the sharpest contradiction
- **Replace** *"you never place an order and never give personal financial advice (the
  regulatory firewall … is structural, even for a single user)"* with: *"you give James a
  direct recommendation and may stage the orders to act on it; you never place an order or move
  capital yourself — James reviews and executes every trade. The firewall is execution and
  distribution, not advice-to-the-one-user."*
- **Replace** the boundary line *"No order placement, no 'you should buy/sell N shares', no
  price target you invent"* with: *"No order placement or capital movement (James executes).
  You MAY say 'buy/trim N shares at $X, using tax-lot L' as a staged recommendation. Every
  figure still traces to a cited source — a staged price/size is derived from cited holdings +
  Decimal arithmetic, never an invented number (the cite-everything rule is unchanged)."*
- Verdict labels may become directive (a recommendation), not merely "a summary of evidence."

### 4.3 `.claude/rules/portfolio-conventions.md` — §Regulatory firewall (Part 0 Q1)
- **Keep** the `_require_personal_use()` / `ASXOS_PERSONAL_USE` gate exactly — its mechanism is
  now the load-bearing enforcement of "single user only."
- **Reframe** its rationale: from *"preventing personal-advice outputs from being surfaced in a
  multi-user context"* to *"confining direct personal advice and staged orders to the single
  authorized user (`ASXOS_PERSONAL_USE=1`); the firewall is multi-user surfacing + execution,
  not advice to that one user."*

### 4.4 `docs/product/arbi-permission-model.md` — the P-ladder tripwire (lines ~195-197)
- **Amend** the halt-tripwire *"capital-impacting action (executing, or a memo that implies an
  order rather than a proposal James decides on)"* to: *"capital-impacting action — the system
  executing, moving capital, or routing to a broker. A **staged order James reviews and places**
  is the authorized advice+staging register, NOT a tripwire; an action that **executes** one is."*
- **P6 (Execute) stays exactly as written** — "not a tool arbi holds," never promotable. The
  staging register lives at P4/P5 (a richer memo), not P6.

### 4.5 `docs/product/portfolio-manager-charter.md` — "a recommendation is not an order"
- **Keep verbatim** — it is now the precise safety principle: a staged order IS the
  recommendation; James placing it is what makes it an order. Add one clarifying sentence that
  staging specific sizes/prices/tax-lots is still a recommendation, not an order, because
  nothing executes until James does.

### 4.6 `CLAUDE.md` — firewall references
- Update any line that frames the firewall as "no personal advice" to the "execution +
  distribution, not advice-to-the-one-user" wording, for consistency with #4.1.

### 4.7 `docs/product/arbi-constitution.md` — line ~53
- **Keep** "neither may cross the s766B firewall or rule #11." The firewall is being
  *redefined by the governor*, not *crossed by arbi* — this line stays true under the new
  definition. No edit needed beyond confirming it references the amended definition.

## 5. What explicitly stays OUT (so the grant isn't over-read)

- **Autonomous execution.** No broker tool, no order placement, no capital movement — ever, by
  this amendment. P6 unchanged. A future move here is a separate governor decision.
- **Any second recipient.** Not distributed, not shown to, not represented to anyone but James.
- **Licensed-advice representation.** Unchanged.
- **Rule #11.** Untouched — Model A stays quarantined as a basis; separate axis entirely.

## 6. Enforcement (unchanged machinery, reframed purpose)

- `_require_personal_use()` / `ASXOS_PERSONAL_USE=1` — the single-user gate. Now the mechanical
  guarantee that advice+staging only ever surfaces in James's own context.
- **P6 mechanical guarantee** — no execution/broker tool is mounted; arbi physically cannot
  place an order (`arbi-permission-model.md` §291-293). This is what makes "advise + stage,
  never execute" safe rather than aspirational.

## 7. Honest note on the law (stated once; not a legal opinion)

I cannot give a legal opinion and this is not one. For a genuinely single-user tool advising
only its owner, the regulated concept of providing a "financial service to another person" is
likely not even engaged — there is no client, no second party, no business. The conservative
"no personal advice even for one user" framing in the surfaces was partly a forward hedge
against a possible multi-user Path B future that may never happen. If James ever wants certainty
before relying on this heavily, that is one question for a real adviser/lawyer — not something
this amendment (or arbi) can certify. This note exists so the change is made with eyes open,
not to block it.

## 8. Ratification path

1. arbi-red-team stress-tests this drafted boundary (fidelity to the grant; does "stage orders"
   erode the execution line; any un-amended contradiction; interaction with rule #11 / the
   P-ladder / the `_require_personal_use` gate). **[in progress]**
2. Apply red-team fixes.
3. Land the §4 authority-file edits via the GitHub-API draft-PR route, with this doc as the
   rationale, as a **draft PR**.
4. **James merges = ratifies.** Until then, the current firewall stands and the surfaces keep
   their existing (over-hedged) wording.

Nothing in the broker-report build (the parallel Phase A work) ships in the direct-advice
register until this amendment is ratified — until then those artifacts stay in the current
evidence-and-verdict register.
