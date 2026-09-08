# arbi permission model — blast-radius compatibility map

**Status:** current
**Last verified:** 2026-09-08
**Owner:** James
**Authority:** `AGENTS.md`; this file maps the legacy I/P ladders onto that contract.

`AGENTS.md` is the live cross-harness authority contract. This document is a
compatibility map for older plans, commands and scorecards that still use the
I0–I6 and P0–P6 names. It cannot widen a grant or preserve an older prohibition
that conflicts with `AGENTS.md`.

The old rule “I5/I6 are never standing” is retired. It bundled safe pull-request
landing with secrets, destructive data operations and direct pushes. The current
model classifies the exact effect as Green, Amber or Red and lets the server-side
gate enforce the result.

---

## State gate

| State | Maximum infrastructure authority |
|---|---|
| Missing, malformed or unattested `AUTONOMY` | `ATTENDED` |
| `ATTENDED` | I0–I4 on an agent branch, stopping at a draft PR |
| Attested `STANDING` | I0–I4 plus server-gated pull-request landing described below |

`ARBI_UNATTENDED=1` is a separate execution profile. It remains draft-only even
when repository autonomy is `STANDING`; scheduled landing needs its own explicit
policy and mechanical implementation.

---

## Infrastructure ladder (I0–I6)

| Tier | Capability | `ATTENDED` | Attested `STANDING` |
|---|---|---|---|
| I0 | Read repository and observable state | allowed | allowed |
| I1 | Analyse, prioritise and draft instructions | allowed | allowed |
| I2 | Edit and test on `codex/**`, `claude/**` or `cursor/**` | allowed | allowed |
| I3 | Commit, push the agent branch and open/update a draft PR | allowed | allowed |
| I4 | Dispatch bounded reversible work | allowed within the same ceiling | allowed within the same ceiling |
| I5 | Migration, production-data, egress, spend or secret-adjacent effect | prepare only; no production effect | exact Green/Amber/Red treatment below |
| I6 | Ready, merge or deploy | blocked | server-gated squash merge only; exact Green/Amber/Red treatment below |

### I5 is effect-classified

- Authoring and locally testing a migration is ordinary branch work. A PR that
  adds or changes a migration is Amber because reverting Git cannot undo an
  applied schema change.
- Bounded, non-destructive changes to stored records, auth, egress, communications
  or variable spend are Amber. They require the applicable acceptance-criteria,
  environment and current-head owner gates in `AGENTS.md`.
- Secret values, destructive production SQL, uncontrolled spend and every other
  `AGENTS.md` §8 action are Red. They remain unavailable in every state.

### I6 is integration-classified

- Green PR: while attested `STANDING`, the agent may mark it ready and request a
  squash merge after current-head required checks pass.
- Amber PR: the same path is available only after James has approved the current
  head and the external classifier accepts that exact review.
- Red PR: never merges through agent authority.
- Direct or force push to `main`, `--admin`, auto-merge, merge/rebase merge methods,
  protection bypass and merging a different head are always forbidden.

Merge is deployment because production workflows execute from `main`. A revert is
therefore another classified PR, not a direct main-branch operation.

---

## Portfolio ladder (P0–P6)

| Tier | Capability | Current treatment |
|---|---|---|
| P0 | Read portfolio, market, thesis, tax and benchmark state | read-only |
| P1 | Evidence-only analysis | allowed; cite current evidence |
| P2 | Single-position decision-support memo | impersonal output is Amber with explicit-yes AC; personalised output is Red |
| P3 | Portfolio allocation proposal | same investment-output classification; no order |
| P4 | Persist or schedule a memo | classify the write, output and spend effects independently |
| P5 | Change portfolio mandate or hard constraints | authority self-amendment; draft only for James |
| P6 | Place, modify or cancel an order; move capital | permanently Red and not mounted |

Model A remains quarantined. No Model A signal, scan, allocation or thesis output
may support a real capital decision until a new version passes the pre-registered
positive monotonic conviction-to-21-day-return bar and separately earns
`approved_for_allocation`.

---

## Execution profiles

### Interactive attended session

James may direct I0–I4 work. The stopping point is a draft PR while repository
autonomy is `ATTENDED`. A direct instruction to merge does not override the state
gate or a hard stop.

### Interactive standing session

The agent may use the server-gated Green/Amber merge path only when both of these
facts are current:

1. the repository variable is exactly `AUTONOMY=STANDING`; and
2. the control ledger attests the current `AGENTS.md` digest and authoritative
   verifier commit.

The external `risk-classify` check and protected-branch rules are the enforcement
boundary. A local hook result is feedback, not proof.

### Scheduled or `ARBI_UNATTENDED=1`

The three standing producer lanes may select work, edit an agent branch, verify it
and open a draft PR under their lane-specific controls. They may not ready or merge
a PR, push to `main`, apply a migration, mutate production data, handle secrets or
produce a capital-facing result. This narrower ceiling remains until a later policy
change names and implements scheduled landing.

---

## Mechanical enforcement

| Boundary | Primary enforcement |
|---|---|
| State and policy identity | `AUTONOMY` plus control-ledger attestation |
| Tier and current-head review | App-bound `risk-classify` required check |
| Main history and merge shape | active ruleset: PR-only, squash-only, linear, current checks, no bypass |
| Authority and sensitive-path routing | CODEOWNERS plus classifier registry and drift test |
| Claude feedback | `.claude/settings.json` and fail-closed PreToolUse hooks |
| Scheduled producer ceiling | workflow permissions plus `unattended-guard.sh` |
| Capital and secrets | credentials and tools are not issued to an agent identity |

If any required signal is missing, stale, malformed or bound to another SHA,
identity or policy digest, the result is `ATTENDED` or a failed check—not an
implicit grant.

---

## Promotion and breakers

Green and Amber are assigned mechanically per PR. Amber path classes may move to
Green only through the evidence thresholds and owner decision in `AGENTS.md` §10.
Migrations and Red paths never promote.

Operational and integrity breakers are defined in `AGENTS.md` §9. A trip stops
landing and moves repository autonomy to `ATTENDED`. Only the attested restore path
may return it to `STANDING`; direct variable editing is forbidden.
