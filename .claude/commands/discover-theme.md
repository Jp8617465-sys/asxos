# Discover Themes (macro-conditioned) — `/discover-theme [macro_thesis_id]`

One **optional** argument: a `governed_active_macro_theses` id. Invokes the
`theme-researcher` discovery agent (top-down: operationalise an approved macro thesis's
regime into ASX-investable themes), logs its findings into `agent_runs`/`agent_evidence`,
and reports the resulting run IDs so a human can review and approve them.

## Why a slash command and not an agent

Same reason as `/discover-sector`, `/discover-macro`, `/pm-review`: dispatch-parse-persist
is main-loop orchestration; a subagent can't reliably shell out to the CLI as its own final
action. This is the *top-down* sibling of `/discover-sector` (which is bottom-up,
coverage-driven).

## Step 1 — Dispatch theme-researcher

Invoke the `theme-researcher` agent, passing the `macro_thesis_id` argument if given (else
no argument — the agent scans all approved macro theses). Wait for its full response. If it
reports the macro thesis is already fully theme-covered, or the approved set is empty,
relay that plainly and stop — zero proposals is a valid outcome.

## Step 2 — Parse the structured output block

The agent's response ends with one fenced ` ```json ` block shaped like:
```json
{
  "summary": "...",
  "macro_thesis_id": 7,
  "regime_context": {"regime_quadrant": "...", "macro_thesis_title": "...", "existing_theme_coverage": 0},
  "theme_proposals": [ {theme_code, name, description, conviction_band, stage, macro_thesis_id, evidence_citation_ids}, ... ],
  "theme_holding_proposals": [ {theme_code, symbol, exposure_strength, direction, mechanism_text, evidence_citation_ids}, ... ],
  "evidence": [ {claim, tier, source_type, source_table, source_as_of, snapshot_data}, ... ]
}
```
If there is no such block, or it doesn't parse, stop and tell the user plainly — do not
invent a proposal or retry silently. If both proposal arrays are empty, report the
regime→theme mapping as the run's deliverable and stop.

**Validate the top-down discipline:** every `theme_proposal.macro_thesis_id` must be
non-NULL (a NULL one is a bottom-up theme — `sector-screener`'s output, not this agent's).
If any proposal has a NULL `macro_thesis_id`, flag it and skip logging that one.

## Step 3 — Log one agent_runs row per proposal

Log ALL theme proposals first, then all theme-holding proposals (a holding's `theme_code`
may reference a same-run theme, and `asx theme holding open --from-agent-run` hard-fails if
the theme row doesn't exist yet).

For each `theme_proposals` entry: `asx agent-run log theme-researcher --object-type theme
--summary ... --proposal-json ... --evidence-json ...`
For each `theme_holding_proposals` entry: same with `--object-type theme_holding`.

Pass the FULL `evidence` array unchanged to every call (the `"local:N"` positions index
into that same array). Use scratchpad files + command substitution for the JSON payloads,
never inline shell strings. Capture each printed `run_id`. If a call hard-fails (speculative
citation, Pydantic validation, unknown agent_name — theme-researcher must be in
`_KNOWN_AGENTS`), report that proposal's error and continue with the rest.

## Step 4 — Report results

```
Logged theme proposal #<N>: "<name>" (from macro thesis #<M>) (run_id=<R1>)
Logged theme-holding proposal #<K>: <symbol> → <theme_code> (run_id=<R2>)
Review, then (order matters — themes before their holdings):
  asx theme open --from-agent-run <R1>
  asx theme approve <theme_id> --reason "..."
  asx theme holding open --from-agent-run <R2>
  asx theme holding approve <holding_id> --reason "..."
```
List failures separately from successes.

## Boundaries

This command logs proposals for human review — it never opens or approves anything itself.
A human reads the evidence and runs the open/approve verbs. The agent runs on the read-only
Supabase MCP; this command's own `asx agent-run log` calls are the only DB writes in the
flow, they are append-only audit rows, and they happen in attended sessions only (never
from a scheduled/unattended loop). s766B firewall: proposing a `theme_holding` is "this
instrument has exposure to this theme", never "buy this."
