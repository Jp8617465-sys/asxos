# `.github/workflows/issue-snapshot.yml` — patch for James, 2026-09-06

**Status:** drafted; **NOT applied.** `.github/**` is deny-listed to the agent (`.claude/settings.json`
`permissions.deny`, `authority-guard.sh` `AUTHORITY_FRAGMENTS`) and James ruled on 2026-09-06 that the
fix is delivered as a patch, not via an API commit. Backlog row **A-24**. Inbox row in `james-inbox.md`.

## The red — measured

- Scheduled run **34030294978**, 2026-09-06 11:27 UTC, job `snapshot`, step **Commit if changed**:

  ```
  [main 529f4f7] chore(ops): refresh GitHub issues snapshot
   1 file changed, 50 insertions(+), 1 deletion(-)
  remote: error: GH013: Repository rule violations found for refs/heads/main.
  remote: - Changes must be made through a pull request.
  remote: - Required status check "full-check" is expected.
   ! [remote rejected] main -> main (push declined due to repository rule violations)
  ```

- Green 09-01 → 09-05 (runs 33506655943 … 33962307935). The export itself still works — the
  payload changed (issues #204/#205 were opened 09-06 01:52 UTC) and that is exactly the push that
  the ruleset now refuses.
- Cause: the workflow's last step is `git commit … && git push` to `main` under the default
  `GITHUB_TOKEN` with `contents: write` (`issue-snapshot.yml:37-38, 55-62`). The ruleset that
  issue #205 inventoried on 09-06 ("PR use, strict current `full-check`, no bypass actors") applies
  to `refs/heads/main`, so a bot push to `main` can never succeed again. This is a fresh instance
  of the failure class `roadmap-state.md` names at `:1254` — a scheduled loop failing where nobody
  is watching — and it will re-fail daily at 07:00 UTC until changed.

## Options (the decision is James's)

| # | Change | Keeps "git history is the archive" (`export_github_issues.sh:6-7`)? | Cost |
|---|---|---|---|
| **B — recommended** | Commit the snapshot to a dedicated unprotected branch `ops/issue-snapshot` instead of `main` | **yes** — same repo, same durability; `main` keeps a placeholder | one-line precondition: confirm the ruleset targets `main` only (Settings → Rules → the active ruleset's *Target branches*) |
| A | Open/update a bot PR per change | yes, once merged | a daily PR needing `full-check` + a James merge — converts one red into one click per day |
| C | Upload the JSON as a workflow artifact, drop the commit step | **no** — 90-day artifact retention, not git | none, but defeats the script's stated purpose |
| D | Add `github-actions[bot]` as a ruleset bypass actor | yes | reintroduces a bot with `main` write — the property #205 verified absent and the ACP plan is built to keep absent. Reject. |

**B** is the only option that keeps the archive property without a click or a bypass. Note the ACP
plan (`docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md` §3 Phase 3)
retires Markdown/YAML dual-write after the GitHub cutover, so this whole workflow is transitional;
B is the smallest change that keeps it honest until then.

## Patch — option B

```diff
--- a/.github/workflows/issue-snapshot.yml
+++ b/.github/workflows/issue-snapshot.yml
@@
-# Commits docs/ops/github-issues-snapshot.json on main when the payload
-# changed. full-check.yml paths-ignore that file so a snapshot-only push does
-# not run the full pytest suite. GitHub cron only fires from the default
-# branch. workflow_dispatch works from any ref after merge.
+# Commits docs/ops/github-issues-snapshot.json to the unprotected branch
+# ops/issue-snapshot when the payload changed. It used to commit to main;
+# the main ruleset (PR-required, full-check required, no bypass actors —
+# verified 2026-09-06, issue #205) rejects any direct push, so run
+# 34030294978 failed on 2026-09-06 and would fail daily. The export still
+# runs from main's code; only the archive branch differs. full-check.yml
+# paths-ignore the file so a snapshot-only push never runs pytest. GitHub
+# cron only fires from the default branch. workflow_dispatch works from any
+# ref after merge.
@@
       - name: Commit if changed
         run: |
           set -euo pipefail
           git config user.name "github-actions[bot]"
           git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
+          # Archive branch: fast-forward onto its current tip if it exists, else start it from main.
+          if git fetch origin ops/issue-snapshot 2>/dev/null; then
+            git checkout -B ops/issue-snapshot FETCH_HEAD
+          else
+            git checkout -B ops/issue-snapshot
+          fi
+          git checkout main -- docs/ops/github-issues-snapshot.json 2>/dev/null || true
+          bash scripts/export_github_issues.sh
           git add docs/ops/github-issues-snapshot.json
           if git diff --staged --quiet; then
             echo "issue snapshot unchanged"
             exit 0
           fi
           git commit -m "chore(ops): refresh GitHub issues snapshot"
-          git push
+          git push origin HEAD:refs/heads/ops/issue-snapshot
```

(The `Export issues` step above it can stay — re-running the export on the archive branch is what
makes the diff meaningful against the *previous snapshot* rather than against `main`'s placeholder.
If you prefer one export, delete the earlier step and keep this one; `GH_TOKEN` must then move
into this step's `env:`.)

## Test pins to update in the same PR (arbi-editable path, but they must land together)

`tests/test_issue_snapshot.py:72-78` pins `"git push" in _WORKFLOW_TEXT` — still true. Add one
assertion so the archive branch is load-bearing, not incidental:

```python
def test_workflow_archives_to_the_ops_branch_not_main() -> None:
    assert "git push origin HEAD:refs/heads/ops/issue-snapshot" in _WORKFLOW_TEXT
    assert "git push\n" not in _WORKFLOW_TEXT  # a bare push would target main and hit GH013
```

## Steps

1. Confirm the ruleset's target is `main` only (if `ops/**` is also protected, choose A or C).
2. Apply the diff on a `claude/**` or `james/**` branch; add the test above; `make check`.
3. Open the PR, let `full-check` go green, merge.
4. `gh workflow run issue-snapshot.yml` — expect a green run whose last step pushes to
   `ops/issue-snapshot`; then `git ls-remote origin ops/issue-snapshot` shows the tip.
5. Close backlog row A-24 and the inbox row.

**Verify the red is gone:** `gh run list --workflow=issue-snapshot.yml --limit 2` → both `success`.
