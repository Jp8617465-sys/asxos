"""Reproducible drill predicates. They do not mutate production."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanaryRevision:
    before_sha: str
    canary_sha: str
    after_revert_sha: str


def canary_revert_restored(revisions: CanaryRevision) -> bool:
    return (
        revisions.before_sha != revisions.canary_sha
        and revisions.after_revert_sha == revisions.before_sha
    )


def negative_observation_reasons() -> tuple[str, ...]:
    return (
        "wrong_repository",
        "merge_or_non_head_ref",
        "agents_md_digest_mismatch",
        "amber_needs_current_head_approval",
        "publisher_identity_mismatch",
        "missing_telemetry",
    )
