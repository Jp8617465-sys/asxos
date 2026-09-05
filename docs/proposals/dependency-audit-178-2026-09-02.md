# Dependency audit — PR #178 and the two proposed CI dev-deps

**Status:** recommendation for James's merge decision
**Scope:** Dependabot PR #178 (`dependabot/pip/python-8353cf76d5`, head `3417645`), and the two
Phase 2 CI dev-dependencies proposed 2026-08-25 and never ruled on
**Owner:** `tech-stack-researcher` consulted per CLAUDE.md's delegation table; arbi verified the
diff and wrote this; **James merges**
**Campaign node:** H1-E (Amendment H, Wave 1)

---

## 1. PR #178 — what it actually is

The title says "27 updates" and reads like a dev-tooling bump. It is not. `.github/dependabot.yml`
groups the whole pip ecosystem on `*` — deliberately, to keep PR volume survivable for a solo
reviewer — so **runtime dependencies are in this PR too**. The notable moves:

| Package | From → to | Note |
|---|---|---|
| `pandas` | 2.2.3 → **3.0.5** | **A major version, unflagged in the title** |
| `resend` | 2.4.0 → **2.39.0** | On the live daily-brief send path |
| `fastapi` | 0.115.0 → 0.141.1 | |
| `asyncpg` | 0.29.0 → 0.31.0 | Every job's DB driver |
| `pydantic` / `pydantic-settings` | 2.9.2 → 2.13.4 / 2.5.2 → 2.15.0 | |
| `typer` / `click` cap | 0.12.5 → 0.27.1 / `<8.2` → `<8.5` | see defect (a) |
| `ruff` / `mypy` / `pytest-asyncio` | 0.7.0 → 0.16 / 1.11.2 → 2.x / 0.24.0 → 1.4.0 | the three named majors |
| `lightgbm` / `shap` / `scikit-learn` / `joblib` | all bumped | **nothing imports these** |

## 2. The fallout commit is a real fix, not suppression

The branch's third commit ("fix ruff 0.16 / mypy 2 / pytest-asyncio 1.4 fallout") is the thing
worth checking, because green CI on a branch that silenced the new rules is not the same as a
clean upgrade. Verified against `origin/main`:

| Check | Baseline | Branch | Verdict |
|---|---|---|---|
| `# noqa` occurrences | 12 | **12** | no new suppression |
| `# type: ignore` in `asxos/` | 23 | **22** | net *decrease* — a real fix |
| `ruff.toml` | 4 ignores | **untouched** | no rule silenced |
| `mypy.ini` | `strict = True`, `warn_unused_ignores = True` | **untouched** | strictness intact |
| `pyproject.toml` asyncio settings | `asyncio_mode`, `..._loop_scope` | **untouched** | as expected — the repo pre-paid the 1.0 migration |

The code changes are genuine modernisations: a redundant `cast()` dropped in
`decision_engine/types.py`, a now-unneeded `type: ignore[index]` removed in `portfolio/profile.py`,
`{k: 0.0 for k in present}` → `dict.fromkeys(present, 0.0)`, `__all__` re-sorted, an unused
`TypeVar` deleted. That is what a correct fallout fix looks like.

**Conclusion: the tool-major half of this PR is in good shape.** The risk that remains is not in
the linters.

## 3. What the green check does not cover

`tests/conftest.py` states it plainly: every test that touches the DB mocks `asyncpg`/`acquire`
directly, and the one real-database test is skipped without `MIGRATION_TEST_DATABASE_URL`. So
2735 passing tests are strong evidence about `ruff`/`mypy`/`pytest-asyncio` and **weak evidence
about `asyncpg`, `pydantic`, `httpx` and `resend`** — whose failures appear at 20:30 UTC in a
scheduled job, not in CI.

Concretely:

- **`resend` 2.4.0 → 2.39.0** is the highest live risk in the PR. `asxos/brief/email.py:61-62`
  calls `resend.api_key = …` then `resend.Emails.send(…)`; that surface is mocked in tests. A
  breaking change there stops the daily brief silently — the exact class of failure the north
  star's "discipline events reach him before they cost money" criterion exists to prevent.
- **`pandas` 2.2.3 → 3.0.5** touches only `domain/research/alpha_loader.py` and `alpha_eval.py`
  (used by `factor_scores.py` / `jobs/compute_factor_scores.py`). `alpha_loader` is at 100% test
  coverage since #174, and the panel it loads is the **frozen** `signals` table, so the blast
  radius is one module cluster on quarantined data. Lower risk than its major-version number
  suggests, but it is a major and the PR title does not say so.
