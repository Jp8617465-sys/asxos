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
| I5 | Migration definitions, production-data, egress, spend or secret-adjacent effects | prepare only; no production effect | exact Green/Amber/Red treatment below |
| I6 | Ready, merge or deploy | blocked | server-gated squash merge only; exact Green/Amber/Red treatment below |

### I5 is effect-classified

- Authoring and locally testing a migration is ordinary branch work. A PR that
  adds or changes a migration file is Amber. Merging the definition is not
  permission to apply it.
- Production migration application remains owner-only. The ordinary agent,
  verifier and publisher identities may not call the migration tool or assume
  the production migration role. Migration `0042` remains reserved.
- Bounded, non-destructive changes to stored records, auth, egress, communications
  or variable spend are Amber only after the corresponding product invariant and
  acceptance-criteria gates in `AGENTS.md` are satisfied.
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
2. the control ledger attests the current `AGENTS.md` digest, authoritative
   verifier commit, distinct Ledger Writer App identity and exact protected
   ledger parent, after reconstructing an append-only commit chain from the
   owner-approved genesis.

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
Migration-file PRs and Red paths never promote.

Operational and integrity breakers are defined in `AGENTS.md` §9. A trip stops
landing and moves repository autonomy to `ATTENDED`. Only the attested restore path
may return it to `STANDING`; direct variable editing is forbidden.

---

## Legacy citation redirects

Older current documents cite headings from the pre-2026-09-08 version of this
file. These redirects keep those citations meaningful without retaining a second
permission system.

### Promotion preconditions

Promotion means the evidence-based Amber-to-Green process in `AGENTS.md` §10.
Repository activation is separate and requires every item in
`autonomy-policy.md` §Activation checklist.

### Circuit breakers

The authoritative breaker set is `AGENTS.md` §9. The operational controller may
only lower effective autonomy; restoration follows the attested restore path.

### Runtime enforcement honesty

Claude and Cursor hooks are local feedback and can be bypassed by arbitrary code.
The cross-harness boundary is the external exact-head classifier/publisher,
protected ruleset, control-ledger attestation, and the absence of dangerous
credentials from agent identities. Missing or malformed local hook inputs deny.

### The autonomy unlock pack

Skills, builders and mission commands are execution conveniences inside the
active state gate. They do not independently grant ready, merge, migration,
production-write, secret, bypass or capital authority.

### Scheduled/unattended promotion preconditions

`ARBI_UNATTENDED=1` remains draft-only. Scheduled landing requires a later
explicit policy, an independently attested server gate, and separate evidence;
interactive `STANDING` cannot be inherited by a legacy producer workflow.

### Dispatch splits by attendance

Historical attended workflow-dispatch allowlists remain narrow exceptions.
They do not grant merge or production effects, and they do not widen scheduled
producer credentials. Each new caller must be classified and pinned separately.

### Branch-protection status

Re-verified 2026-09-08: `asxos-main` (ruleset 19077432) applies to the default
branch and requires a pull request plus strict `full-check`; ruleset `main`
(18221894) has no included ref and provides no effective coverage. The effective
rule still permits merge, squash and rebase, has no linear-history requirement,
and does not require `risk-classify`. Activation checklist item 2 is therefore
not met.

### Tiers

I0–I6 and P0–P6 describe capability and blast radius. Green, Amber and Red
classify the exact change and effect. Where an old document assigns authority
from a tier number alone, `AGENTS.md` controls and the old claim is stale.
