"""Staged asxos-control cores. Destined for Jp8617465-sys/asxos-control.

Nothing in this package writes GitHub Checks, repository variables, or secrets.
Callers in asxos-control workflows perform those side effects after this package
returns a fail-closed decision.
"""

from asxos_control.activate import evaluate_activation
from asxos_control.breaker import evaluate_breaker
from asxos_control.classify import classify
from asxos_control.digest import DIGEST_CRON_UTC, digest_template
from asxos_control.restore import evaluate_restore

__all__ = [
    "DIGEST_CRON_UTC",
    "classify",
    "digest_template",
    "evaluate_activation",
    "evaluate_breaker",
    "evaluate_restore",
]
