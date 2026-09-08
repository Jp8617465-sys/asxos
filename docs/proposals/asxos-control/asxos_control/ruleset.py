"""Evaluate a ruleset specification without mutating GitHub."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Action = Literal[
    "direct_push",
    "force_push",
    "admin_bypass",
    "stale_check",
    "non_squash_merge",
    "squash_merge_with_required_checks",
]

_DEFAULT = Path(__file__).resolve().parents[1] / "fixtures" / "ruleset-spec.json"


@dataclass(frozen=True)
class RulesetSpec:
    required_pull_request: bool
    allowed_merge_methods: tuple[str, ...]
    linear_history: bool
    allow_force_push: bool
    allow_deletions: bool
    bypass_actors: tuple[str, ...]
    required_checks: tuple[dict[str, object], ...]
    strict_required_status_checks: bool
    require_code_owner_review: bool
    required_approving_review_count: int
    require_last_push_approval: bool

    @classmethod
    def load(cls, path: Path | None = None) -> RulesetSpec:
        raw = json.loads((path or _DEFAULT).read_text(encoding="utf-8"))
        return cls(
            required_pull_request=bool(raw["required_pull_request"]),
            allowed_merge_methods=tuple(raw["allowed_merge_methods"]),
            linear_history=bool(raw["linear_history"]),
            allow_force_push=bool(raw["allow_force_push"]),
            allow_deletions=bool(raw["allow_deletions"]),
            bypass_actors=tuple(raw["bypass_actors"]),
            required_checks=tuple(raw["required_checks"]),
            strict_required_status_checks=bool(raw["strict_required_status_checks"]),
            require_code_owner_review=bool(raw["require_code_owner_review"]),
            required_approving_review_count=int(raw["required_approving_review_count"]),
            require_last_push_approval=bool(raw["require_last_push_approval"]),
        )


def spec_errors(spec: RulesetSpec) -> list[str]:
    errors: list[str] = []
    if not spec.required_pull_request:
        errors.append("pull_request_not_required")
    if spec.allowed_merge_methods != ("squash",):
        errors.append("not_squash_only")
    if not spec.linear_history:
        errors.append("linear_history_disabled")
    if spec.allow_force_push:
        errors.append("force_push_allowed")
    if spec.allow_deletions:
        errors.append("deletions_allowed")
    if spec.bypass_actors:
        errors.append("bypass_list_not_empty")
    if not spec.strict_required_status_checks:
        errors.append("required_checks_not_strict")
    if spec.require_code_owner_review:
        errors.append("global_codeowner_review_would_block_green")
    if spec.required_approving_review_count != 0:
        errors.append("global_approval_count_would_block_green")
    if spec.require_last_push_approval:
        errors.append("last_push_approval_would_block_green")
    names = [str(item.get("context")) for item in spec.required_checks]
    if "full-check" not in names:
        errors.append("missing_full_check")
    if "risk-classify" not in names:
        errors.append("missing_risk_classify")
    risk = next((item for item in spec.required_checks if item.get("context") == "risk-classify"), None)
    if risk is not None and not risk.get("app_slug"):
        errors.append("risk_classify_not_app_bound")
    return errors


def action_allowed(spec: RulesetSpec, action: Action) -> bool:
    if spec_errors(spec):
        if action != "squash_merge_with_required_checks":
            return False
    if action == "direct_push":
        return not spec.required_pull_request
    if action == "force_push":
        return spec.allow_force_push
    if action == "admin_bypass":
        return bool(spec.bypass_actors)
    if action == "stale_check":
        return not spec.strict_required_status_checks
    if action == "non_squash_merge":
        return any(method != "squash" for method in spec.allowed_merge_methods)
    if action == "squash_merge_with_required_checks":
        return not spec_errors(spec) and spec.allowed_merge_methods == ("squash",)
    return False
