---
paths:
  - asxos/domain/models/**
---

# ML Pipeline Rules — asxos (retired 2026-08-19)

Model A's training chain, artefacts, feature engine, signal-generation and
threshold machinery, and the associated tests this file used to document
were all removed 2026-08-19 as part of the Model A retirement — see
`docs/product/model-a-reference-manifest.md` for the full disposition and
`CLAUDE.md` rule #11 for the standing quarantine policy.

What remains under `asxos/domain/models/` is `production_gate.py` —
rule #11's mechanical enforcement point (`resolve_production_model()` /
`ModelGateDormant`), which is generic (it gates *any* model, not
specifically Model A) and stays permanently. It needs no ML-specific
convention beyond ordinary Python/asyncpg discipline.

This file is a placeholder rather than deleted outright — a Bash-level
authority guard blocks `git rm` on `.claude/rules/**` from this session, and
routing an actual deletion through that guard is a separate, deliberate
action for James, along with dropping this file from `CLAUDE.md`'s
"Auto-activating rules" list.
