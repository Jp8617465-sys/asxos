# Paper Intent v1

`paper-intent-v1` records the evaluator's non-routable decision to trade or take
no action for one origin and branch.

**Machine contract:** [`paper-intent-v1.schema.json`](../schemas/paper-intent-v1.schema.json)

The intent resolves one frozen origin, proposal, and typed
[`sizing-decision-v1`](sizing-decision-v1.md). Each line records asset, side,
requested quantity and notional, reference price, the exact sized-line digest,
decision reason, and source hash used at the knowledge cutoff. For `RECORDED`,
the semantic validator requires a one-to-one match to an `APPROVED` line in the
referenced `SIZED` artifact: asset, side, quantity, notional, price, and
`sizing_line_sha256` all match. Proposal deltas alone cannot create an intent.
`NO_ACTION` and `REJECTED` are first-class outcomes with zero lines;
`RECORDED` requires at least one line.

The sizing-line digest is SHA-256 over the RFC 8785 canonical sizing line after
excluding only `line_item_sha256`; `line_id` remains in the preimage. Production
validators recompute it before comparing `sizing_line_id` and
`sizing_line_sha256`.

The intent is not an order and cannot be approved or routed. It is
`PAPER_ONLY`, simulated, and independent of live holdings and broker surfaces.
