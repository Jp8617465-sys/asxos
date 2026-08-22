# Decision package — 2026-08-22

> ## ✅ G1 — CLEARED by James, 2026-08-22
>
> **James approved both `P3-01` and `P3-02`** in the `/arbi-mission` session on
> `claude/product-roadmap-backlog-8k3jz5`, choosing "clear gate G1" over three alternatives
> (proceed with `SB4-01` as amended, fix the `/pm-review` hazard first, or stand down).
>
> **What it unblocks:** `P3-03` → `P4-01` → `P4-02` → `P5-02` → `P6-01` → `P7-01` → `P7-02` →
> `P8-01` — 8 of the 17 remaining rows. `P3-03`'s dependency is literally "P3-01..02 approvals",
> and this is the first moment both artifacts existed *and* were approved.
>
> **What it does NOT authorise.** Approving the two work orders is not approval to execute what
> they describe. `P3-02` §2 is explicit that bucket creation with Object Lock is effectively
> one-shot, and the packet routes credential creation, bucket creation and scheduler cutover to
> James regardless. So `P3-03` proceeds on the read-only half (replay + lineage) and the
> backup/restore leg stays blocked until James creates the S3 credentials.
>
> **The two honest holes below remain holes.** Approval did not resolve them and they are not
> treated as resolved: `P3-02` still carries **no cost model** (AWS pricing was `unavailable` —
> egress blocked), and its Object Lock claim is still from documented behaviour rather than a
> probe. `P3-01`'s sizing still rests on a 90-minute weekly chain that PR #128 cut to 4m35s, so
> its cost case must be re-derived before anything is deployed.
>
> The G1 section below is preserved unedited as the record of what was decided against.

**Status:** superseded in part — **G1 cleared 2026-08-22**; G2 and the seven carried items remain open
**Scope:** every decision blocking the documented build, in one place, with what each unblocks
**Prepared:** 2026-08-22, from the `/arbi-run` session on `claude/product-roadmap-backlog-8k3jz5`
(10 commits ahead of `origin/main` @ `31c78f4`)
**Owner:** James. Nothing here is arbi's to decide.

---

## Why this exists

The build has a queue of 17 remaining work orders. **Eight of them sit behind one gate, and the
gate is now assemblable for the first time** — both artifacts it requires exist. Two more
decisions carry a clock. The rest are small and have been carried across several sessions.

Two independent governance rules now say the same thing about what is left unblocked: the
packet's §9 kill condition ("pause on more orchestration work than product evidence work") and
recipe R1's composition rule ("at least 70% product/code/live-ops"). **The only unblocked work is
second-brain/autonomy work**, which fails both. That is not a scheduling nuisance — it means the
build cannot resume its actual purpose until G1 clears.

---

## G1 — approve the two Stage 1 work orders

**Unblocks 8 of 17 remaining rows:** `P3-03` → `P4-01` → `P4-02` → `P5-02` → `P6-01` →
`P7-01` → `P7-02` → `P8-01`.

`P3-03`'s dependency is stated as "P3-01..02 **approvals**". Both now exist:

| | Work order | State |
|---|---|---|
| `P3-01` | Dagster deployment / cost / cutover | merged #117, `docs/proposals/dagster-deployment-cost-cutover-work-order-2026-08-17.md` |
| `P3-02` | S3 credentials / Object Lock / lifecycle / restore | written this session, `docs/proposals/s3-object-store-work-order-2026-08-22.md` |

**Read `P3-02` §2 before deciding.** Enabling Object Lock on an existing bucket is not a
self-service operation, so bucket creation is effectively one-shot. Its §3 recommends a two-prefix
split (`raw/` with per-object retention, `backup/` daily dumps without) because Object Lock plus a
daily full dump produces unprunable storage — lifecycle cannot delete a locked object.

**Two honest holes in `P3-02`, both flagged in the document:** AWS pricing is `unavailable`
(egress blocked from this environment), so §4 states there is **no cost model** — do not approve a
cost position on it. And the Object Lock constraint is from documented behaviour, not a probe;
it is the claim most deserving independent confirmation.

