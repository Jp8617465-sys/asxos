<!--
STAGING COPY — not live. Final placement: .claude/commands/discover-sector.md
(an authority path; placement is James's merge-time / attended step, never a
scheduled-session write). Mirrors .claude/commands/discover-macro.md, adapted
for the two-proposal-type sector-screener output.
-->
# Discover Sector Candidates — `/discover-sector <sector>`

One required argument: the target sector (a `universe.sector` value as printed
by `asx theme coverage`). Invokes the `sector-screener` discovery agent for
that sector, logs its findings into `agent_runs`/`agent_evidence`, and reports
the resulting run IDs so a human can review and approve them.

## Why a slash command and not an agent

Same reason as `/discover-macro` and `/pm-review`: dispatch-parse-persist is
main-loop orchestration; a subagent can't reliably shell out to the CLI as its
own final action.

## Step 1 — Dispatch sector-screener

Invoke the `sector-screener` agent with the sector argument. Wait for its full
response. If the agent reports the sector is already well-covered or empty,
relay that plainly and stop — zero proposals is a valid outcome, not a failure.

## Step 2 — Parse the structured output block

The agent's response ends with one fenced ` ```json ` block shaped like:
```json
{
  "summary": "...",
  "sector": "...",
  "coverage_snapshot": {"symbol_count": 0, "theme_covered": 0, "thesis_covered": 0},
  "theme_proposals": [ {theme_code, name, description, conviction_band,
                        stage, macro_thesis_id, evidence_citation_ids}, ... ],
  "theme_holding_proposals": [ {theme_code, symbol, exposure_strength,
                                direction, mechanism_text,
                                evidence_citation_ids}, ... ],
  "evidence": [ {claim, tier, source_type, source_table, source_as_of,
                 snapshot_data}, ... ]
}
```
If there is no such block, or it doesn't parse, stop and tell the user plainly
— do not invent a proposal or retry silently. If both proposal arrays are
empty, report the coverage snapshot as the run's deliverable and stop.

## Step 3 — Log one agent_runs row per proposal

Order matters for review ergonomics but not for logging — log ALL theme
proposals first, then all theme-holding proposals, so the printed review
sequence matches the required open order (a holding's `theme_code` may
reference a same-run theme, and `asx theme holding open --from-agent-run`
hard-fails if the theme row doesn't exist yet).

For each entry in `theme_proposals`: `asx agent-run log sector-screener
--object-type theme --summary ... --proposal-json ... --evidence-json ...`
For each entry in `theme_holding_proposals`: same with
`--object-type theme_holding`.

Pass the FULL `evidence` array unchanged to every call (the `"local:N"`
citation positions index into that same array — same tradeoff as
`/discover-macro`). Use scratchpad files + command substitution for the JSON
payloads, never inline shell strings. Capture each printed `run_id`.

If any call fails (speculative-citation hard-fail, Pydantic validation),
report that proposal's error and continue with the rest.

## Step 4 — Report results

```
Logged theme proposal #<N>: "<name>" (run_id=<R1>)
Logged theme-holding proposal #<M>: <symbol> → <theme_code> (run_id=<R2>)
Review, then (order matters — themes before their holdings):
  asx theme open --from-agent-run <R1>
  asx theme approve <theme_id> --reason "..."
  asx theme holding open --from-agent-run <R2>
  asx theme holding approve <holding_id> --reason "..."
```
List failures separately from successes.

## Boundaries

This command logs proposals for human review — it never opens or approves
anything itself. A human reads the evidence and runs the open/approve verbs.
The agent it dispatches runs on the read-only Supabase MCP; this command's
own `asx agent-run log` calls are the only DB writes in the flow, they are
append-only audit rows, and they happen in attended sessions only (never from
a scheduled/unattended loop).
