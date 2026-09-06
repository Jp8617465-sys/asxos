# Fence integrity — work order (2026-09-06)

Format follows ADR §10.2 D7, the last change of this kind. Its binding constraint
applies here too:

> "Executed in Cursor, not Claude Code — **an agent must not edit its own permission
> surface**." — `docs/product/architecture-decision-record.md:476-486`

So nothing in this directory has been applied. The diffs are authored and verified;
applying them is James's step.

**This is not an unfence.** `.github/**` stays fenced, `AUTHORITY_FRAGMENTS` keeps
every entry it has, and the `settings.json` deny array is unchanged. Every item below
makes the existing fence hold where measurement showed it did not.

## How these were found

By probing the guard, not by reading it. The guard's header (`:22-27`) frames its
residual risk as exotic — "a base64-decoded path, `os.rename`, indirect string
construction". Measurement showed the two most ordinary spellings walked through.

Probes invoke the hook and read its decision. None performs the destructive act to
see whether it is caught: a probe that turns destructive when the guard is missing
is not a test, it is the incident.

| Probe | Before | After |
|---|---|---|
| `rm .github/workflows/full-check.yml` | **ALLOW** | deny |
| `git rm .github/workflows/full-check.yml` | **ALLOW** | deny |
| `rm docs/product/arbi-constitution.md` | **ALLOW** | deny |
| `rm .env` | **ALLOW** | deny |
| `echo x > ./.github/workflows/foo.yml` | **ALLOW** | deny |
| `echo x > ./docs/product/arbi-constitution.md` | **ALLOW** | deny |
| `python -c "open('./.github/workflows/x.yml','w')"` | **ALLOW** | deny |
| authority-guard with `jq` absent | **ALLOW** (fails open) | deny (fails closed) |
| unattended-guard, `.github/` path, `ARBI_UNATTENDED=1` | **ALLOW** | deny |
| `echo x > .github/workflows/foo.yml` | deny | deny |
| `pytest -q`, `rm -rf .pytest_cache`, `cat .github/...` | allow | allow |

## The items

| Item | File | Change |
|---|---|---|
| **W1** | `authority-guard.sh:39` | fail closed when `jq` is absent. It failed open, so the always-on fence silently vanished on a machine without jq. `unattended-guard.sh:49` already failed closed; this is the missing half. |
| **W1b** | `authority-guard.sh` Bash branch | collapse `./` spellings before matching. `$authority_ref`'s left-boundary class excludes `/`, so `.github/` inside `./.github/` was preceded by `/` and never matched. The character class deliberately excludes `.` so `../` is left alone. |
| **W1c** | `authority-guard.sh` `util_verb` | add `rm`, `rmdir`, `unlink`. Deletion appeared in neither the write-verb list nor the redirect check. `mv` was already covered. |
| **W2** | `unattended-guard.sh:58-67` | add `.github/*`. It was absent, so the entire `.github/` fence rested on `authority-guard.sh` alone with no second layer in unattended mode. |
| **W3** | — | **already landed** as `tests/test_authority_fence_drift.py`. It passes against the current hooks, so it needs no patch. |

## Applying

```sh
git apply docs/proposals/fence-integrity-2026-09-06/fence-integrity-all.patch
cp docs/proposals/fence-integrity-2026-09-06/tests-staged/test_fence_integrity.py tests/
make check
```

**The three `authority-guard.sh` diffs are individually clean but not sequentially
composable** — W1b inserts lines above the region W1c anchors on, so applying W1b
first makes W1c fail. Use `fence-integrity-all.patch` for all four, or
`authority-guard-all.diff` + `W2-*.diff`. The individual `W1`/`W1b`/`W1c` diffs exist
so you can take exactly one; verified to apply cleanly to pristine, one at a time.

`fence-integrity-all.patch` was verified to reproduce the tested scratch copy
byte-for-byte (`diff -q` against the tree all probes above were run on).

## Why the test file is staged rather than committed

`tests/` is not fenced, so I could have committed `test_fence_integrity.py` directly.
It would fail on `main` until the hook patch lands — 14 of its 27 cases assert
behaviour the current hooks do not have. Landing a red test to describe a change
that has not happened turns the suite into a to-do list. It travels with the patch.

**Mutation evidence** — the same file against unpatched hooks: **14 failed, 11 passed**.
Against patched hooks: **25 passed**. The 11 that pass either way are the
must-stay-allowed regressions, which is the half of the contract that keeps the
fence from being routed around.

## Scope note

W1 is the item you named. **W1b and W1c came from measurement during this work and
are separable** — they are the same class (fence integrity, no unfence) but they widen
the blast radius of a mistake in a security-critical hook, so they may deserve their
own review pass. Taking W1 + W2 alone and deferring W1b/W1c is a coherent choice; the
diffs are split so that is a one-command decision.

## Observation, not shipped

`authority-guard.sh` has no equivalent of `unattended-guard.sh:55-56`, which denies
when a payload arrives but no `tool_name` can be read from it. The authority guard
falls through to `exit 0` in that case. Same fail-open class as W1, but outside the
item you approved, so it is reported rather than patched.
