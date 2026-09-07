"""Canonical product Finding contract for the closed-loop control plane.

This module is pure and credential-free. Product probes call :func:`build_finding`
to produce a closed-schema artifact; Sentinel and Intake later parse the same
artifact and recompute its fingerprint and actionability decision. Run metadata
is evidence, never identity.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from asxos.redaction import redact_secrets

FINDING_SCHEMA_VERSION: Final = 1
MAX_LOG_EXCERPT_CHARS: Final = 2_000

_SLUG_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_IDENTIFIER_KEY_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_RUN_URL_RE: Final = re.compile(
    r"^https://github\.com/Jp8617465-sys/asxos/actions/runs/[1-9][0-9]*$"
)
_SHA256_RE: Final = re.compile(r"^sha256:[0-9a-f]{64}$")
_PYTEST_NODE_RE: Final = re.compile(
    r"^tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py::"
    r"(?:Test[A-Za-z0-9_]*::)?test_[A-Za-z0-9_]+(?:\[[^\]\r\n]{1,128}\])?$"
)
_CHECK_IDENTITY_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "lint_failure": re.compile(r"^ruff:[A-Z][0-9]{3,4}$"),
    "type_check_failure": re.compile(r"^mypy:[a-z][a-z0-9-]{0,63}$"),
    "code_invariant_failure": re.compile(r"^invariant:[a-z][a-z0-9_-]{0,63}$"),
}

_ACTIONABLE_FAILURE_IDENTIFIERS: Final[dict[str, str]] = {
    "unit_test_failure": "test_id",
    "lint_failure": "check_id",
    "type_check_failure": "check_id",
    "code_invariant_failure": "invariant_id",
}

# A Finding may point at these paths for diagnosis, but a worker must never be
# admitted to repair them. Item 5 will place the complete verifier manifest
# around this classifier and make changes to the classifier itself V9-denied.
_PROTECTED_EXACT_PATHS: Final = frozenset({"AGENTS.md", "CLAUDE.md", ".mcp.json"})
_PROTECTED_PREFIXES: Final = (
    ".claude/",
    ".github/",
    "asxos/control_plane/",
    "docs/product/",
    "migrations/",
    "tests/",
)

type IdentifierValue = StrictStr | StrictInt | StrictBool | None
type Severity = Literal["L1", "L2", "L3"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActionabilityReason(StrEnum):
    """Stable reason codes emitted by the deterministic classifier."""

    ACTIONABLE_UNIT_TEST = "actionable_unit_test"
    ACTIONABLE_LINT = "actionable_lint"
    ACTIONABLE_TYPE_CHECK = "actionable_type_check"
    ACTIONABLE_CODE_INVARIANT = "actionable_code_invariant"
    DENY_FAILURE_CLASS = "deny_failure_class"
    DENY_MISSING_IDENTITY = "deny_missing_identity"
    DENY_INVALID_FILE_HINT = "deny_invalid_file_hint"
    DENY_NO_FILE_HINT = "deny_no_file_hint"
    DENY_PROTECTED_PATH = "deny_protected_path"
    DENY_NON_CODE_PATH = "deny_non_code_path"


class ActionabilityDecision(_FrozenModel):
    actionable: bool
    reason: ActionabilityReason


def _validate_canonical_value(value: object, *, location: str = "$") -> None:
    """Reject values with ambiguous or non-portable JSON representations."""

    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and unicodedata.normalize("NFC", value) != value:
            raise ValueError(f"{location} must use NFC-normalized Unicode")
        return
    if isinstance(value, float):
        raise ValueError(f"{location} must not contain a float")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{location} contains a non-string object key")
            _validate_canonical_value(key, location=f"{location}.<key>")
            _validate_canonical_value(child, location=f"{location}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_canonical_value(child, location=f"{location}[{index}]")
        return
    raise ValueError(f"{location} contains unsupported type {type(value).__name__}")


def canonical_json(value: object) -> str:
    """UTF-8 canonical JSON: sorted keys, no whitespace, and no floats."""

    _validate_canonical_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def finding_fingerprint(
    *,
    probe: str,
    failure_class: str,
    identifiers: Mapping[str, IdentifierValue],
) -> str | None:
    """Return the stable Finding identity, or ``None`` without stable identifiers."""

    if not identifiers:
        return None
    identity = {
        "probe": probe,
        "failure_class": failure_class,
        "identifiers": dict(identifiers),
    }
    digest = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _validate_repo_path(path: str) -> None:
    if not path or path != path.strip():
        raise ValueError("file hints must not be blank or padded")
    if path.startswith("/") or "\\" in path or "\n" in path or "\r" in path:
        raise ValueError(f"file hint must be a repository-relative POSIX path: {path!r}")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise ValueError(f"file hint must not contain empty, dot, or parent segments: {path!r}")
    if str(PurePosixPath(path)) != path:
        raise ValueError(f"file hint is not canonical: {path!r}")


def _is_protected_path(path: str) -> bool:
    return path in _PROTECTED_EXACT_PATHS or path.startswith(_PROTECTED_PREFIXES)


def _is_owned_code_path(path: str) -> bool:
    if path.startswith("asxos/") or path.startswith("jobs/"):
        return path.endswith(".py")
    return path.startswith("scripts/") and path.endswith(".py")


def classify_actionability(
    *,
    failure_class: str,
    identifiers: Mapping[str, IdentifierValue],
    file_hints: Sequence[str],
) -> ActionabilityDecision:
    """Classify whether a Finding can enter the code-repair lane.

    Only four explicitly allowlisted failure classes can return ``True``.
    Provider, data, migration, schema, configuration, timeout, and ambiguous
    failures therefore fall through to ``DENY_FAILURE_CLASS`` rather than
    relying on an expanding denylist.
    """

    required_identity = _ACTIONABLE_FAILURE_IDENTIFIERS.get(failure_class)
    if required_identity is None:
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_FAILURE_CLASS,
        )
    identity = identifiers.get(required_identity)
    if not isinstance(identity, str) or not identity.strip():
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_MISSING_IDENTITY,
        )
    if failure_class == "unit_test_failure" and not _PYTEST_NODE_RE.fullmatch(identity):
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_MISSING_IDENTITY,
        )
    identity_pattern = _CHECK_IDENTITY_PATTERNS.get(failure_class)
    if identity_pattern is not None and not identity_pattern.fullmatch(identity):
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_MISSING_IDENTITY,
        )
    if not file_hints:
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_NO_FILE_HINT,
        )
    try:
        for path in file_hints:
            _validate_repo_path(path)
    except ValueError:
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_INVALID_FILE_HINT,
        )
    if any(_is_protected_path(path) for path in file_hints):
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_PROTECTED_PATH,
        )
    if any(not _is_owned_code_path(path) for path in file_hints):
        return ActionabilityDecision(
            actionable=False,
            reason=ActionabilityReason.DENY_NON_CODE_PATH,
        )

    reason = {
        "unit_test_failure": ActionabilityReason.ACTIONABLE_UNIT_TEST,
        "lint_failure": ActionabilityReason.ACTIONABLE_LINT,
        "type_check_failure": ActionabilityReason.ACTIONABLE_TYPE_CHECK,
        "code_invariant_failure": ActionabilityReason.ACTIONABLE_CODE_INVARIANT,
    }[failure_class]
    return ActionabilityDecision(actionable=True, reason=reason)


class FindingEvidence(_FrozenModel):
    """Bounded, already-redacted evidence attached to one Finding."""

    run_url: str
    log_excerpt_sha256: str
    log_excerpt: str = Field(max_length=MAX_LOG_EXCERPT_CHARS)

    @field_validator("run_url")
    @classmethod
    def _run_url_is_product_actions_run(cls, value: str) -> str:
        if not _RUN_URL_RE.fullmatch(value):
            raise ValueError("run_url must identify a numeric asxos GitHub Actions run")
        return value

    @field_validator("log_excerpt_sha256")
    @classmethod
    def _digest_shape_is_pinned(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("log_excerpt_sha256 must be lowercase sha256:<64 hex>")
        return value

    @model_validator(mode="after")
    def _digest_matches_redacted_excerpt(self) -> FindingEvidence:
        expected = "sha256:" + hashlib.sha256(self.log_excerpt.encode("utf-8")).hexdigest()
        if self.log_excerpt_sha256 != expected:
            raise ValueError("log_excerpt_sha256 does not match log_excerpt")
        if redact_secrets(self.log_excerpt) != self.log_excerpt:
            raise ValueError("log_excerpt contains recognized credential material")
        return self


class Finding(_FrozenModel):
    """Closed schema shared by product probes, Sentinel, and Intake."""

    schema_version: Literal[1]
    probe: str = Field(min_length=1, max_length=64)
    failure_class: str = Field(min_length=1, max_length=64)
    fingerprint: str | None
    severity: Severity
    title: str = Field(min_length=1, max_length=200)
    identifiers: dict[str, IdentifierValue] = Field(max_length=32)
    evidence: FindingEvidence
    actionable_in_code: bool
    file_hints: tuple[str, ...] = Field(max_length=20)
    observed_at: AwareDatetime

    @field_validator("probe", "failure_class")
    @classmethod
    def _slug_fields_are_canonical(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("must be a lowercase snake_case identifier")
        return value

    @field_validator("fingerprint")
    @classmethod
    def _fingerprint_shape_is_pinned(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError("fingerprint must be lowercase sha256:<64 hex> or null")
        return value

    @field_validator("title")
    @classmethod
    def _title_is_one_canonical_line(cls, value: str) -> str:
        if value != value.strip() or "\n" in value or "\r" in value:
            raise ValueError("title must be one unpadded line")
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("title must use NFC-normalized Unicode")
        return value

    @field_validator("identifiers")
    @classmethod
    def _identifiers_are_canonical(
        cls, value: dict[str, IdentifierValue]
    ) -> dict[str, IdentifierValue]:
        for key, item in value.items():
            if not _IDENTIFIER_KEY_RE.fullmatch(key):
                raise ValueError(f"identifier key is not canonical: {key!r}")
            if isinstance(item, str):
                if not item or item != item.strip() or len(item) > 256:
                    raise ValueError(f"identifier {key!r} must be 1-256 unpadded characters")
                if unicodedata.normalize("NFC", item) != item:
                    raise ValueError(f"identifier {key!r} must use NFC-normalized Unicode")
            elif isinstance(item, int) and not isinstance(item, bool) and abs(item) > 2**63 - 1:
                raise ValueError(f"identifier {key!r} is outside the signed 64-bit range")
        return value

    @field_validator("file_hints")
    @classmethod
    def _file_hints_are_canonical(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("file_hints must be sorted and unique")
        for path in value:
            _validate_repo_path(path)
        return value

    @model_validator(mode="after")
    def _derived_fields_recompute_exactly(self) -> Finding:
        expected_fingerprint = finding_fingerprint(
            probe=self.probe,
            failure_class=self.failure_class,
            identifiers=self.identifiers,
        )
        if self.fingerprint != expected_fingerprint:
            raise ValueError("fingerprint does not match the canonical Finding identity")
        decision = classify_actionability(
            failure_class=self.failure_class,
            identifiers=self.identifiers,
            file_hints=self.file_hints,
        )
        if self.actionable_in_code != decision.actionable:
            raise ValueError("actionable_in_code does not match the deterministic classifier")

        textual_values = [
            self.probe,
            self.failure_class,
            self.title,
            self.evidence.run_url,
            self.evidence.log_excerpt,
            *self.file_hints,
            *(item for item in self.identifiers.values() if isinstance(item, str)),
        ]
        if any(redact_secrets(value) != value for value in textual_values):
            raise ValueError("Finding contains recognized credential material")
        return self

    def canonical_json(self) -> str:
        """Serialize the complete record deterministically for JSONL transport."""

        # ``frozen=True`` prevents field reassignment but Pydantic dictionaries
        # remain mutable. Revalidation here makes an in-process mutation fail
        # before it can cross the artifact boundary.
        payload = self.model_dump(mode="json")
        validated = Finding.model_validate(payload)
        return canonical_json(validated.model_dump(mode="json"))


def parse_finding_json(line: str) -> Finding:
    """Parse exactly one canonical JSONL record and reject alternate encodings."""

    candidate = line.removesuffix("\n")
    if not candidate or "\n" in candidate or "\r" in candidate:
        raise ValueError("expected exactly one canonical Finding JSONL record")
    finding = Finding.model_validate_json(candidate)
    if finding.canonical_json() != candidate:
        raise ValueError("Finding JSON is valid but not canonical")
    return finding


def build_finding(
    *,
    probe: str,
    failure_class: str,
    severity: Severity,
    title: str,
    identifiers: Mapping[str, IdentifierValue],
    run_url: str,
    log_excerpt: str,
    file_hints: Sequence[str],
    observed_at: datetime,
) -> Finding:
    """Build a Finding while deriving every security-sensitive field."""

    redacted_excerpt = redact_secrets(log_excerpt)[:MAX_LOG_EXCERPT_CHARS]
    excerpt_digest = "sha256:" + hashlib.sha256(
        redacted_excerpt.encode("utf-8")
    ).hexdigest()
    sorted_hints = tuple(sorted(set(file_hints)))
    identity = dict(identifiers)
    decision = classify_actionability(
        failure_class=failure_class,
        identifiers=identity,
        file_hints=sorted_hints,
    )
    if observed_at.tzinfo is not None:
        observed_at = observed_at.astimezone(UTC)
    return Finding(
        schema_version=FINDING_SCHEMA_VERSION,
        probe=probe,
        failure_class=failure_class,
        fingerprint=finding_fingerprint(
            probe=probe,
            failure_class=failure_class,
            identifiers=identity,
        ),
        severity=severity,
        title=title,
        identifiers=identity,
        evidence=FindingEvidence(
            run_url=run_url,
            log_excerpt_sha256=excerpt_digest,
            log_excerpt=redacted_excerpt,
        ),
        actionable_in_code=decision.actionable,
        file_hints=sorted_hints,
        observed_at=observed_at,
    )
