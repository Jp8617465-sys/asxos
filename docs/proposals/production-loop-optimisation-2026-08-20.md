# Production-loop optimisation — the six-point ruling of 2026-08-20

**Status:** ruled by James 2026-08-20 (verbatim: "okay lets do all of these 6", accepting the
six-point critique presented in-session); this document is the execution record and the
drafts for the parts only James can apply
**Scope:** the operating loop itself (wake → plan → vet → build → review → merge), not any
product feature
**Origin:** an in-session assessment (2026-08-20, session on `claude/asx-stock-evaluation-p0hxx2`)
that the loop is optimised for safety/auditability/reversibility but not for production
throughput, scale, longevity, or repeatability — with each weakness evidenced from the repo's
own history (the four-week-stale state header, three stale-claim errors in one session, nine
open draft PRs queued behind one merger — six of them from the 2026-08-17..19 burst alone,
19-of-22 uncited merged PRs, R17, flat-rate review ceremony)
**Owner:** main loop executed items 2 and the recordable parts of 4 this session; items 1, 3,
5, 6 carry James-gated steps drafted below
**Superseded by:** N/A

The six items, their status after this session, and what remains:

| # | Item | Status after this session | Remaining owner |
|---|---|---|---|
| 1 | Second GitHub identity | **Runbook written** — `docs/product/runbooks/second-github-identity.md` | James (interactive browser steps only he can do) |
| 2 | Structured operational state | **BUILT this session** — see §2 | Next wake refreshes the snapshot; SB1-02 automates production |
| 3 | Wire closure scripts into CI | **YAML drafted** — §3 (this session cannot edit `.github/**`) | James applies the workflow edit |
| 4 | Ratify Amendment E | **Ratification recorded** — `roadmap-state.md` Amendment E block + `check_ledger_coverage.sh` effective-date constant; retroactivity question stays open | James: the retroactivity ruling (deliberately left blank in the draft) |
| 5 | One runtime / fence Cursor | **Policy recommendation** — §5 | James (usage behaviour + app access are his) |
| 6 | Risk-tiered review loop | **Tier policy + CLAUDE.md diff drafted** — §6 | James applies the CLAUDE.md edit (authority path) |

---

## §2 — Structured operational state (BUILT)

**What shipped this session** (all on `claude/asx-stock-evaluation-p0hxx2`):

- `docs/product/state/latest-snapshot.json` — the first real `ProjectStateSnapshot` artifact,
  populated from this wake's live probes (git, GitHub MCP, Supabase SELECT-only): every leaf
  `observed` with a real value, and six backing `probes[]` records carrying source +
  timestamp (per-leaf probe *linkage* is deferred to SB1-02 by the schema's own
  `sb1_02_deferred_probe_linkage` note, so not every leaf names its probe yet). One file,
  overwritten per wake, versioned by git — history is `git log`, not a growing prose block.
- `scripts/check_project_state.py` — the validator seam: frozen-schema validation
  (SB1-01, `asxos/secondbrain/project_state.py`, v1, `extra="forbid"`) plus a wake-time
  freshness check (`--max-age-days`, default 7). Exit conventions 0/1/2 match the two
  existing closure scripts. It never writes or repairs a snapshot (L18 clause 2).
- `tests/test_check_project_state.py` — 8 tests, including the load-bearing one:
  **the checked-in artifact must always validate**, which runs in the existing `full-check`
  pytest lane — so item 2 is CI-enforced *today*, before any workflow edit, via the test
  suite that already gates every PR.

