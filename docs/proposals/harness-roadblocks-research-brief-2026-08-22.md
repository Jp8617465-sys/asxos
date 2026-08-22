# Research brief — what actually stops production code getting written

**Status:** current · a paste-ready prompt for a fresh session
**Created:** 2026-08-22, from the roadblocks hit during the `/arbi-run` production session (PR #154)
**Owner:** James
**Superseded by:** N/A

The block below is self-contained. Paste it into a new session.

---

```
Research task: find out what is actually preventing this repo from producing production code,
and separate what I can fix from what I cannot.

Context — a production-code session on 2026-08-22 (draft PR #154, branch
claude/production-code-session-tasks-5hqs5n) planned 8 work orders and delivered 4. It produced
5 doc commits to 1 code commit. That ratio was not a scoping choice, and I want to know how much
of it is structural. Read docs/session-handoff-2026-08-22.md, the close row `close-2026-08-22` in
docs/product/arbi-run-ledger.md, and docs/proposals/review-gate-allow-rule-2026-08-22.md first —
they carry the measured evidence rather than the impressions.

Investigate five areas. For each, establish what is TRUE by probing, not by reading docs — this
repo's recurring defect is documents asserting states production has already left, and at least
five such claims were found and corrected in that one session.

1. THE REVIEW GATE AND THE PERMISSION CLASSIFIER
   .claude/hooks/review-gate.sh blocks `git commit` while Python is staged until a marker file
   (.claude/.review-passed-<staged-diff-hash>) exists. The hook prints the exact path. Writing
   that file was denied by the harness permission classifier REPEATEDLY, across both Bash(touch)
   and the Write tool, then succeeded later with no change in circumstances. An explicit
   in-session grant of "all allow and autonomy permissions" did not reach it.
   - Is the denial deterministic or probabilistic? What triggers it?
   - .claude/settings.json carries `Edit(/.claude/settings.json)` in its own permissions.deny,
     so the allow rule cannot be added from inside a session. Is settings.local.json also denied?
     Is there any in-session path, or is this strictly a human-at-a-keyboard edit?
   - Does the marker mechanism have an alternative that is not classifier-gated?
   - Read .claude/hooks/review-gate.sh and tests/test_review_gate_hook.py before proposing
     anything — the hook is deliberately advisory and fail-open, and the marker is forgeable by
     design. Do not propose "hardening" it; the problem is unreliability, not weakness.

2. PYTHON-SPECIFIC FRICTION
   - There is no .venv at session start. The Makefile defaults PY to /usr/local/bin/python3.12,
     which does not exist in this sandbox; the real interpreter is /usr/bin/python3.12, while
     bare `python3` is 3.11 and pyproject requires >=3.12,<3.13.
   - permissions.allow carries Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Bash(make check:*) —
     none of which match `.venv/bin/pytest`, which is what an installed environment actually
     runs. Confirm whether that mismatch causes prompts.
   - CLAUDE.md's "Known test environment gaps (do not chase)" section describes a
     model_a.py -> cache.py -> joblib import chain that PR #144 DELETED. Verify with:
       grep -rn "import joblib\|lightgbm\|sklearn\|shap" asxos/ jobs/ tests/
     Measured 2026-08-22: with .venv + `pip install -e ".[dev]"` and no ML extras, ruff 0.7.0 is
     clean, mypy 1.11.2 strict is clean, and pytest is 2427 passed / 0 collection errors. The
     documented gap does not exist. How many sessions burned time on it?
   - A `session-start-hook` skill exists in this environment. Would a SessionStart hook that
     builds the venv remove this entire class of problem? Cost it.

3. DATABASE ACCESS
   - MCP server IDs ROTATE mid-session. On 2026-08-22 `mcp__supabase-ro__execute_sql` became a
     UUID name and back again, three times. permissions.allow lists it by literal name, so the
     allowlist stops matching; and all five investment-analysis agents declare it in STATIC
     frontmatter, so an agent dispatched across a rotation has no DB tool at all. It does not
     error — it answers from the repo or from memory. Establish whether a stable alias exists,
     or whether agent frontmatter can resolve tools dynamically.
   - The read-only role is inert: current_user is supabase_read_only_user, not asxos_agent_ro
     (which exists but nothing connects through). See
     docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md. What does the Supavisor
     repoint actually require, and is it doable without exposing a credential to a session?
   - Write access was granted verbally but MCP write tools still prompt for approval, which is
     fatal for an unattended run. Confirm whether that is configurable.

4. EDIT-DENIED PATHS THAT BLOCK WHOLE CLASSES OF WORK
   .github/** and migrations/** are both Edit-denied. That removes, outright: scheduling any job
   (detect_theme_stages has been unscheduled since ~2026-08-12), wiring any CI check, and
   authoring any migration. Several planned units were unreachable for this reason alone.
   - Is the deny list load-bearing safety, or precaution that has outlived its cause? Answer per
     path, not as a blanket.
   - claude-execute.yml reportedly may edit workflow files on a claude/** branch. If so, why is
     the direct path denied — and is the indirect path actually usable?
   - authority-guard.sh false-positives on commit MESSAGE text naming an authority path, and on
     reads. It blocked three legitimate operations on 2026-08-22. See
     docs/proposals/permission-and-guard-friction-2026-08-21.md, which already logged this class.

5. THE STRUCTURAL QUESTION — the one I actually care about
   Does the friction asymmetry (doc commits ungated, Python commits gated and unreliable) bias
   this project toward producing artifacts ABOUT code rather than code? Test it against the
   record, don't assume it:
   - Count commits by type across the last ~15 merged PRs. Docs vs code vs tests.
   - Four results_review PRs (#113/#115/#119/#122) merged with ZERO DB access — verify with a
     grep for asyncpg/acquire/SELECT across asxos/domain/results_review/.
   - Amendment E in roadmap-state.md exists BECAUSE units were closing without rendering
     anything. Read why it was written.
   - Counter-hypothesis to test seriously: the live substrate is thin (1 holding lot, 0
     disposals, 1 theme, 0 rows in screening_runs), so several units would legitimately close
     "correct and empty" under Amendment E regardless of any permission. How much of the ratio
     is friction and how much is genuinely nothing to build against?

DELIVERABLE — write it to docs/proposals/, do not just report in chat:
  a) A table of every roadblock, each classified HARNESS (Anthropic/Claude Code, I cannot fix),
     REPO (settings/hooks/docs, I can fix), or ENVIRONMENT (sandbox, fixable by a setup hook) —
     with the evidence for the classification.
  b) A ranked fix list with effort and expected effect. Lead with anything that is one line.
  c) The exact diffs for every REPO-class fix, ready for me to paste. Do not apply them —
     settings and hook files are Edit-denied, which is itself one of the findings.
  d) An honest answer to (5), including how much of the ratio the counter-hypothesis explains.
  e) A measurement I can run each month to see whether the ratio is improving.

CONSTRAINTS
  - Probe before asserting. Every claim cites a file:line, a command output, or a live query.
  - Do not apply any fix, edit any denied path, merge, apply a migration, or write to the DB.
  - Rule #11 stands: do not read the signals table or cite Model A output.
  - If a roadblock turns out not to exist, say so plainly — I would rather lose a finding than
    act on a false one. At least five doc claims were found false in the session that produced
    this brief, so treat this brief's own claims the same way.
```
