"""Provenance resolvers for Layer 1 — does an arbi-authored issue's citation point at
something real in the checkout of ``main``?

Six forms, each answering "where did this work come from" with something a reviewer can
open (AGENTS.md §7: every figure traces to a probe or a doc line):

    run:<id>                    a failing workflow run — the loop fixing what it saw break
    decision-log:<YYYY-MM-DD>   a row in docs/product/decision-log.md
    backlog:<A-E>-<n>           an id in docs/product/backlog.yaml (the archived queue)
    roadmap:<id>                a queue item named in docs/product/roadmap-state.md
    doc:<docs/product|proposals/…md>#<heading-slug>
                                a section of a merged plan or proposal
    issue:#<n>                  a parent issue opened by the owner

The first two are what rev 2 allowed. The other four are what let the loop build the
roadmap rather than only react to breakage — AGENTS.md §0 says arbi names the
highest-leverage thing and does it; a provenance rule that only accepts incidents would
have made that impossible.

Reads files only. The parent-issue check is a callback so this module never reaches the
network itself.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from asxos.backlog import load as load_backlog
from asxos.domain.governance.issue_eligibility import ProvenanceRef

DECISION_LOG: Final[str] = "docs/product/decision-log.md"
BACKLOG: Final[str] = "docs/product/backlog.yaml"
ROADMAP: Final[str] = "docs/product/roadmap-state.md"
DOC_ROOTS: Final[tuple[str, ...]] = ("docs/product/", "docs/proposals/")

_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEADING_RE: Final[re.Pattern[str]] = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*$")


def heading_slug(text: str) -> str:
    """GitHub's anchor for a Markdown heading: lower-case, punctuation dropped, spaces → ``-``."""
    text = re.sub(r"`|\*|_", "", text.strip().lower())
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text).strip("-")


@dataclass(frozen=True)
class RepoProvenance:
    """Resolve a :class:`ProvenanceRef` against one checkout.

    ``owner_login`` is the repository owner (from the repository record);
    ``parent_author`` returns the login that opened a given issue, or None if it
    cannot be read — the ``issue:`` form resolves only when that login is the owner.
    """

    root: Path
    owner_login: str
    parent_author: Callable[[int], str | None] | None = None

    def resolve(self, ref: ProvenanceRef) -> bool:
        return {
            "run": self._run,
            "decision-log": self._decision_log,
            "backlog": self._backlog,
            "roadmap": self._roadmap,
            "doc": self._doc,
            "issue": self._issue,
        }[ref.kind](ref.value)

    # --- the six forms ----------------------------------------------------------------------

    @staticmethod
    def _run(value: str) -> bool:
        return value.isdigit()

    def _decision_log(self, value: str) -> bool:
        if not _DATE_RE.match(value):
            return False
        path = self.root / DECISION_LOG
        if not path.is_file():
            return False
        prefix = f"| {value} |"
        return any(
            line.startswith(prefix) for line in path.read_text(encoding="utf-8").splitlines()
        )

    def _backlog(self, value: str) -> bool:
        path = self.root / BACKLOG
        if not path.is_file():
            return False
        return any(item.id == value for item in load_backlog(path))

    def _roadmap(self, value: str) -> bool:
        path = self.root / ROADMAP
        if not path.is_file() or not value:
            return False
        return (
            re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", path.read_text(encoding="utf-8"))
            is not None
        )

    def _doc(self, value: str) -> bool:
        rel, _, fragment = value.partition("#")
        if not rel.startswith(DOC_ROOTS) or ".." in rel.split("/") or not rel.endswith(".md"):
            return False
        path = self.root / rel
        if not path.is_file():
            return False
        if not fragment:
            return True
        for line in path.read_text(encoding="utf-8").splitlines():
            m = _HEADING_RE.match(line)
            if m and heading_slug(m.group("text")) == fragment:
                return True
        return False

    def _issue(self, value: str) -> bool:
        number = value.lstrip("#")
        if not number.isdigit() or self.parent_author is None:
            return False
        author = self.parent_author(int(number))
        return author is not None and author.lower() == self.owner_login.lower()
