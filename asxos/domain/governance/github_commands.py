"""
GitHub-comment commands for governance decisions (F-E2E r2, S8) — the pure parser.

James does not run CLIs; he reads GitHub on a phone. A comment on the pinned
"asxos — decisions" issue is the one-line form of the three decisions that are
his to make on system-proposed content:

    APPROVE thesis <id> <reason>
    REJECT thesis <id> <reason>
    DISPOSE <packet_id> <verdict> [note]      verdict: accept | request_revision | reject | defer

Only the first non-blank line of a comment is read; the rest is free text.
Keywords are case-insensitive; ids are not. A comment that does not start with
one of the three keywords is data, never a command, and is left alone.

Trust boundary, stated once: this module decides only what a comment *says*.
Who may say it — the repository owner's login and nobody else — is
`select_commands`' filter, and the job passes the login it fetched from the
repository itself, never from the comment. Every other comment on the issue,
from any other login, is inert. A command is applied at most once: the job
answers each one with a marker reply (`MARKER_PREFIX`), and a comment whose
marker reply already exists is never re-read, whether it was applied or
refused.

No I/O here: the job (`jobs/apply_github_decisions.py`) fetches and posts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

from asxos.domain.decision_engine.delivery import DispositionVerdict

#: HTML comment prefix of the reply the job posts under every applied or refused command.
MARKER_PREFIX: Final[str] = "<!-- asxos-decisions:"
_MARKER_RE: Final[re.Pattern[str]] = re.compile(
    r"<!-- asxos-decisions:(?P<outcome>applied|refused) comment_id=(?P<comment_id>\d+) -->"
)

_APPROVE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<verb>approve|reject)\s+thesis\s+(?P<thesis_id>\d+)\s+(?P<reason>\S.*)$", re.IGNORECASE
)
_DISPOSE_RE: Final[re.Pattern[str]] = re.compile(
    r"^dispose\s+(?P<packet_id>dpk-[a-z0-9.\-]+)\s+(?P<verdict>[a-z_]+)(?:\s+(?P<note>\S.*))?$",
    re.IGNORECASE,
)
_VERDICTS: Final[frozenset[str]] = frozenset({"accept", "request_revision", "reject", "defer"})
#: Words that begin a command line; anything else is data and is never reported on.
_COMMAND_WORDS: Final[frozenset[str]] = frozenset({"approve", "reject", "dispose"})


@dataclass(frozen=True)
class ThesisGovernanceCommand:
    action: Literal["approve", "reject"]
    thesis_id: int
    reason: str

    @property
    def summary(self) -> str:
        return f"{self.action.upper()} thesis {self.thesis_id}"


@dataclass(frozen=True)
class DisposeCommand:
    packet_id: str
    verdict: DispositionVerdict
    note: str | None

    @property
    def summary(self) -> str:
        return f"DISPOSE {self.packet_id} {self.verdict}"


Command = ThesisGovernanceCommand | DisposeCommand


class CommandSyntaxError(ValueError):
    """A line that starts like a command but does not parse — reported back, not applied."""


@dataclass(frozen=True)
class IssueComment:
    comment_id: int
    author_login: str
    body: str


@dataclass(frozen=True)
class MarkerReply:
    outcome: Literal["applied", "refused"]
    comment_id: int


def parse_marker(body: str) -> MarkerReply | None:
    """The marker the job left under a command, if this comment is one of its replies."""
    m = _MARKER_RE.search(body)
    if m is None:
        return None
    return MarkerReply(outcome=m.group("outcome"), comment_id=int(m.group("comment_id")))  # type: ignore[arg-type]


def marker_for(outcome: Literal["applied", "refused"], comment_id: int) -> str:
    return f"{MARKER_PREFIX}{outcome} comment_id={comment_id} -->"


def _first_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def parse_command(body: str) -> Command | None:
    """The command a comment's first non-blank line states, or None when it is data.

    Raises CommandSyntaxError when the line begins with a command word but the
    rest does not parse (missing reason, unknown verdict, malformed id) — that
    is a command James meant to give, so the job answers it rather than
    silently ignoring it.
    """
    line = _first_line(body)
    if not line or line.startswith("<!--"):
        return None
    word = line.split(maxsplit=1)[0].lower()
    if word not in _COMMAND_WORDS:
        return None
    if word in {"approve", "reject"}:
        m = _APPROVE_RE.match(line)
        if m is None:
            raise CommandSyntaxError(
                f"expected `{word.upper()} thesis <id> <reason>` — the reason is required"
            )
        return ThesisGovernanceCommand(
            action=m.group("verb").lower(),  # type: ignore[arg-type]
            thesis_id=int(m.group("thesis_id")),
            reason=m.group("reason").strip(),
        )
    m = _DISPOSE_RE.match(line)
    if m is None:
        raise CommandSyntaxError(
            "expected `DISPOSE <packet_id> <verdict> [note]` with a `dpk-…` packet id"
        )
    verdict = m.group("verdict").lower()
    if verdict not in _VERDICTS:
        raise CommandSyntaxError(
            f"unknown verdict {verdict!r}; one of {', '.join(sorted(_VERDICTS))}"
        )
    note = m.group("note")
    return DisposeCommand(
        packet_id=m.group("packet_id"),
        verdict=verdict,  # type: ignore[arg-type]
        note=note.strip() if note else None,
    )


@dataclass(frozen=True)
class PendingCommand:
    comment: IssueComment
    command: Command | None
    error: str | None

    @property
    def summary(self) -> str:
        if self.command is not None:
            return self.command.summary
        return _first_line(self.comment.body)[:80]


def select_commands(comments: list[IssueComment], *, owner_login: str) -> list[PendingCommand]:
    """Owner-authored command comments with no marker reply yet, in id order.

    A comment by any other login is data. A comment that is itself a marker
    reply is skipped. A command whose marker (applied or refused) already
    exists on the issue is terminal and never re-read — the job's idempotency
    across daily runs rests on this, not on the database.
    """
    answered = {m.comment_id for c in comments if (m := parse_marker(c.body)) is not None}
    out: list[PendingCommand] = []
    for c in sorted(comments, key=lambda c: c.comment_id):
        if c.author_login.lower() != owner_login.lower():
            continue
        if parse_marker(c.body) is not None or c.comment_id in answered:
            continue
        try:
            command = parse_command(c.body)
        except CommandSyntaxError as exc:
            out.append(PendingCommand(comment=c, command=None, error=str(exc)))
            continue
        if command is None:
            continue
        out.append(PendingCommand(comment=c, command=command, error=None))
    return out
