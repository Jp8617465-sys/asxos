"""
asxos.domain.portfolio — M13 portfolio construction.

Path A scope per the plan's Part 0 Q1: this code path is for James-as-user_id=1
personal tooling. The CLI commands check `ASXOS_PERSONAL_USE=1` before
dispatching; the brief section 6 checks the same flag plus
`ASXOS_PORTFOLIO_BRIEF_ENABLED=1` before rendering. The module itself is
importable without the flag so tests don't have to set it.

s766B Corporations Act 2001 (Cth) / Westpac v ASIC (2021) FCAFC 2: any
output of this code is "personal advice." Path A defers AFSL authorisation by
keeping the surface single-user. Path B (general advice with architectural
separation) is parked until/unless the screening pivot exposes a wider audience.
"""
