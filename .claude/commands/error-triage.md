# Error Triage — Root Cause Analysis

$ARGUMENTS = the error message, stack trace, or description of the problem.

## Steps

**Step 1 — Locate origin**
Search the codebase for the error string or the function/module in the stack trace:
- Extract the key error phrase (e.g., `KeyError: 'prob_up'`, `Cannot read properties of undefined`)
- Search: `grep -r "[error phrase]" app/ jobs/ frontend/ --include="*.py" --include="*.ts" --include="*.tsx" -n`
- Identify the file:line where the error originates

**Step 2 — Check Render logs**
Via Render MCP:
- Search logs for the error phrase
- Report: frequency (how many times in last 24h), first occurrence, last occurrence
- Identify whether it's getting worse, stable, or intermittent
- Check if it correlates with a recent deploy

**Step 3 — Reproduce + understand**
- Read the file at the origin line and surrounding context (±20 lines)
- Identify the root cause: what state or input causes this?
- Check if there's a related test that should have caught it

**Step 4 — Propose fix**
- Write the minimal fix (patch the root cause, not just the symptom)
- State what test should be added or updated to prevent regression
- Estimate blast radius: is this affecting all users, specific users, or specific data states?

## Output

```
Error Triage: [error summary]
──────────────────────────────
Origin:      [file:line]
Frequency:   [N occurrences in last 24h]
First seen:  [timestamp]
Root cause:  [one paragraph]

Proposed fix:
[code diff or description]

Test to add:
[test description]

Blast radius: [all users / specific condition / data-dependent]
```

## Constraints
- Do NOT apply the fix without explicit user confirmation
- If the error is in a migration or model artefact, stop and ask before proceeding
- If Render logs are unavailable, note this and proceed with codebase analysis only
