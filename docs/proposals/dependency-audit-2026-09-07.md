# Dependency audit — PRs #214 and #215 (2026-09-07)

**Status:** recommendation for James's merge decision. Not a merge, not an approval.
**Scope:** **#214** `ci: bump anthropics/claude-code-action 1.0.210 → 1.0.216`
(`dependabot/github_actions/actions-6d6a6803d2`) and **#215** `chore: bump the python group with 5
updates` (`dependabot/pip/python-2461c629a7`). Both opened 2026-09-07, both **non-draft**, both
`MERGEABLE`. Baseline `origin/main` @ `fd6172c`.
**Owner:** arbi verified the diffs and wrote this; **James merges.** Sprint
`production-sprint-r1-2026-09-07.md` slice **M1**. **Work-Item:** F-E2E/M1 · **Contract-Revision:** r1.
**Pattern:** `docs/proposals/dependency-audit-178-2026-09-02.md` (merged in #191; backlog A-8), whose
verdict vocabulary and §2 suppression table this follows.
**Every figure measured** at `fd6172c` unless marked *inferred*.

---

## 1. What they actually are

### #214 — four workflow lines, and they are the agentic lanes

One action, six patch releases. Four files, `+1/−1` each — **all under `.github/**`, so this is a
James merge regardless of the audit** (CODEOWNERS; the path is Edit-denied to the agent):

| File | Note |
|---|---|
| `.github/workflows/backlog-roll.yml` | the standing backlog lane |
| `.github/workflows/claude-execute.yml` | the attended execution harness |
| `.github/workflows/nightly-triage.yml` | standing triage lane |
| `.github/workflows/weekly-toolwatch.yml` | standing toolwatch lane |

**The blast radius is arbi's own execution harness, not product code.** Three of the four are the
standing lanes armed by #199, whose backlog row says *"THE MERGE IS THE ARMING ACTION"* — but they
remain `workflow_dispatch`-only with an `acknowledge_write_token_risk` gate and **0 runs**, so this
bump changes nothing until a lane is dispatched. Every release note for 1.0.211 → 1.0.216 is *"Full
Changelog"* only, with no described change [measured — no substantive note to audit against].

### #215 — one file, five lines, one of them on the live send path

`pyproject.toml`, `+5/−5`:

| Package | From → to | Note |
|---|---|---|
| `pydantic` | 2.13.4 → 2.13.5 | patch. Every contract in `decision_engine` and `secondbrain` is a pydantic model — broad surface, but the suite exercises it heavily |
| `typer` | 0.27.1 → 0.27.2 | patch; CLI only |
| `click` | `<8.5` → `<8.6` | **a constraint widen, not a version pin** — see the carry-forward defect below |
| **`resend`** | **2.39.0 → 2.42.0** | **the live daily-brief send path** (`asxos/brief/email.py:61-62`), **mocked in every test** |
| `ruff` | 0.16.4 → 0.16.5 | dev-only lint pin |

## 2. The suppression check — did green CI cost anything?

The question this section exists for: was the green check bought by silencing a rule? Measured on
`origin/main` @ `fd6172c`, then compared with each PR's diff.

| Dimension | Baseline (`fd6172c`) | #214 | #215 | Verdict |
|---|---|---|---|---|
| `# noqa` (`asxos/ jobs/ scripts/ tests/`) | **10** | untouched | untouched | no new suppression |
| `# type: ignore` (`asxos/`) | **59** | untouched | untouched | no new suppression |
| `ruff.toml` ignores | **4** — `E501`, `RUF001`, `RUF002`, `RUF003` | untouched | untouched | strictness intact |
| `mypy.ini` | `strict = True`, `warn_unused_ignores = True`, `disallow_untyped_defs = True` | untouched | untouched | strictness intact |

**Neither PR touches a Python source file, `ruff.toml`, or `mypy.ini`** [measured: #214 is four
workflow YAMLs, #215 is `pyproject.toml` alone]. All four dimensions are therefore *trivially*
unchanged — this section is cheap here, and saying so is more honest than implying a deep check.

*Method note for the next audit: the #178 audit reported the `# type: ignore` baseline as 23, where
the naive `git grep -c` over `asxos/` returns **59**. It used a narrower scoping than the command
above. The exact command is pinned in this table's header so the two are comparable next time.*

## 3. What the green check does not cover

The real work of this audit. CI green is **weak evidence** for exactly one line of #215:

- **`resend` 2.39.0 → 2.42.0 is unexercised by the suite.** `resend` is stubbed into `sys.modules`;
  no test issues a real send. This is the same finding the #178 audit called *"the highest live risk
  in the PR"* for its 2.4.0 → 2.39.0 predecessor — and that predecessor's follow-up has now **paid
  off once**: the first scheduled `daily-brief` after #178 ran **2026-09-06 22:11:55Z, success**
  (run 34063310527; `compose_brief` wrote 7 rows) [measured]. So 2.39.0 is proven on the live path;
  2.42.0 is not. **The only real test is the first scheduled `daily-brief` after this merges.**
- **`pydantic` 2.13.5** is broad but well covered — 4,413 tests exercise the contract layer, and the
  release is four fixes including two GC-traversal fixes in `pydantic-core` *(inferred from the
  release notes, not from a local reproduction)*.
- **`claude-code-action` 1.0.216** is exercised by nothing in CI. The lanes are dispatch-only with
  0 runs, so the first evidence would be a manual dispatch — which is backlog **A-21**, already
  yours.

## 4. One carry-forward defect — not new, and now staler

`#215` widens the `click` cap but leaves its comment verbatim:

```
"click<8.6",  # typer 0.12.5 is incompatible with click 8.2+ (make_metavar signature change)
```

`typer` is being bumped to **0.27.2** in the same five lines. The comment has said `0.12.5` since
before #178, and **this is defect (a) from the #178 audit** (`dependency-audit-178-2026-09-02.md`),
whose follow-up #2 was never executed. #215 makes it staler without touching it.

Offered as a follow-up rather than a change to this PR for the same reason the #178 audit gave:
**Dependabot force-pushes over unexpected commits**, so an edit pushed onto its branch is lost on the
next rebase. Fix it in a separate one-line PR after merge.

## 5. Recommendation

> **#215 — MERGE WITH NAMED FOLLOW-UPS.** Not "as-is", and not a split.
> **#214 — MERGE (yours by path).** No follow-up beyond the standing A-21 dispatch.

Named follow-ups, in order:

1. **Watch the first scheduled `daily-brief` after #215 merges** (cron `30 20 * * 0-4`; the run
   lands ~22:11 UTC). This is the only real test of `resend` 2.42.0. Same follow-up as #178's — and
   #178's is now discharged, which is the argument for keeping it.
2. **Fix the `click` comment** in a one-line PR after merge (`typer 0.12.5` → the current pin).
   Carry-forward from #178; do not push it onto the Dependabot branch.
3. **Split `.github/dependabot.yml`'s pip group.** #178's follow-up #4 proposed `runtime` +
   `dev-tools`; it was never done, and #215 is the evidence — a lint pin (`ruff`) and the live send
   path (`resend`) arrive in one indivisible PR, so you cannot take one without the other. This is a
   `.github/**` edit, so it is yours.

## 6. Standing rulings this audit touches

- **D-6** (*"Rule C10 — Dependabot follow-ups, verdict MERGE WITH FOLLOW-UPS"*) is still open. Its
  four follow-ups from #178 are: watch the send path *(now discharged once)*; fix the `click`
  comment *(open)*; delete the `[ml]` extra *(open)*; split the dependabot group *(open)*. Follow-ups
  2 and 4 above are the same two, re-raised by #215 rather than newly discovered.
  *(Disambiguation: the "C10" in D-6's title is a **ruling** id, not backlog row **C-10**, which is
  the 4-week paper-trade window. Different things.)*
- **D-7** (*"pip-audit ADOPT; mypy-baseline DECLINE"*) is ruled but **unexecuted** — `pip-audit`
  appears nowhere in `pyproject.toml` [measured], only in docs. Neither PR here changes that, but a
  dependency audit is the natural moment to note that the adopted tool still is not running. The
  exact step is in the #178 audit; it is a `.github/**` edit, so it is yours.

## 7. Live exposure note (not a finding against either PR)

Both PRs are **non-draft**, and `pr-review-agent.yml` runs on `pull_request` **at PR head** with
`OPENAI_API_KEY` and `issues: write`, skipping only while a PR is draft. So every Dependabot
force-push runs that workflow at a head neither of us authored. The steps that run are the reviewed
ones from `main`, so this is controlled use rather than a defect — it is flagged because it is the
reason M1 was scheduled ahead of the other maintenance work, and because the same property is one of
the two exposures the #211 inventory named.

## 8. Boundary

This document merges nothing, edits no dependency, and touches no workflow. Both merges are James's:
#214 by path (`.github/**`), #215 by the standing no-auto-merge rule.
