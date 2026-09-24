"""asxos/domain/governance/github_commands.py — the pure parser behind S8."""
from __future__ import annotations

import pytest

from asxos.domain.governance import github_commands as gc

OWNER = "Jp8617465-sys"


def _c(comment_id: int, body: str, author: str = OWNER) -> gc.IssueComment:
    return gc.IssueComment(comment_id=comment_id, author_login=author, body=body)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("APPROVE thesis 42 evidence is fresh and the plan is sane", gc.ThesisGovernanceCommand("approve", 42, "evidence is fresh and the plan is sane")),
        ("reject thesis 7 peak-cycle ROE\nmore text below is ignored", gc.ThesisGovernanceCommand("reject", 7, "peak-cycle ROE")),
        ("\n\n  Approve Thesis 3 ok  \n", gc.ThesisGovernanceCommand("approve", 3, "ok")),
        ("DISPOSE dpk-cba-1-2026-09-17 accept", gc.DisposeCommand("dpk-cba-1-2026-09-17", "accept", None)),
        ("dispose dpk-hubs-13-2026-09-17 Defer wait for the result", gc.DisposeCommand("dpk-hubs-13-2026-09-17", "defer", "wait for the result")),
        ("DISPOSE dpk-cba-1-2026-09-17 request_revision", gc.DisposeCommand("dpk-cba-1-2026-09-17", "request_revision", None)),
    ],
)
def test_commands_parse_from_the_first_line(body: str, expected: gc.Command) -> None:
    assert gc.parse_command(body) == expected


@pytest.mark.parametrize(
    "body",
    ["", "   ", "thanks, looks good", "Approved!", "<!-- asxos-decisions:applied comment_id=1 -->\n✅ Applied", "the APPROVE word mid-line"],
)
def test_data_is_never_a_command(body: str) -> None:
    assert gc.parse_command(body) is None


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ("APPROVE thesis 42", "reason is required"),
        ("APPROVE 42 ok", "reason is required"),
        ("REJECT thesis x nope", "reason is required"),
        ("DISPOSE dpk-cba-1-2026-09-17 maybe", "unknown verdict"),
        ("DISPOSE 12345 accept", "dpk-"),
        ("DISPOSE", "dpk-"),
    ],
)
def test_a_malformed_command_is_a_syntax_error_not_silence(body: str, fragment: str) -> None:
    with pytest.raises(gc.CommandSyntaxError, match=fragment):
        gc.parse_command(body)


def test_only_the_owner_commands_and_answered_ones_are_terminal() -> None:
    comments = [
        _c(5, "APPROVE thesis 1 fine"),
        _c(6, "APPROVE thesis 2 also fine", author="someone-else"),
        _c(7, f"{gc.marker_for('applied', 5)}\n✅ Applied `APPROVE thesis 1`"),
        _c(8, "REJECT thesis 3 no"),
        _c(9, f"{gc.marker_for('refused', 8)}\n❌ Not applied"),
        _c(10, "just a note to self"),
        _c(11, "DISPOSE dpk-cba-1-2026-09-17 accept"),
        _c(12, "APPROVE thesis 4"),  # syntax error: no reason
        _c(4, "dispose dpk-x-9-2026-09-10 reject stale"),  # lower id, must come first
    ]
    pending = gc.select_commands(comments, owner_login="jp8617465-sys")  # case-insensitive login
    assert [(p.comment.comment_id, p.summary, p.error is None) for p in pending] == [
        (4, "DISPOSE dpk-x-9-2026-09-10 reject", True),
        (11, "DISPOSE dpk-cba-1-2026-09-17 accept", True),
        (12, "APPROVE thesis 4", False),
    ]
    assert pending[2].error is not None and "reason is required" in pending[2].error


def test_marker_round_trips() -> None:
    marker = gc.marker_for("refused", 123)
    assert marker.startswith(gc.MARKER_PREFIX)
    assert gc.parse_marker(f"{marker}\n❌ Not applied `x`") == gc.MarkerReply("refused", 123)
    assert gc.parse_marker("nothing here") is None


# ---------------------------------------------------------------------------
# MANDATE approve|reject <id> <reason> — the mandate layer's ratification verb
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("body", "action", "mandate_id", "reason"),
    [
        ("MANDATE approve 7 ratified after reading the memo", "approve", 7, "ratified after reading the memo"),
        ("mandate reject 8 the drawdown tolerance is wrong\nmore context", "reject", 8, "the drawdown tolerance is wrong"),
    ],
)
def test_mandate_commands_parse(body: str, action: str, mandate_id: int, reason: str) -> None:
    cmd = gc.parse_command(body)
    assert isinstance(cmd, gc.MandateGovernanceCommand)
    assert (cmd.action, cmd.mandate_id, cmd.reason) == (action, mandate_id, reason)
    assert cmd.summary == f"MANDATE {action.upper()} {mandate_id}"


@pytest.mark.parametrize("body", ["MANDATE approve 7", "MANDATE bless 7 please", "MANDATE approve seven ok"])
def test_a_malformed_mandate_command_is_answered_not_ignored(body: str) -> None:
    with pytest.raises(gc.CommandSyntaxError, match=r"MANDATE approve\|reject"):
        gc.parse_command(body)
