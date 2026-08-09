# Policy amendment — decision-surface doctrine (output-attached firewall)

**Status: DRAFT for James.** Governor ruling D5 (PR #78 §6, 2026-08-09) approved this
doctrine as a governed-doc amendment. The authority-guard correctly prevents arbi from
editing `docs/product/portfolio-policy.md` directly — this file carries the exact text;
James applies it (insert the section below into `docs/product/portfolio-policy.md`
immediately before `## What requires James's explicit approval`) or directs its
application after merging.

Source: the 2026-08-08 finance red-team (`docs/proposals/finance-red-team-2026-08-08.md`,
register #3/#20, synthesis §3): the s766B protections attached to pipelines, while the
most directive surface the system ever produced was minted in an ad-hoc lane no gate
touched.

---

## Decision-surface doctrine — the output-attached firewall (D5, approved 2026-08-09)

- **Functional-influence classification attaches to the OUTPUT, not the pipeline.** Every
  surface an investor sees is one of {informational · framing-influential ·
  functionally-directive}. Any generated surface that renders a live position and names or
  ranks an action — a CLI command, an option list, an "act now" framing — is
  **functionally-directive by definition**, regardless of which lane, tool, or artifact
  produced it, and regardless of any disclaimer footer.
- **A functionally-directive surface must pass the four-step ordering before it renders:**
  1. **Rule integrity** — the rule it invokes is attested `underwritten`, coherent, and in
     the state it claims (not placeholder, not born-breached, not a stale trigger). Fail ⇒
     the only legitimate output is a **rule-repair card**; never an action card.
  2. **Enforceability** — any implied action is executable (no disposal lock, no
     instrument constraint). Fail ⇒ every trigger is demoted to ALERT/REVIEW **on the face
     of the surface**, with the constraint stated.
  3. **Facts** — the decision-relevant facts are current and evaluated (tape vs stored
     flag; falsifiers vs actuals; tax consequence per path; FX basis). Unavailable facts
     are printed on the surface, never papered over.
  4. **Options last** — unranked or status-quo-first, each carrying its own prerequisites
     and tax consequence. **"Insufficient evidence — no decision solicited today" is a
     valid and sometimes the correct output.**
- **Placeholder rules never reach action framing.** A rule with `attestation =
  'placeholder'` (D4, migration 0042) may not appear on any action-framed surface and may
  not have an action verb attached to it in any alert.
- Wording discipline continues to apply (the discipline module's verb-stripping stands),
  but wording alone never reclassifies a surface: influence is a property of structure.

---

*Mechanical anchors already implementing this doctrine in code (rules-integrity build):*
`asxos/domain/theses/alerts.py` (action verbs iff underwritten + hard_exit + unlocked),
`enter_thesis()`'s attestation gate, and the brief `active_theses` collector's
attestation/lock/condition-state rendering.
