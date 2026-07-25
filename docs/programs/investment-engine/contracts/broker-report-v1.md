# BrokerReportVersionV1

**Normative wire shape:** [`../schemas/broker-report-v1.schema.json`](../schemas/broker-report-v1.schema.json)

## Purpose

A broker-report version is an immutable, evidence-linked point of view—not a mutable text blob.
Migration 0040 `theses.report_sections` and the Phase C CLI/rendering shipped in PR #68 are the
starting point.

## Required content

- Thesis/report identity, version, flavour, data-as-of, and context/source hashes.
- Executive view.
- Evidence-linked claim register.
- Bear, base, and bull scenarios.
- Valuation/payoff framing.
- Catalysts and falsifiers.
- Risks and unanswered questions.
- Entry/stop/target/timeline discipline wrapper where available.
- Ordered report sections and figures.
- Governance state and producer/version metadata.

Every capital-relevant figure follows the existing `ReportFigure` provenance contract. Derived
figures show formulas over cited inputs. Prose does not smuggle numeric capital claims around that
contract.

`source_sha256` identifies the ordered proposal/evidence source manifest and is
not the report artifact's own digest. The root artifact uses the programme RFC
8785/SHA-256 `canonical_hash` envelope; only
`/canonical_hash/payload_sha256` is removed while computing it.

## Versioning and monitoring

- Approval never mutates the original draft payload.
- A changed claim, scenario, figure, catalyst, falsifier, or discipline input creates a new version.
- Monitoring produces an event and proposed revision; it cannot approve or overwrite.
- Original forecasts remain linked to paper outcomes even after later revisions.
- A report with stale mandatory evidence may render for audit but cannot advance.
