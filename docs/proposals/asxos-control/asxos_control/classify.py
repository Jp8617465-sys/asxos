"""Deterministic Green/Amber/Red classification. No GitHub write side effects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from asxos_control.hashes import is_git_sha, is_sha256, sha256_hex
from asxos_control.observation import Observation
from asxos_control.registry import PathRegistry, highest_tier, touches_investment_output

PRODUCT_REPO = "Jp8617465-sys/asxos"
CHECK_NAME = "risk-classify"
Conclusion = Literal["success", "failure"]
Tier = Literal["green", "amber", "red"]


@dataclass(frozen=True)
class ClassifyResult:
    ok: bool
    conclusion: Conclusion
    reason: str
    head_sha: str
    tier: Tier | None
    check_name: str = CHECK_NAME

    def as_check(self) -> dict[str, str]:
        """Binary Checks API payload. Never skipped or neutral."""
        return {
            "name": self.check_name,
            "head_sha": self.head_sha,
            "conclusion": self.conclusion,
        }


def _fail(obs: Observation, reason: str, *, tier: Tier | None = None) -> ClassifyResult:
    return ClassifyResult(
        ok=False,
        conclusion="failure",
        reason=reason,
        head_sha=obs.head_sha if is_git_sha(obs.head_sha) else "",
        tier=tier,
    )


def _pass(obs: Observation, reason: str, tier: Tier) -> ClassifyResult:
    return ClassifyResult(
        ok=True,
        conclusion="success",
        reason=reason,
        head_sha=obs.head_sha,
        tier=tier,
    )


def _james_current_head_approval(obs: Observation) -> bool:
    matching = [
        review
        for review in obs.reviews
        if review.user_login == obs.james_login
        and not review.dismissed
        and review.state == "APPROVED"
        and review.commit_id == obs.head_sha
    ]
    return bool(matching)


def _explicit_yes_holds(obs: Observation) -> bool:
    ac = obs.ledger_ac
    if ac is None or not ac.frozen or not ac.explicit_yes:
        return False
    if not is_sha256(ac.digest):
        return False
    expected = f"APPROVE-AC sha256:{ac.digest}"
    return ac.owner_comment == expected


def classify(obs: Observation, registry: PathRegistry | None = None) -> ClassifyResult:
    """Fail closed on incomplete, stale, merge-ref, or identity-mismatched evidence."""
    reg = registry or PathRegistry.load()

    if obs.product_repo != PRODUCT_REPO:
        return _fail(obs, "wrong_repository")
    if not isinstance(obs.pr_number, int) or obs.pr_number <= 0:
        return _fail(obs, "malformed_pr_number")
    if not is_git_sha(obs.head_sha):
        return _fail(obs, "malformed_head_sha")
    if not is_git_sha(obs.check_sha):
        return _fail(obs, "malformed_check_sha")
    if obs.check_sha != obs.head_sha:
        return _fail(obs, "stale_or_non_head_sha")
    if obs.ref_kind != "head":
        return _fail(obs, "merge_or_non_head_ref")
    if not is_git_sha(obs.verifier_ref):
        return _fail(obs, "mutable_verifier_ref")
    if not obs.paths_complete:
        return _fail(obs, "incomplete_changed_paths")
    if not obs.codeowners_text.strip():
        return _fail(obs, "missing_codeowners")
    if not obs.agents_md_bytes:
        return _fail(obs, "missing_agents_md")
    actual_digest = sha256_hex(obs.agents_md_bytes)
    if not is_sha256(obs.claimed_agents_md_digest):
        return _fail(obs, "malformed_agents_md_digest")
    if obs.claimed_agents_md_digest != actual_digest:
        return _fail(obs, "agents_md_digest_mismatch")
    if not obs.james_login:
        return _fail(obs, "missing_james_login")
    if obs.publisher_app_slug != obs.expected_publisher_app_slug:
        return _fail(obs, "publisher_identity_mismatch")
    if not obs.publisher_app_slug:
        return _fail(obs, "missing_publisher_identity")
    if "relocation" in obs.labels and not obs.pure_relocation:
        return _fail(obs, "relocation_not_pure_move")

    tier = highest_tier(obs.changed_paths, reg)
    if tier == "red":
        return _fail(obs, "red_path_never_passes", tier="red")

    if touches_investment_output(obs.changed_paths, reg):
        if not _explicit_yes_holds(obs):
            return _fail(obs, "investment_output_needs_digest_bound_approval", tier="amber")
        if not _james_current_head_approval(obs):
            return _fail(obs, "amber_needs_current_head_approval", tier="amber")
        return _pass(obs, "amber_investment_output_approved", "amber")

    if tier == "green":
        return _pass(obs, "green_allowlist", "green")

    if not _james_current_head_approval(obs):
        return _fail(obs, "amber_needs_current_head_approval", tier="amber")
    return _pass(obs, "amber_current_head_approved", "amber")
