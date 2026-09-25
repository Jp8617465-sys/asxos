"""The routine-liveness check — K-08's 90%, the part that needed no console.

`_preamble.md` §1's START comment detects a Routine that woke and did nothing,
but only if something alive reads it, and the reader was itself a Routine. These
tests pin the shapes that matter: a fire that never happened, a fire that began
and never closed, and — just as important for a watchdog nobody will read on a
good day — the cases that must stay SILENT.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from scripts.check_routine_ledger import (
    Routine,
    check,
    load_routines,
    parse_run_lines,
    previous_fire,
)

_PRODUCT = Routine(name="daily-product", cron="30 17 * * *", budget_min=120)
_SECURITY = Routine(name="weekly-security", cron="0 12 * * 0", budget_min=60)


def _comments(*bodies: str) -> str:
    return json.dumps([{"body": b} for b in bodies])


def _run(name: str, fire: str, status: str) -> str:
    return f"ROUTINE-RUN name={name} fire={fire} doc_sha=abc123 status={status}\n"


# --- previous_fire ----------------------------------------------------------


def test_daily_cron_before_the_fire_time_goes_back_a_day() -> None:
    now = datetime(2026, 9, 26, 10, 0, tzinfo=UTC)  # before 17:30
    assert previous_fire("30 17 * * *", now) == datetime(2026, 9, 25, 17, 30, tzinfo=UTC)


def test_daily_cron_after_the_fire_time_is_today() -> None:
    now = datetime(2026, 9, 26, 23, 0, tzinfo=UTC)
    assert previous_fire("30 17 * * *", now) == datetime(2026, 9, 26, 17, 30, tzinfo=UTC)


def test_weekly_cron_finds_the_most_recent_matching_weekday() -> None:
    # 2026-09-26 is a Saturday; cron dow 0 = Sunday → the 20th.
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    assert previous_fire("0 12 * * 0", now) == datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def test_weekly_cron_on_its_own_day_before_the_hour_goes_back_a_week() -> None:
    now = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)  # Sunday, before 12:00
    assert previous_fire("0 12 * * 0", now) == datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "cron",
    [
        "30 17 1 * *",  # day-of-month
        "30 17 * 6 *",  # month
        "*/5 * * * *",  # step minute
        "30 17 * * 1-5",  # dow range
        "30 17 * *",  # not five fields
    ],
)
def test_an_unsupported_schedule_shape_raises_rather_than_passing(cron: str) -> None:
    """The correct failure for a watchdog. A shape it cannot reason about must
    stop the check, never silently report healthy."""
    with pytest.raises(ValueError):
        previous_fire(cron, datetime(2026, 9, 26, 12, 0, tzinfo=UTC))


# --- parse_run_lines -------------------------------------------------------


def test_parses_start_and_end_from_comment_bodies() -> None:
    runs = parse_run_lines(
        _comments(
            _run("daily-product", "2026-09-25T17:32:35Z", "START"),
            "some prose, then\n" + _run("daily-product", "2026-09-25T17:32:35Z", "END"),
        )
    )
    assert [(r.name, r.status) for r in runs] == [
        ("daily-product", "START"),
        ("daily-product", "END"),
    ]
    assert runs[0].fire == datetime(2026, 9, 25, 17, 32, 35, tzinfo=UTC)


def test_prose_about_a_routine_is_not_a_run_line() -> None:
    """Comment bodies are external content, read as DATA. Only the literal line
    shape counts — otherwise a digest paragraph mentioning a fire would forge a
    heartbeat, which is the one thing this check must not let happen."""
    runs = parse_run_lines(
        _comments("daily-product fired at 2026-09-25T17:32:35Z and status was START, roughly")
    )
    assert runs == []


def test_an_unparseable_fire_timestamp_is_skipped_not_fatal() -> None:
    runs = parse_run_lines(_comments(_run("daily-product", "not-a-date", "START")))
    assert runs == []


# --- check -----------------------------------------------------------------


def test_a_fire_that_never_happened_is_reported() -> None:
    now = datetime(2026, 9, 25, 23, 0, tzinfo=UTC)  # well past 17:30 + 120min + 3h

    problems = check([_PRODUCT], [], now)

    assert len(problems) == 1
    assert "no START" in problems[0]


def test_a_fire_that_began_and_never_closed_is_reported() -> None:
    """The exact 2026-09-22 shape: the scheduler recorded delivery, the session
    stalled on a pending approval, and no END was ever posted."""
    now = datetime(2026, 9, 25, 23, 0, tzinfo=UTC)
    runs = parse_run_lines(_comments(_run("daily-product", "2026-09-25T17:32:35Z", "START")))

    problems = check([_PRODUCT], runs, now)

    assert len(problems) == 1
    assert "no matching END" in problems[0]


def test_a_matched_pair_is_silent() -> None:
    now = datetime(2026, 9, 25, 23, 0, tzinfo=UTC)
    runs = parse_run_lines(
        _comments(
            _run("daily-product", "2026-09-25T17:32:35Z", "START"),
            _run("daily-product", "2026-09-25T17:32:35Z", "END"),
        )
    )

    assert check([_PRODUCT], runs, now) == []


def test_an_end_carrying_a_different_fire_does_not_match() -> None:
    """The fire timestamp is the run's identity in the contract, so an END must
    carry the SAME one to vouch for a START.

    Both lines here sit inside the window deliberately. An earlier version of
    this test used yesterday's END, which the window filter discarded before the
    match was reached — so it passed whether the code matched on `(name, fire)`
    or on name alone, and a mutation to the latter went green. Caught by that
    mutation; the shape below is the one that actually pins the mechanism.
    """
    now = datetime(2026, 9, 25, 23, 0, tzinfo=UTC)
    runs = parse_run_lines(
        _comments(
            _run("daily-product", "2026-09-25T17:32:35Z", "START"),
            # Same day, inside the window, different fire — a copy-paste END, or
            # an END written from a re-read clock instead of the START's value.
            _run("daily-product", "2026-09-25T17:45:00Z", "END"),
        )
    )

    problems = check([_PRODUCT], runs, now)

    assert len(problems) == 1
    assert "no matching END" in problems[0]


def test_a_fire_still_inside_its_window_is_silent() -> None:
    """Quiet-by-default, and load-bearing: `nightly-check` runs at 15:17 UTC,
    before the 17:30 fire, so every run of this check sees one routine mid-window.
    Reporting that as dead would make the check cry wolf daily and be switched
    off — the fate of the two scheduled loops this repo already retired."""
    now = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)  # 30 min into a 120-min budget

    assert check([_PRODUCT], [], now) == []


def test_an_overrunning_fire_is_not_called_dead() -> None:
    """The 09-19 and 09-22 fires both ran past T+290 and both posted END. A
    grace tighter than the real overruns would have paged on a live session."""
    fire = datetime(2026, 9, 25, 17, 30, tzinfo=UTC)
    now = fire + timedelta(minutes=250)  # past budget, inside grace

    assert check([_PRODUCT], [], now) == []


def test_each_routine_is_judged_on_its_own_cron_and_budget() -> None:
    now = datetime(2026, 9, 26, 23, 0, tzinfo=UTC)  # Saturday
    runs = parse_run_lines(
        _comments(
            _run("daily-product", "2026-09-26T17:30:00Z", "START"),
            _run("daily-product", "2026-09-26T17:30:00Z", "END"),
        )
    )

    problems = check([_PRODUCT, _SECURITY], runs, now)

    # daily-product is clean; weekly-security's last expected fire was Sunday
    # the 20th and has no lines at all.
    assert len(problems) == 1
    assert problems[0].startswith("weekly-security")


# --- load_routines ---------------------------------------------------------


def test_the_live_routine_docs_are_all_readable_and_supported() -> None:
    """Coverage is derived from the docs, so a new routine doc joins this check
    automatically — and a doc with a schedule shape `previous_fire` cannot read
    fails HERE, at a desk, rather than at 15:17 UTC.
    """
    routines = load_routines()

    assert {r.name for r in routines} == {"daily-product", "nightly-steward", "weekly-security"}
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    for r in routines:
        assert previous_fire(r.cron, now) <= now
        assert r.budget_min > 0


def test_frontmatter_missing_a_required_field_raises(tmp_path) -> None:
    (tmp_path / "broken.md").write_text(
        '---\nname: broken\ncron: "0 1 * * *"\n---\n\n# no budget_min\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="budget_min"):
        load_routines(tmp_path)


# --- drift guard: the ledger issue number appears in two places -------------


def test_the_workflow_reads_the_same_ledger_issue_the_readme_declares() -> None:
    """`nightly-check.yml` hardcodes the issue number and `README.md` declares it
    in prose. Neither can reasonably import the other, so they are pinned against
    each other instead: change one and this fails at a desk rather than at 15:17
    UTC, where a wrong number would make the check read an empty comment list and
    report every routine dead.
    """
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "docs/ops/routines/README.md").read_text(encoding="utf-8")
    workflow = (repo / ".github/workflows/nightly-check.yml").read_text(encoding="utf-8")

    declared = re.search(r"the ledger #(\d+)", readme)
    assert declared, "README.md no longer declares 'the ledger #<n>'"

    used = re.search(r"/issues/(\d+)/comments", workflow)
    assert used, "nightly-check.yml no longer reads an issue's comments"

    assert used.group(1) == declared.group(1), (
        f"nightly-check.yml reads #{used.group(1)} but README.md declares the ledger "
        f"as #{declared.group(1)} — a wrong number reports every routine dead"
    )


def test_the_ledger_job_holds_no_write_permission() -> None:
    """It reads a ledger and judges it. A watchdog that could write to the thing
    it watches is not one."""
    from pathlib import Path

    import yaml

    repo = Path(__file__).resolve().parent.parent
    wf = yaml.safe_load((repo / ".github/workflows/nightly-check.yml").read_text(encoding="utf-8"))
    perms = wf["jobs"]["routine-ledger"]["permissions"]

    assert perms == {"contents": "read", "issues": "read"}
    assert all(v == "read" for v in perms.values())
