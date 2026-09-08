"""Credential-free observation of one pull request head.

The verifier never fetches with a write token. A caller supplies already-read
evidence; missing or malformed evidence fails closed in ``classify``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RefKind = Literal["head", "merge", "other"]


@dataclass(frozen=True)
class Review:
    """One effective review (latest per user) on the observed PR."""

    user_login: str
    state: str
    commit_id: str
    submitted_at: str
    dismissed: bool = False


@dataclass(frozen=True)
class LedgerAC:
    """Content-addressed acceptance criteria recorded in the control ledger."""

    digest: str
    frozen: bool
    explicit_yes: bool
    owner_comment: str | None = None


@dataclass(frozen=True)
class Observation:
    """Complete observation required to classify one PR head.

    ``paths_complete`` must be True. A truncated GitHub files list is refused.
    """

    product_repo: str
    pr_number: int
    head_sha: str
    check_sha: str
    ref_kind: RefKind
    changed_paths: tuple[str, ...]
    paths_complete: bool
    reviews: tuple[Review, ...]
    codeowners_text: str
    agents_md_bytes: bytes
    claimed_agents_md_digest: str
    verifier_ref: str
    publisher_app_slug: str
    expected_publisher_app_slug: str
    james_login: str
    labels: tuple[str, ...] = ()
    ledger_ac: LedgerAC | None = None
    pure_relocation: bool = False
    actor_login: str = ""
