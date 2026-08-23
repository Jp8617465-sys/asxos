# Where I stopped

Two draft PRs open, both green, neither merged: **#161** (3 cleanups) · **#163** (audit P0/P1 — schema reproducibility, UTC session pin, verified backup, observable alerts).

**Yours next:** merge or reject #161/#163, then apply the 4 artifacts in #163's body that `.github/**` and prod DDL blocked — restore-drill weekly schedule, drift-check CI step, two `screening_runs` comment fixes.

**Live and unfixed:** every scheduled brief stamps `as_of` a day behind Sydney; 2026-08-16 was stamped Sunday while `snapshot_portfolio` used Friday. Phase 2, needs your sign-off per call site.

**Stale checkout:** `authority-guard.sh` here is ~20 commits behind and still enforces the `migrations/` deny you removed in #162 — fast-forward it. Rule #11 stands: no Model A output for capital decisions.
