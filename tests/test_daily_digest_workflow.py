"""Pins on ``daily-digest.yml`` — AGENTS.md §12's mechanical lines as a scheduled job.

What is pinned: the slot (21:00 UTC = 07:00 Brisbane, the §12 deadline, after daily-brief
and ≥30 min from every Routine), a dispatch whose default posts nothing, a `main` checkout,
one secret (the PAT) and nothing that would put the lane in the James-reserved set
(no RESEND_API_KEY, no EODHD_API_KEY), and that the script — not a model — writes it.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".github/workflows/daily-digest.yml"
TEXT = PATH.read_text(encoding="utf-8")
DOC = yaml.safe_load(TEXT)
TRIGGERS = DOC.get("on") or DOC.get(True)


def test_scheduled_at_0700_brisbane_and_dispatchable() -> None:
    assert TRIGGERS["schedule"] == [{"cron": "0 21 * * *"}]
    assert "workflow_dispatch" in TRIGGERS


def test_dispatch_default_is_a_dry_run() -> None:
    inputs = TRIGGERS["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] is True
    assert "--dry-run" in TEXT


def test_checks_out_main_with_read_only_permissions_and_one_secret() -> None:
    assert "ref: refs/heads/main" in TEXT
    assert DOC["permissions"] == {"contents": "read"}
    assert set(re.findall(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}", TEXT)) == {"ARBI_GITHUB_TOKEN"}


def test_the_script_writes_it_and_no_model_does() -> None:
    assert "scripts/post_daily_digest.py" in TEXT
    assert "claude-code-action" not in TEXT
    assert 'ASXOS_DIGEST_ISSUE: "271"' in TEXT


def test_it_is_a_recognised_scheduled_lane() -> None:
    from asxos.secondbrain.contradictions import SCHEDULED_LANES

    assert "daily-digest" in SCHEDULED_LANES