`P3-01` carries its own flag: its sizing rests on a 90-minute weekly chain that no longer exists
(PR #128 cut `sync_corporate_actions` from 88m06s to 4m35s), so its cost case must be re-derived.

**Decision:** approve both, approve one, or send back. Approving unblocks the product lane.

---

## G2 — the capital/risk calibration (`P5-01`)

**Unblocks Stage 4 → 5 → 6.** Ruling F4 names it explicitly: *"James must complete the
capital/risk calibration before Stage 4."*

**This one has a hidden clock.** `P7-01` observes outcomes at **21 / 63 / 126 trading days**, and
the programme's definition of done (§9) needs one complete learning episode. 126 trading days is
roughly six calendar months *after* the first governed paper case exists — and that case
(`P5-02`) is downstream of both G1 and G2. Every week G2 waits is a week added to the end of the
programme, not to the middle.

---

## Time-boxed — 6 days

**Dark-launch surfaces #1 (portfolio brief) and #4 (paper-trade evaluator) expire 2026-08-31 —
9 days out — with a "decide by 2026-08-28" flag, 6 days out.**

`dark-launch-exit-plan.md` names James as flip owner for both (capital-adjacent). Note the
interaction: #4's gate is "start the 4-week paper-trade run", which **cannot produce evidence
before #1's own expiry**. If the window is not opened this week, both re-raise on 08-31 with no
new evidence to decide on — the same undecided state the document's own rule forbids.

---

## Carried items

| # | Item | Why James | Note |
|---|---|---|---|
| 1 | Apply migration `0045_segment_map` | Migration approval | Unapplied; `segment_map` absent; `build_segment_map` inert. **Not** time-boxed |
| 2 | Schedule `detect_theme_stages` | `.github/` is Edit-denied to the agent | Theme stages un-refreshed since ~2026-08-12 |
| 3 | Amputate `thesis-coherence-guard`'s dead SHAP steps | `.claude/agents/` Edit-denied; capital-adjacent | **`/pm-review` is unsafe until then** — it returns frozen Model A evidence as current, into a synthesis about real holdings, and its frontmatter says "use PROACTIVELY" |
| 4 | Enumerate the **product lane's** standing rows | Amendment D is James's ruling | The lane ranks above the packet lane but has **no rows anywhere in the repo** — exhausted in fact, undefined in form |
| 5 | Wire `authority-guard.sh` into the MCP surface | Authority change | PR #148 wired `mcp__*` into `pr-draft-guard` + `unattended-guard` but not this one. The GitHub API route reaches every authority file — it is how `CLAUDE.md` was edited this session, disclosed at the time |
| 6 | Wire `scripts/check_project_state.py --schema-only` into `full-check.yml` | `.github/` Edit-denied | Its own docstring says "CI must run with" it; no workflow does. Now more valuable — it gained contradiction detection this session |
| 7 | Apply the permission/guard friction patches | `.claude/settings.json` + hooks are authority paths | Already drafted at `docs/proposals/permission-and-guard-friction-2026-08-21.md` with measured evidence: 32 permission-request rows, 3 hook false-positives in one session |

---

## On the standing permission grant

James granted "full allow list and permissions to override any requests" this session. Recorded
plainly: **a verbal grant changes nothing mechanically.** The harness reads `.claude/settings.json`,
not conversation, and `authority-guard.sh` is `ALWAYS-ON`, not gated on any permission mode. This
was demonstrated live — a read-only `grep` was blocked seconds after the grant.

Carried item 7 is the action that converts the intent into capability. Yesterday's session reached
the identical conclusion independently (`permission-and-guard-friction-2026-08-21.md:11-31`).

Four boundaries are treated as **not** covered by any general grant, and would each need naming
separately: **rule #11** (its removal condition is specified and pre-emptively forbids removal on
v1_5's basis), the **s766B firewall** (a legal boundary), **capital execution**, and **migration
`0042`**. Self-granting authority is outside arbi's reach by constitution regardless.

---

## What arbi does while these are open

Per recipe R1's composition rule and the §9 kill condition, arbi does **not** launch a chaining
window over the remaining unblocked queue — it is all second-brain work and would be ~0%
product/code/live-ops against a 70% floor.

It takes `#6` (the `leaves()` consolidation — a genuine prerequisite for `SB3-01`, and small), and
stops. Recipe **R2** (`arbi-goal-recipes.md`) is the vetted loop to launch once G1 clears and the
product lane has rows to run.