**Deliberately built on, not beside, SB1-01.** The schema was frozen 2026-08-17 (PR #118);
inventing a second state format would have been the exact parallel-thread defect this ruling
exists to reduce. Full probe *automation* (adapters that produce the snapshot mechanically)
remains SB1-02's mission — pre-authorized by the 2026-08-17 rider, still needing its own
red-team vet. What shipped here is the consumer seam SB1-02 plugs into, plus the first
hand-probed-but-real artifact so the seam is never empty.

**The wake contract change this implies** (for `/arbi` step 1 and `/arbi-close` step 2,
prompt-level until SB1-02 automates it): a wake refreshes `latest-snapshot.json` from its
probes and runs `PYTHONPATH=. python scripts/check_project_state.py` (no flag — freshness
checked); the prose Last-wake-snapshot block in `roadmap-state.md` becomes a pointer to the
artifact rather than a hand-maintained duplicate. Two sources of the same truth is how the
four-week header rot happened.

## §3 — CI wiring for the closure checks (DRAFT — James applies; `.github/**` is deny-listed for agent sessions)

Current measured state, so the wiring lands green rather than instantly red:

- `check_ledger_coverage.sh` — **cannot run in this sandbox** (no `gh` CLI; exit 2). Must be
  verified once by James locally before wiring. Its Amendment E check is now live per §4.
- `check_doc_expiry.sh` — **currently FAILS: 23 expired dated docs** (measured this session,
  2026-08-20). Wiring it blocking today reddens every PR; wiring it `continue-on-error`
  trains everyone to ignore it. The right order is: disposition the 23 (archive/allowlist/
  rewrite, per the script's own remedy text) in one sweep PR, *then* wire blocking.
- `check_project_state.py --schema-only` — **passes today** (artifact validates), and is
  already enforced via the pytest lane regardless of this wiring.

Drafted addition to `.github/workflows/full-check.yml` (a separate job so its failures are
legible as loop-hygiene, not test failures):

```yaml
  loop-closure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Project-state snapshot validates against the frozen schema
        run: |
          pip install pydantic pydantic-settings
          PYTHONPATH=. python scripts/check_project_state.py --schema-only
      - name: Doc expiry
        # BLOCKING only after the 23-offender sweep lands; do not wire with
        # continue-on-error — an ignorable check is worse than none.
        run: scripts/check_doc_expiry.sh
      - name: Ledger coverage + Amendment E completion test
        # Needs gh auth; PR-time runs see merged-PR history, so this fails on
        # pre-existing uncited merges until the ledger is current (it is, as of
        # the 2026-08-17 remediation — verify once locally before wiring).
        env:
          GH_TOKEN: ${{ github.token }}
        run: scripts/check_ledger_coverage.sh
```

Sequencing: state-check step is safe immediately; doc-expiry after the sweep; ledger-coverage
after one green local run. Three steps, each turned on when it can hold.

## §5 — Runtime policy: fence or pause the out-of-fence lanes (RECOMMENDATION)

R17 (recorded in unmerged PR #143; deliberately not duplicated into `risk-register.md` here to
avoid a second uncoordinated edit to the same row) established that Cursor Cloud Agent
sessions run with `settings.json` permission arrays and `authority-guard.sh` **inert**, and
that one such session's `arbi-red-team` dispatch **fabricated a citation**. Four of the nine
open drafts (four of the six from the 2026-08-17..19 burst) came from that lane,
uncoordinated with two concurrent Claude-lane threads.

**Recommendation** (enactment is James's — it is his usage behaviour and his app grants):

1. **Pause Cursor-lane repo work** until either (a) that runtime can enforce the same hook
   set, or (b) its scope is confined to read-only analysis whose outputs land as draft PRs
   vetted by an *in-fence* red-team run. Not because the work was bad — #141/#142 are good
   work — but because two fences with one gate between them is one fence.
2. **Standing rule regardless:** no red-team verdict from an out-of-fence runtime counts as a
   vet (already arbi's position this wake; worth promoting to a lesson if it holds).
3. When the second-identity runbook (item 1) executes, revisit: an enforced-review world
   tolerates out-of-fence *authors* much better, since nothing merges unreviewed.

## §6 — Risk-tiered review (POLICY + DRAFTED CLAUDE.md DIFF)

The mechanical gate (`review-gate.sh`) already tiers: it fires only when `.py` is staged.
The *flat-rate ceremony* lives in CLAUDE.md's prose ("After any non-trivial code change ...
run the review loop"), which sessions apply to doc-only work too. Formalising the tiers
changes prompt-level convention only — no hook edit needed:

- **Tier A — full three-agent loop** (`security-engineer` where the trigger conditions hold,
  `refactoring-expert`, `technical-writer`): anything under `asxos/**`, `jobs/**`,
  `scripts/*.py`, behaviour-bearing tests. Unchanged from today.
- **Tier B — single-pass or none**: `docs/**` and non-authority config. A `technical-writer`
  pass when the doc is load-bearing (governance set, runbooks, specs); nothing for session
  records (handoffs, ledgers, decision-log rows — these are *records of* review, and
  reviewing the record of a review is where the flat rate burns tokens).
- **Tier C — James-only**: the existing deny-listed authority paths. Unchanged; already
  mechanical.

Drafted CLAUDE.md edit (James applies — the file is deny-listed): in the "Subagents —
delegation policy" section, replace the sentence "**After any non-trivial code change, before
committing, run the review loop:**" with "**After any non-trivial change to code
(`asxos/**`, `jobs/**`, `scripts/*.py`, behaviour-bearing tests), run the full review loop
before committing. Doc-only commits take at most a single `technical-writer` pass (load-bearing
docs) or none (session records — handoffs, ledger and decision-log rows). Authority paths are
James-only regardless.**" — leaving the numbered three-agent list beneath it unchanged.

## What this ruling does NOT change

Every hard stop survives verbatim: merge/ready/un-draft remain James-only; no migration is
applied by any of this (none is needed — item 2 is file-and-script only); `0042` never; rule
#11 untouched (nothing here reads `signals`/`model_versions`); the s766B firewall untouched;
no authority file edited by an agent (the two that need edits — `full-check.yml`, `CLAUDE.md`
— are drafted above for James, per the deny-list's own draft-for-James flow).
