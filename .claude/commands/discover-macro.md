# Discover Macro Theses — `/discover-macro`

No arguments. Invokes the `macro-economist` discovery agent, logs its findings
into `agent_runs`/`agent_evidence`, and reports the resulting run IDs so a
human can review and approve them.

## Why a slash command and not an agent

Same reason as `/pm-review` (see `.claude/commands/pm-review.md`): a subagent
cannot shell out to a CLI command reliably as its own final action the way the
main loop can, and this command's whole job — dispatch the agent, parse its
structured output, persist it — is exactly the kind of orchestration that
belongs in the main loop, not inside another agent.

**Note the name**: `.claude/commands/discover.md` already exists (an unrelated
read-only system-health audit). This command is `/discover-macro`, not
`/discover` — do not confuse the two.

## Step 1 — Dispatch macro-economist

Invoke the `macro-economist` agent (no arguments needed — it reads the
current market snapshot itself). Wait for its full response.

## Step 2 — Parse the structured output block

The agent's response ends with one fenced ` ```json ` block shaped like:
```json
{
  "summary": "...",
  "proposals": [ {title, thesis_text, regime_quadrant, horizon_months,
                  catalyst, falsifier, data_signals, evidence_citation_ids}, ... ],
  "evidence": [ {claim, tier, source_type, source_table, source_as_of,
                 snapshot_data}, ... ]
}
```
If the agent's response has no such block, or it doesn't parse as JSON, or
`proposals` is empty, stop and tell the user plainly — do not invent a
proposal or retry silently.

## Step 3 — Log one agent_runs row per proposal

For **each** entry in `proposals`, call `asx agent-run log` once, passing:
- `--object-type macro_thesis`
- `--summary` — the run's overall `summary` field from Step 2 (same for
  every proposal in this run)
- `--proposal-json` — that ONE proposal object, serialized as JSON
- `--evidence-json` — the FULL `evidence` array from Step 2, unchanged (every
  proposal's `evidence_citation_ids` uses `"local:N"` positions into this same
  array, so resubmitting it whole means no re-indexing is needed; a small
  amount of `agent_evidence` duplication across proposals from the same run
  is an acceptable tradeoff for a personal, low-volume system, not a
  correctness issue)

**Practical note on shell-quoting**: these JSON payloads can be long and
contain nested quotes — don't try to inline them into a Bash command string
directly. Write each proposal's JSON and the shared evidence JSON to files
under the scratchpad directory (via the Write tool), then invoke the CLI with
command substitution reading those files, e.g.:
```bash
ASXOS_PERSONAL_USE=1 asx agent-run log macro-economist \
  --object-type macro_thesis \
  --summary "$(cat /path/to/scratchpad/summary.txt)" \
  --proposal-json "$(cat /path/to/scratchpad/proposal_0.json)" \
  --evidence-json "$(cat /path/to/scratchpad/evidence.json)"
```
Capture the printed `run_id` from each call's output (`✓ Logged agent run #N`).

If any call fails (a hard-fail from `log_agent_run()` — e.g. a citation
resolves to a speculative-tier claim, or a proposal fails Pydantic
validation), report that proposal's error to the user and continue with the
remaining proposals — one bad proposal must not block the others in the same
run.

## Step 4 — Report results

For each successfully logged run, tell the user:
```
Logged macro thesis proposal #<N>: "<title>" (run_id=<run_id>)
Review it, then: asx macro-thesis open --from-agent-run <run_id>
                  asx macro-thesis approve <macro_thesis_id> --reason "..."
```
If any proposals failed to log, list them with their error messages
separately, clearly distinguished from the successes.

## Boundaries

This command logs proposals for human review — it never approves anything
itself and never calls `asx macro-thesis open`/`approve` on the user's
behalf. A human must read the evidence and explicitly run those commands.
