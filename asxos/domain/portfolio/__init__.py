"""
asxos.domain.portfolio — M13 portfolio construction.

Path A scope per the plan's Part 0 Q1: this code path is for James-as-user_id=1
personal tooling. The CLI commands check `ASXOS_PERSONAL_USE=1` before
dispatching, and so does every model-independent brief card. The second gate
`ASXOS_PORTFOLIO_BRIEF_ENABLED` is gone — it and the allocator brief section it
fronted were deleted under A-34 (2026-09-14), leaving `ASXOS_PERSONAL_USE` as
the single firewall gate. The module itself is importable without the flag so
tests don't have to set it.

s766B Corporations Act 2001 (Cth) / Westpac v ASIC (2021) FCAFC 2: any
output of this code is "personal advice." Path A defers AFSL authorisation by
keeping the surface single-user. Path B (general advice with architectural
separation) is parked until/unless the screening pivot exposes a wider audience.
"""
