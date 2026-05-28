from __future__ import annotations

import os

import typer
from rich.console import Console

console = Console()


def _require_personal_use() -> None:
    """Hard-fail if the personal-use firewall flag isn't set.

    Plan Part 0 Q1: this code path is "personal advice" under s766B; the
    flag is the architectural firewall preventing accidental public exposure.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise typer.BadParameter(
            "Portfolio commands require ASXOS_PERSONAL_USE=1. "
            "This surface generates personal-advice outputs under s766B "
            "(Corporations Act 2001) and is gated to single-user use only. "
            "Set the env var in your shell or in your secrets file."
        )