- **The `[ml]` extras were bumped and nothing imports them.** No live module imports `lightgbm`,
  `shap`, `scikit-learn` or `joblib` — the only repo-wide match is a docs code block — yet both CI
  lanes install `.[ml,dev]` on every run, paying an llvmlite/shap compile to protect code deleted
  in #144. Bumping them is accepting risk for zero benefit.

## 4. One real defect in the diff

**(a) The `click` cap comment is now false.** The pin moved `click<8.2` → `click<8.5`, but the
inline rationale still reads *"typer 0.12.5 is incompatible with click 8.2+ (make_metavar
signature change)"* — while `typer` itself moved to 0.27.1 in the same diff. The cap may well be
right; the sentence explaining it is about a version no longer in the file. Left uncorrected it
becomes the next person's false premise. One-line fix, offered as a follow-up rather than pushed
onto a Dependabot branch (Dependabot force-pushes over unexpected commits).

## 5. Recommendation

**MERGE WITH NAMED FOLLOW-UPS** — not "as-is", and not a split.

The tech-stack-researcher consult recommended splitting into four PRs. That was the right call on
the evidence available to it — it could not read the diff. With the diff verified clean, splitting
now costs more than it buys: it means rebasing a 30-pin resolution set by hand, and Dependabot
will simply re-open the remainder. Merge it, and take these four follow-ups:

1. **Watch the first scheduled `daily-brief` run after merge** (22:43 UTC) and confirm the email
   actually sent — that is the `resend` bump's only real test. If it fails, the revert is one pin.
2. **Fix the stale `click` comment** (defect (a)).
3. **Delete the `[ml]` extra** — `pyproject.toml` plus `[ml,dev]` → `[dev]` in both CI lanes.
   Removes the bump risk *and* an llvmlite build from every CI run. Needs James (`.github/**`).
4. **Split `dependabot.yml`'s single `*` group** into `runtime` and `dev-tools` so a major runtime
   bump is never again invisible behind a tooling headline. Two grouped PRs a week is the
   compromise against the anti-volume rationale, not fifteen. Needs James.

**Operational note:** `scripts/hooks/pre-push` resolves `.venv/bin/ruff` and `.venv/bin/mypy`. After
merge, any dev environment whose `.venv` is not reinstalled runs the *old* linters and reports
green against the new pins.

---

## 6. The two proposed dev-dependencies

**`mypy-baseline` — DECLINE for now.** The tool is well-shaped for this repo (a ratchet that fails
on *new* errors, not a warning stream, so it does not violate the standing "no warnings nobody
acts on" lesson). Two reasons to wait. First, necessity is unmeasured: the same widening is
available with no new dependency by moving `mypy asxos` → `mypy asxos jobs` → `+ scripts` one
directory per PR, and nobody has run `mypy asxos jobs scripts` to see whether the error count is
even large enough to need a baseline file. Second, sequencing: `mypy-baseline` parses mypy's error
output, and this repo is about to move to mypy 2.x, whose output format and new parallel-checking
mode are the least-settled thing in the whole bump. Adopting an output-parsing tool in the same
window is the wrong order. Revisit after #178 settles, with a measured error count.

**`pip-audit` — ADOPT.** It is a hard-fail scanner, not a warning generator: non-zero exit on any
advisory affecting an installed package, which matches CLAUDE.md rule #10's idiom. It closes a
real gap — Dependabot as configured gives *version currency* on a weekly cron; it says nothing
about a CVE landing on a pin already in the tree. With 30 exact pins the alert volume is
inherently low and every alert is actionable.

The step for James to add to `full-check.yml`, after the ruff and mypy steps so a security
advisory cannot mask a lint or type regression:

```yaml
      - name: Audit dependencies (pip-audit)
        run: pip-audit --skip-editable
```

`--skip-editable` is required, not cosmetic: `pip install -e .` makes `asxos` itself an editable
install with no PyPI presence, which pip-audit would otherwise flag. Add the pin to the `dev`
extra like everything else. Do not add it to `targeted-ml-tests.yml` — that lane is already
documented as redundant.

**The failure mode to accept deliberately:** pip-audit blocks the build when an advisory exists
with *no fixed version available*, so an unrelated PR cannot merge until you act. The escape hatch
is one `--ignore-vuln GHSA-…` flag with a dated comment — the same reviewed-exception pattern the
`click` cap and the `pyyaml` pin already use. That keeps it a decision, not a silenced warning.
