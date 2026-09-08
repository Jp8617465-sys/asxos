"""Publisher contract. This module is the only write-shaped interface.

The verifier must not import it. The publisher identity posts only the binary
result against the exact PR head SHA. No other GitHub write is expressed here.
"""

from __future__ import annotations

from dataclasses import dataclass

from asxos_control.classify import CHECK_NAME, ClassifyResult
from asxos_control.hashes import is_git_sha

ALLOWED_CONCLUSIONS = frozenset({"success", "failure"})


@dataclass(frozen=True)
class CheckPost:
    name: str
    head_sha: str
    conclusion: str
    repo: str


class PublishError(ValueError):
    """Refuse to emit a Checks API post."""


def prepare_check_post(
    result: ClassifyResult,
    *,
    repo: str,
    requested_sha: str,
    publisher_app_slug: str,
    expected_publisher_app_slug: str,
) -> CheckPost:
    if publisher_app_slug != expected_publisher_app_slug:
        raise PublishError("wrong_app")
    if not is_git_sha(requested_sha) or requested_sha != result.head_sha:
        raise PublishError("exact_head_mismatch")
    if result.conclusion not in ALLOWED_CONCLUSIONS:
        raise PublishError("skipped_or_neutral_forbidden")
    payload = result.as_check()
    if payload["name"] != CHECK_NAME:
        raise PublishError("wrong_check_name")
    if payload["conclusion"] not in ALLOWED_CONCLUSIONS:
        raise PublishError("skipped_or_neutral_forbidden")
    return CheckPost(
        name=payload["name"],
        head_sha=payload["head_sha"],
        conclusion=payload["conclusion"],
        repo=repo,
    )
