#!/usr/bin/env python3
"""Validate the ASXOS investment-engine implementation dossier.

The validator deliberately uses only the Python standard library.  It checks the
JSON-compatible roadmap, the JSON Schema subset used by this dossier, contract
fixtures, dependency/link integrity, release-gate constants, and the generated
roadmap view.  It does not import product code or contact live services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "docs/programs/investment-engine"
SCHEMA_DIR = PROGRAM / "schemas"
FIXTURE_DIR = PROGRAM / "fixtures"
ROADMAP_PATH = ROOT / "docs/product/roadmap.yaml"
ROADMAP_VIEW_PATH = ROOT / "docs/product/investment-engine-roadmap.md"
ROADMAP_SCHEMA_PATH = SCHEMA_DIR / "roadmap.schema.json"
MISSION_TEMPLATE_PATH = PROGRAM / "mission-template.yaml"
SPRINT_COMMAND_PATH = ROOT / ".claude/commands/investment-engine-sprint.md"
MODEL_A_DECOMMISSION_PATH = PROGRAM / "model-a-decommission.md"
TAILORED_OUTPUT_AUTHORITY_DOCUMENTS = (
    "CLAUDE.md",
    "docs/product/north-star.md",
    "docs/product/portfolio-manager-charter.md",
    "docs/product/portfolio-policy.md",
    "docs/product/recommendation-schema.md",
    "docs/product/arbi-permission-model.md",
    ".claude/rules/portfolio-conventions.md",
)
MODEL_A_FAIL_CLOSED_TOKEN = "MODEL_A_DECOMMISSIONED"
MODEL_A_M02_RECORD_PATHS = (
    "docs/programs/investment-engine/missions/S01/M02/mission.yaml",
    "docs/programs/investment-engine/missions/S01/M02/model-a-inventory.json",
    "docs/programs/investment-engine/missions/S01/M02/model-a-archive-manifest.json",
    "docs/programs/investment-engine/missions/S01/M02/model-a-restore-evidence.json",
    "docs/programs/investment-engine/missions/S01/M02/model-a-approval.md",
    "docs/programs/investment-engine/missions/S01/M02/close.md",
)
REVIEW_ROLES = {
    "evidence_claims",
    "valuation_scenarios",
    "thesis_adversary",
    "portfolio_risk_fit",
    "implementation_liquidity_tax",
}
REVIEW_MODEL_REF = {
    "id": "review-model-001",
    "version": "1.0.0",
    "sha256": "b0" * 32,
}
REVIEW_RUBRIC_REF = {
    "id": "review-rubric-main",
    "version": "1.0.0",
    "sha256": "c0" * 32,
}
REVIEW_ROLE_IDENTITY_SPECS = {
    "evidence_claims": (
        "blind-evidence-reviewer",
        "a1" * 32,
        "review-prompt-evidence",
        "b1" * 32,
    ),
    "valuation_scenarios": (
        "blind-valuation-reviewer",
        "a2" * 32,
        "review-prompt-valuation",
        "b2" * 32,
    ),
    "thesis_adversary": (
        "blind-adversarial-reviewer",
        "a3" * 32,
        "review-prompt-adversary",
        "b3" * 32,
    ),
    "portfolio_risk_fit": (
        "blind-risk-reviewer",
        "a4" * 32,
        "review-prompt-risk",
        "b4" * 32,
    ),
    "implementation_liquidity_tax": (
        "blind-implementation-reviewer",
        "a5" * 32,
        "review-prompt-implementation",
        "b5" * 32,
    ),
}
REVIEW_FRESHNESS_SOURCE_TYPES = {
    "market_price": "market_data",
    "company_filing": "company_filing",
}
GOLDEN_REVIEW_RESOLUTIONS = {
    "41000000-0000-4000-8000-000000000001": {
        "code": "SCENARIO_ROUNDING",
        "severity": "low",
        "status": "RESOLVED",
        "claim_ids": ["CLM-002"],
        "evidence_ids": [900001],
        "resolution_ref": {
            "resolution_id": "resolution-valuation-001",
            "resolution_type": "RESOLVED",
            "resolved_by": "James",
            "resolved_at": "2026-07-24T01:05:00Z",
            "resolution_sha256": "ab" * 32,
        },
    }
}
CAPITAL_SCHEMA_EXCLUSIONS = {"roadmap.schema.json"}
MODEL_A_BOUNDARY_TOKENS = {
    "allocator_score",
    "expected_return",
    "model_a",
    "prob_up",
    "shap",
    "signal_label",
    "signal_rank",
}
MODEL_A_NEGATIVE_CONTROL_SCHEMAS = {
    "evaluation-policy-v1.schema.json",
    "evaluator-config-v1.schema.json",
}
MODEL_A_ARCHIVE_EVIDENCE_SCHEMAS = {
    "model-a-archive-manifest-v1.schema.json",
    "model-a-archive-restore-evidence-v1.schema.json",
}
MODEL_A_ARCHIVE_EVIDENCE_CONTRACTS = {
    "model-a-archive-manifest-v1",
    "model-a-archive-restore-evidence-v1",
}
FORBIDDEN_CAPITAL_TOKENS = {
    "auth_token",
    "authentication",
    "authorization",
    "broker_api",
    "broker_account",
    "broker_client",
    "broker_connection",
    "broker_credential",
    "broker_endpoint",
    "broker_route",
    "broker_session",
    "broker_token",
    "cancel_order",
    "execute_order",
    "external_order_id",
    "model_a",
    "modify_order",
    "multi_user",
    "order_route",
    "place_order",
    "shap",
    "prob_up",
    "expected_return",
    "rls",
    "route_order",
    "submit_order",
    "signal_label",
    "signal_rank",
    "allocator_score",
    "tenant_id",
    "tenancy",
    "user_id",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
UTC_DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_SAFE_JSON_INTEGER = (1 << 53) - 1
ARTIFACT_ID_FIELDS = {
    "accounting-policy-v1": "accounting_policy_id",
    "benchmark-policy-v1": "benchmark_policy_id",
    "benchmark-snapshot-v1": "benchmark_snapshot_id",
    "branch-ledger-v1": "ledger_id",
    "branch-nav-v1": "nav_artifact_id",
    "broker-report-v1": "report_version_id",
    "cohort-statistics-v1": "statistics_id",
    "dependency-isolation-evidence-v1": "evidence_id",
    "episode-outcome-v1": "outcome_id",
    "evaluation-origin-v1": "origin_id",
    "evaluation-policy-v1": "policy_id",
    "evaluator-config-v1": "config_id",
    "fill-model-v1": "fill_model_id",
    "model-a-archive-manifest-v1": "archive_id",
    "model-a-archive-restore-evidence-v1": "restore_evidence_id",
    "paper-evaluator-v1": "evaluation_id",
    "paper-fill-v1": "paper_fill_id",
    "paper-intent-v1": "intent_id",
    "paper-order-v1": "paper_order_id",
    "portfolio-construction-policy-v1": "policy_id",
    "portfolio-proposal-v1": "proposal_id",
    "portfolio-snapshot-v1": "portfolio_snapshot_id",
    "promotion-decision-v1": "promotion_decision_id",
    "review-context-v1": "context_id",
    "review-eligibility-v1": "eligibility_decision_id",
    "reviewer-assessment-v1": "assessment_id",
    "risk-policy-v1": "policy_id",
    "security-classification-snapshot-v1": "classification_snapshot_id",
    "sizing-decision-v1": "sizing_decision_id",
    "sizing-policy-v1": "sizing_policy_id",
    "staged-order-set-v1": "order_set_id",
    "staging-policy-v1": "policy_id",
    "tax-profile-v1": "tax_profile_id",
    "trading-calendar-v1": "calendar_id",
}
REFERENCE_DIGEST_KEYS = {
    "eligibility_decision_id": "eligibility_sha256",
}
REFERENCE_CONTRACT_NAMES = {
    "eligibility_decision_id": "review-eligibility-v1",
}
CONSTRUCTION_CAP_ORDER = (
    "ELIGIBILITY",
    "CLASSIFICATION",
    "STOP_RISK",
    "ISSUER",
    "CORPORATE_GROUP",
    "SINGLE_NAME",
    "SECTOR",
    "THEME",
    "PORTFOLIO_LOSS_AT_STOP",
    "GROSS_EXPOSURE",
    "NET_EXPOSURE",
    "CASH_RESERVE",
    "TURNOVER",
    "RESERVATIONS",
    "LIQUIDITY_ADV_SPREAD",
    "TAX",
    "MINIMUM_TARGET",
)
SIZING_CONSTRAINT_ORDER = (
    "CLASSIFICATION",
    "TARGET_NOTIONAL",
    "AVAILABLE_CASH",
    "ISSUER",
    "CORPORATE_GROUP",
    "SINGLE_NAME",
    "SECTOR",
    "THEME",
    "PORTFOLIO_LOSS_AT_STOP",
    "GROSS_EXPOSURE",
    "NET_EXPOSURE",
    "RESERVATIONS",
    "TURNOVER",
    "ADV_PARTICIPATION",
    "SPREAD",
    "LOSS_HEADROOM",
    "TICK_RULE",
    "BOARD_LOT",
    "MINIMUM_ORDER",
    "FEES",
)

# Normative comparison direction per numeric constraint code. NUMERIC_LIMIT
# carries three distinct directions plus an applied-value cap, so a single
# universal rule cannot express it; see contracts/sizing-policy-v1.md.
SIZING_CONSTRAINT_COMPARISON = {
    "TARGET_NOTIONAL": "EXACT",
    "AVAILABLE_CASH": "CAP_APPLIED",
    "ISSUER": "MAXIMUM",
    "CORPORATE_GROUP": "MAXIMUM",
    "SINGLE_NAME": "MAXIMUM",
    "SECTOR": "MAXIMUM",
    "THEME": "MAXIMUM",
    "PORTFOLIO_LOSS_AT_STOP": "MAXIMUM",
    "GROSS_EXPOSURE": "MAXIMUM",
    "NET_EXPOSURE": "MAXIMUM",
    "RESERVATIONS": "MAXIMUM",
    "TURNOVER": "MAXIMUM",
    "ADV_PARTICIPATION": "MAXIMUM",
    "SPREAD": "MAXIMUM",
    "LOSS_HEADROOM": "MINIMUM",
    "BOARD_LOT": "MINIMUM",
    "MINIMUM_ORDER": "MINIMUM",
    "FEES": "MAXIMUM",
}

# Codes whose limit_value resolves directly from a ratified risk-policy field.
# ADV_PARTICIPATION, FEES, BOARD_LOT, AVAILABLE_CASH and TARGET_NOTIONAL are
# derived arithmetically at the call site. RESERVATIONS is the sole code with no
# ratified cap to resolve against: it is direction-asserted only, and
# contracts/sizing-policy-v1.md records that residue explicitly.
SIZING_LIMIT_FROM_RISK_POLICY = {
    "ISSUER": ("portfolio_limits", "max_issuer_weight"),
    "CORPORATE_GROUP": ("portfolio_limits", "max_corporate_group_weight"),
    "SINGLE_NAME": ("portfolio_limits", "max_single_name_weight"),
    "SECTOR": ("portfolio_limits", "max_sector_weight"),
    "THEME": ("portfolio_limits", "max_theme_weight"),
    "GROSS_EXPOSURE": ("portfolio_limits", "max_gross_weight"),
    "NET_EXPOSURE": ("portfolio_limits", "max_net_weight"),
    "TURNOVER": ("portfolio_limits", "max_daily_turnover_weight"),
    "PORTFOLIO_LOSS_AT_STOP": ("loss_limits", "max_portfolio_loss_at_stop_fraction"),
}

SIZING_LIMIT_FROM_SIZING_POLICY = {
    "SPREAD": "maximum_spread_fraction",
    "MINIMUM_ORDER": "minimum_order_aud",
    "LOSS_HEADROOM": "minimum_loss_headroom_aud",
}


class DossierError(ValueError):
    """One or more dossier invariants failed."""


def _assert_constraint_comparison(check: dict[str, Any], code: str, label: str) -> None:
    """Assert a numeric check honours its declared comparison direction.

    ``NUMERIC_LIMIT`` spans three directions plus an applied-value cap, so no
    single universal rule expresses it. The declared direction must match the
    normative registry in ``contracts/sizing-policy-v1.md``, and the check must
    honour it under both terminal actions.

    ``REDUCE`` does not exempt a check: a reduction is only valid if the
    post-reduction ``applied_value`` satisfies the limit. Treating ``REDUCE``
    as a skip would leave the direction assertion as no guard at all for the
    codes whose observed value is not independently recomputed.
    """
    expected = SIZING_CONSTRAINT_COMPARISON[code]
    declared = check.get("comparison")
    prefix = f"{label}.constraint_checks[{code}]"
    if declared != expected:
        raise DossierError(f"{prefix}.comparison: expected {expected}, found {declared!r}")
    action = check.get("action")
    observed = _decimal(check.get("observed_value"), f"{prefix}.observed_value")
    limit = _decimal(check.get("limit_value"), f"{prefix}.limit_value")
    applied = _decimal(check.get("applied_value"), f"{prefix}.applied_value")
    # A reduction must land inside the limit; the pre-reduction observation may
    # legitimately sit outside it. EXACT and CAP_APPLIED are identity/cap proofs
    # and are asserted on the same value under either action.
    if expected == "EXACT":
        satisfied = observed == limit
    elif expected == "CAP_APPLIED":
        satisfied = applied <= limit
    else:
        subject = applied if action == "REDUCE" else observed
        if expected == "MINIMUM":
            satisfied = subject >= limit
        elif expected == "MAXIMUM":
            satisfied = subject <= limit
        else:
            raise DossierError(f"{prefix}: unknown comparison direction {expected!r}")
    if not satisfied:
        raise DossierError(f"{prefix}: {action} violates its declared {expected} comparison")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DossierError(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _is_type(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, int | float) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "object":
        return isinstance(instance, dict)
    raise DossierError(f"unsupported JSON Schema type {expected!r}")


def _json_pointer(document: Any, fragment: str) -> Any:
    if fragment in {"", "#"}:
        return document
    pointer = fragment.removeprefix("#")
    if not pointer.startswith("/"):
        raise DossierError(f"unsupported JSON pointer fragment #{pointer}")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


@dataclass(frozen=True)
class SchemaDocument:
    path: Path
    body: dict[str, Any]


class SchemaStore:
    """Small Draft 2020-12 evaluator for the keywords used by this dossier."""

    def __init__(self, schema_dir: Path) -> None:
        self.by_path: dict[Path, SchemaDocument] = {}
        self.by_uri: dict[str, SchemaDocument] = {}
        for path in sorted(schema_dir.glob("*.json")):
            body = _load_json(path)
            if not isinstance(body, dict):
                raise DossierError(f"{path.relative_to(ROOT)}: schema root must be an object")
            document = SchemaDocument(path=path.resolve(), body=body)
            self.by_path[document.path] = document
            schema_id = body.get("$id")
            if isinstance(schema_id, str):
                self.by_uri[schema_id] = document

    def document(self, path: Path) -> SchemaDocument:
        try:
            return self.by_path[path.resolve()]
        except KeyError as exc:
            raise DossierError(f"schema not loaded: {path}") from exc

    def resolve(
        self, reference: str, current: SchemaDocument
    ) -> tuple[SchemaDocument, dict[str, Any]]:
        uri, separator, fragment = reference.partition("#")
        if not uri:
            target = current
        elif uri in self.by_uri:
            target = self.by_uri[uri]
        else:
            absolute_uri = urljoin(str(current.body.get("$id", "")), uri)
            if absolute_uri in self.by_uri:
                target = self.by_uri[absolute_uri]
            else:
                target_path = (current.path.parent / uri).resolve()
                try:
                    target = self.by_path[target_path]
                except KeyError as exc:
                    raise DossierError(
                        f"{current.path.relative_to(ROOT)}: unresolved $ref {reference!r}"
                    ) from exc
        resolved = _json_pointer(target.body, f"#{fragment}" if separator else "")
        if not isinstance(resolved, dict):
            raise DossierError(
                f"{current.path.relative_to(ROOT)}: $ref {reference!r} did not resolve to a schema"
            )
        return target, resolved

    def lint(self) -> None:
        for document in self.by_path.values():
            body = document.body
            relative = document.path.relative_to(ROOT)
            if body.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                raise DossierError(f"{relative}: must declare JSON Schema Draft 2020-12")
            if body.get("type") != "object":
                raise DossierError(f"{relative}: root type must be object")
            if body.get("additionalProperties") is not False:
                raise DossierError(f"{relative}: root must set additionalProperties=false")
            self._lint_node(body, document, "$")

    def _lint_node(self, node: Any, document: SchemaDocument, path: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(node):
                self._lint_node(item, document, f"{path}[{index}]")
            return
        if not isinstance(node, dict):
            return
        reference = node.get("$ref")
        if isinstance(reference, str):
            self.resolve(reference, document)
        pattern = node.get("pattern")
        if isinstance(pattern, str):
            try:
                re.compile(pattern)
            except re.error as exc:
                raise DossierError(
                    f"{document.path.relative_to(ROOT)}:{path}: invalid regex: {exc}"
                ) from exc
        for key, value in node.items():
            self._lint_node(value, document, f"{path}.{key}")

    def validate(self, instance: Any, schema_path: Path, label: str) -> None:
        document = self.document(schema_path)
        errors = self._errors(instance, document.body, document, "$")
        if errors:
            detail = "\n".join(f"  - {error}" for error in errors[:20])
            suffix = "" if len(errors) <= 20 else f"\n  - … {len(errors) - 20} more"
            raise DossierError(f"{label}: schema validation failed:\n{detail}{suffix}")

    def validate_fragment(
        self, instance: Any, schema_path: Path, fragment: str, label: str
    ) -> None:
        document = self.document(schema_path)
        schema = _json_pointer(document.body, fragment)
        if not isinstance(schema, dict):
            raise DossierError(f"{label}: invalid schema fragment {fragment}")
        errors = self._errors(instance, schema, document, "$")
        if errors:
            detail = "\n".join(f"  - {error}" for error in errors[:20])
            raise DossierError(f"{label}: schema validation failed:\n{detail}")

    def _matches(self, instance: Any, schema: dict[str, Any], document: SchemaDocument) -> bool:
        return not self._errors(instance, schema, document, "$probe")

    def _errors(
        self,
        instance: Any,
        schema: dict[str, Any],
        document: SchemaDocument,
        path: str,
    ) -> list[str]:
        errors: list[str] = []

        reference = schema.get("$ref")
        if isinstance(reference, str):
            target_document, target_schema = self.resolve(reference, document)
            errors.extend(self._errors(instance, target_schema, target_document, path))

        if "const" in schema and instance != schema["const"]:
            errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path}: {instance!r} is not in enum {schema['enum']!r}")

        expected_type = schema.get("type")
        if expected_type is not None:
            allowed = expected_type if isinstance(expected_type, list) else [expected_type]
            if not any(_is_type(instance, item) for item in allowed):
                errors.append(f"{path}: expected type {allowed!r}, got {type(instance).__name__}")
                return errors

        one_of = schema.get("oneOf")
        if isinstance(one_of, list):
            branch_results = [self._errors(instance, branch, document, path) for branch in one_of]
            matching = sum(not branch_errors for branch_errors in branch_results)
            if matching != 1:
                errors.append(f"{path}: oneOf matched {matching} branches, expected exactly one")
                if matching == 0 and branch_results:
                    errors.extend(min(branch_results, key=len)[:3])

        for branch in schema.get("allOf", []):
            errors.extend(self._errors(instance, branch, document, path))

        condition = schema.get("if")
        if isinstance(condition, dict):
            selected = (
                schema.get("then")
                if self._matches(instance, condition, document)
                else schema.get("else")
            )
            if isinstance(selected, dict):
                errors.extend(self._errors(instance, selected, document, path))

        if isinstance(instance, str):
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            if isinstance(min_length, int) and len(instance) < min_length:
                errors.append(f"{path}: string shorter than minLength {min_length}")
            if isinstance(max_length, int) and len(instance) > max_length:
                errors.append(f"{path}: string longer than maxLength {max_length}")
            pattern = schema.get("pattern")
            if isinstance(pattern, str) and re.search(pattern, instance) is None:
                errors.append(f"{path}: {instance!r} does not match {pattern!r}")
            format_name = schema.get("format")
            if isinstance(format_name, str):
                format_error = _format_error(instance, format_name)
                if format_error:
                    errors.append(f"{path}: {format_error}")

        if isinstance(instance, int | float) and not isinstance(instance, bool):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and instance < minimum:
                errors.append(f"{path}: {instance} is below minimum {minimum}")
            if maximum is not None and instance > maximum:
                errors.append(f"{path}: {instance} is above maximum {maximum}")

        if isinstance(instance, list):
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if isinstance(min_items, int) and len(instance) < min_items:
                errors.append(f"{path}: array has fewer than {min_items} items")
            if isinstance(max_items, int) and len(instance) > max_items:
                errors.append(f"{path}: array has more than {max_items} items")
            if schema.get("uniqueItems"):
                canonical_items = [_canonical(item) for item in instance]
                if len(canonical_items) != len(set(canonical_items)):
                    errors.append(f"{path}: array items are not unique")
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(instance):
                    errors.extend(self._errors(item, item_schema, document, f"{path}[{index}]"))
            contains = schema.get("contains")
            if isinstance(contains, dict):
                matches = sum(self._matches(item, contains, document) for item in instance)
                minimum_contains = schema.get("minContains", 1)
                maximum_contains = schema.get("maxContains")
                if matches < minimum_contains:
                    errors.append(f"{path}: contains matched {matches}, below {minimum_contains}")
                if isinstance(maximum_contains, int) and matches > maximum_contains:
                    errors.append(f"{path}: contains matched {matches}, above {maximum_contains}")

        if isinstance(instance, dict):
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    errors.append(f"{path}: missing required property {key!r}")
            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                for key, value in instance.items():
                    property_schema = properties.get(key)
                    if isinstance(property_schema, dict):
                        errors.extend(
                            self._errors(value, property_schema, document, f"{path}.{key}")
                        )
                    elif schema.get("additionalProperties") is False:
                        errors.append(f"{path}: unexpected property {key!r}")

        return errors


def _format_error(value: str, format_name: str) -> str | None:
    try:
        if format_name == "date":
            date.fromisoformat(value)
        elif format_name == "date-time":
            if UTC_DATE_TIME.fullmatch(value) is None:
                return (
                    f"{value!r} is not a UTC date-time "
                    "(required form: YYYY-MM-DDTHH:MM:SS[.ffffff]Z or +00:00)"
                )
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.utcoffset() != timedelta(0):
                return f"{value!r} is not a UTC date-time"
        elif format_name == "uuid":
            UUID(value)
        elif format_name == "uri":
            parsed = urlparse(value)
            if not parsed.scheme:
                return f"{value!r} is not an absolute URI"
    except ValueError:
        return f"{value!r} is not a valid {format_name}"
    return None


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def required_contract_names(roadmap: dict[str, Any]) -> tuple[str, ...]:
    """Return every roadmap-declared contract name, rejecting ambiguity."""
    names = tuple(contract["name"] for contract in roadmap["contracts"])
    if not names:
        raise DossierError("roadmap must declare at least one contract")
    duplicate = _duplicates(names)
    if duplicate:
        raise DossierError(f"roadmap contracts has duplicate names: {sorted(duplicate)}")
    return names


def _require_paths(paths: Iterable[str], context: str) -> None:
    for raw_path in paths:
        path = ROOT / raw_path
        if not path.exists():
            raise DossierError(f"{context}: missing repository path {raw_path}")


def _walk_values(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_values(child, f"{path}[{index}]")


def find_forbidden_capital_tokens(value: str) -> list[str]:
    """Return normalized deny tokens present in one capital-boundary string."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    matches: list[str] = []
    for token in FORBIDDEN_CAPITAL_TOKENS:
        if token == "rls":
            present = re.search(r"(?:^|_)rls(?:_|$)", normalized) is not None
        else:
            present = token in normalized
        if present:
            matches.append(token)
    return sorted(matches)


def _schema_forbidden_tokens(value: str, document_name: str) -> list[str]:
    matches = find_forbidden_capital_tokens(value)
    if document_name in MODEL_A_NEGATIVE_CONTROL_SCHEMAS:
        return [token for token in matches if token not in MODEL_A_BOUNDARY_TOKENS]
    if document_name in MODEL_A_ARCHIVE_EVIDENCE_SCHEMAS:
        return [token for token in matches if token != "model_a"]
    return matches


def _fixture_forbidden_tokens(value: str, contract_name: str) -> list[str]:
    matches = find_forbidden_capital_tokens(value)
    if contract_name in MODEL_A_ARCHIVE_EVIDENCE_CONTRACTS:
        return [token for token in matches if token != "model_a"]
    return matches


def _validate_model_a_negative_controls(document: SchemaDocument) -> None:
    def property_schemas(name: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for _, node in _walk_values(document.body):
            if not isinstance(node, dict):
                continue
            properties = node.get("properties")
            if isinstance(properties, dict) and isinstance(properties.get(name), dict):
                matches.append(properties[name])
        return matches

    if document.path.name == "evaluation-policy-v1.schema.json":
        permitted_fields = property_schemas("model_a_input_permitted")
        if permitted_fields and any(field.get("const") is not False for field in permitted_fields):
            raise DossierError(
                f"{document.path.relative_to(ROOT)}: " "model_a_input_permitted must be const false"
            )
    elif document.path.name == "evaluator-config-v1.schema.json":
        isolation_fields = property_schemas("model_a_isolation")
        if not isolation_fields or any(
            field.get("properties", {}).get("structural_dependency", {}).get("const") != "ABSENT"
            for field in isolation_fields
        ):
            raise DossierError(
                f"{document.path.relative_to(ROOT)}: "
                "Model A structural_dependency must be const ABSENT"
            )


def _validate_capital_schema_boundaries(store: SchemaStore, roadmap: dict[str, Any]) -> None:
    documents = {
        document.path: document
        for document in store.by_path.values()
        if document.path.name not in CAPITAL_SCHEMA_EXCLUSIONS
    }
    for contract in roadmap["contracts"]:
        contract_document = store.document(ROOT / contract["schema_path"])
        documents[contract_document.path] = contract_document

    for document in sorted(documents.values(), key=lambda item: item.path.name):
        if document.path.name in MODEL_A_NEGATIVE_CONTROL_SCHEMAS:
            _validate_model_a_negative_controls(document)

        for path, value in _walk_values(document.body):
            if isinstance(value, dict):
                for key in value:
                    key_matches = _schema_forbidden_tokens(key, document.path.name)
                    if key_matches:
                        raise DossierError(
                            f"{document.path.relative_to(ROOT)}:{path}: capital schema "
                            f"contains forbidden key token(s) {key_matches} in {key!r}"
                        )
            if (
                isinstance(value, dict)
                and value.get("type") == "object"
                and value.get("additionalProperties") is not False
            ):
                raise DossierError(
                    f"{document.path.relative_to(ROOT)}:{path}: capital-contract "
                    "object schemas must set additionalProperties=false"
                )
            if not isinstance(value, str):
                continue
            matches = _schema_forbidden_tokens(value, document.path.name)
            if matches:
                raise DossierError(
                    f"{document.path.relative_to(ROOT)}:{path}: capital schema "
                    f"contains forbidden coupling token(s) {matches}"
                )


def _validate_roadmap(roadmap: dict[str, Any], store: SchemaStore) -> None:
    store.validate(roadmap, ROADMAP_SCHEMA_PATH, str(ROADMAP_PATH.relative_to(ROOT)))

    if roadmap["baseline"]["commit"] != "9d442de287e123ae090b95838155dc41d76ee5f3":
        raise DossierError("roadmap baseline must pin the verified PR #69 merge commit")
    if roadmap["cadence"]["sprint_count"] != 12:
        raise DossierError("roadmap cadence must contain 12 weekly outcome sprints")

    for key in ("source_documents", "north_stars", "initiatives", "sprints"):
        duplicate = _duplicates(item["id"] for item in roadmap[key])
        if duplicate:
            raise DossierError(f"roadmap {key} has duplicate IDs: {sorted(duplicate)}")

    north_star_ids = {item["id"] for item in roadmap["north_stars"]}
    if north_star_ids != {"NS-CUD", "NS-ALERT", "NS-EDGE"}:
        raise DossierError(f"north-star IDs drifted: {sorted(north_star_ids)}")

    initiative_ids = {item["id"] for item in roadmap["initiatives"]}
    for initiative in roadmap["initiatives"]:
        unknown = set(initiative["depends_on"]) - initiative_ids
        if unknown:
            raise DossierError(
                f"initiative {initiative['id']} has unknown dependencies {sorted(unknown)}"
            )
        unknown_north_stars = set(initiative["north_star_ids"]) - north_star_ids
        if unknown_north_stars:
            raise DossierError(
                f"initiative {initiative['id']} has unknown north stars "
                f"{sorted(unknown_north_stars)}"
            )
        _require_paths(initiative["delivery_paths"], f"initiative {initiative['id']}")
    _assert_acyclic(
        {item["id"]: set(item["depends_on"]) for item in roadmap["initiatives"]},
        "initiative",
    )

    sprint_ids = [item["id"] for item in roadmap["sprints"]]
    expected_sprints = [f"S{week:02d}" for week in range(1, 13)]
    if sprint_ids != expected_sprints:
        raise DossierError(f"sprints must be ordered exactly {expected_sprints}")
    sprint_positions = {sprint_id: index for index, sprint_id in enumerate(sprint_ids)}
    for sprint in roadmap["sprints"]:
        if sprint["week"] != sprint_positions[sprint["id"]] + 1:
            raise DossierError(f"{sprint['id']}: week number does not match sequence")
        for dependency in sprint["depends_on"]:
            if dependency not in sprint_positions:
                raise DossierError(f"{sprint['id']}: unknown sprint dependency {dependency}")
            if sprint_positions[dependency] >= sprint_positions[sprint["id"]]:
                raise DossierError(f"{sprint['id']}: dependency {dependency} is not earlier")
        unknown_initiatives = set(sprint["initiative_ids"]) - initiative_ids
        if unknown_initiatives:
            raise DossierError(f"{sprint['id']}: unknown initiatives {sorted(unknown_initiatives)}")
        unknown_north_stars = set(sprint["north_star_ids"]) - north_star_ids
        if unknown_north_stars:
            raise DossierError(f"{sprint['id']}: unknown north stars {sorted(unknown_north_stars)}")
        _require_paths((item["path"] for item in sprint["deliverables"]), sprint["id"])
        if sprint["maximum_evidence_tier"] != "PAPER_ONLY":
            raise DossierError(
                f"{sprint['id']}: implementation sprint evidence tier must be PAPER_ONLY"
            )

    contract_names = required_contract_names(roadmap)
    duplicate_schema_paths = _duplicates(
        contract["schema_path"] for contract in roadmap["contracts"]
    )
    if duplicate_schema_paths:
        raise DossierError(
            "roadmap contracts reuse schema paths: " f"{sorted(duplicate_schema_paths)}"
        )
    for contract in roadmap["contracts"]:
        if contract["introduced_sprint"] not in sprint_positions:
            raise DossierError(
                f"contract {contract['name']}: unknown introduced_sprint "
                f"{contract['introduced_sprint']!r}"
            )
        _require_paths(
            [contract["spec_path"], contract["schema_path"]],
            f"contract {contract['name']}",
        )
        schema = _load_json(ROOT / contract["schema_path"])
        actual_name = schema.get("properties", {}).get("contract_name", {}).get("const")
        if actual_name != contract["name"]:
            raise DossierError(
                f"contract {contract['name']}: schema contract_name is {actual_name!r}"
            )
    if len(contract_names) != len(roadmap["contracts"]):
        raise DossierError("every roadmap contract must resolve exactly once")

    source_paths = [item["path"] for item in roadmap["source_documents"]]
    _require_paths(source_paths, "source_documents")
    for north_star in roadmap["north_stars"]:
        _require_paths(north_star["evidence_paths"], north_star["id"])
    for gate_name, gate in roadmap["release_gates"].items():
        _require_paths(gate["evidence_paths"], gate_name)

    operational = " ".join(roadmap["release_gates"]["operational_gate"]["criteria"]).lower()
    for token in ("30 consecutive", "99.5%", "xjo-tr", "bit-identical"):
        if token not in operational:
            raise DossierError(f"operational gate is missing locked criterion {token!r}")
    strategy = " ".join(roadmap["release_gates"]["strategy_gate"]["criteria"]).lower()
    for token in (
        "252 prospective",
        "20 matured",
        "63 sessions",
        "after-tax",
        "xjo-tr",
        "hold",
        "drawdown",
        "moving-block-bootstrap",
    ):
        if token not in strategy:
            raise DossierError(f"strategy gate is missing locked criterion {token!r}")
    promotion = re.sub(
        r"[^a-z0-9]+",
        "_",
        " ".join(roadmap["release_gates"]["promotion_gate"]["criteria"]).lower(),
    )
    for token in ("operational_gate", "strategy_gate", "james"):
        if token not in promotion:
            raise DossierError(f"promotion gate is missing locked criterion {token!r}")

    policy = roadmap["delivery_policy"]
    surfaces = re.sub(r"[^a-z0-9]+", "_", _canonical(policy["surfaces"]).lower())
    for token in ("cli", "daily_brief"):
        if token not in surfaces:
            raise DossierError(f"delivery surfaces are missing locked capability {token!r}")

    excluded = {
        re.sub(r"[^a-z0-9]+", "_", surface.lower()).strip("_")
        for surface in policy["excluded_surfaces"]
    }
    required_exclusions = {
        "web",
        "mobile",
        "multi_user",
        "public_advice",
        "broker_connection",
        "order_execution",
    }
    missing_exclusions = required_exclusions - excluded
    if missing_exclusions:
        raise DossierError(
            f"delivery policy is missing excluded surfaces {sorted(missing_exclusions)}"
        )

    execution_boundary = re.sub(
        r"[^a-z0-9]+", "_", _canonical(policy["execution_boundary"]).lower()
    )
    for token in (
        "order_staged",
        "cannot_place",
        "route",
        "submit",
        "modify",
        "cancel",
        "external_broker",
    ):
        if token not in execution_boundary:
            raise DossierError(f"execution boundary is missing locked token {token!r}")

    model_routing = re.sub(r"[^a-z0-9]+", "_", _canonical(policy["model_routing"]).lower())
    for token in ("fable_low", "opus_ultra", "capital_boundaries"):
        if token not in model_routing:
            raise DossierError(f"model routing is missing locked token {token!r}")
    if policy["model_routing"]["repair_escalation_after_failed_cycles"] != 2:
        raise DossierError("model routing must escalate after exactly two failed cycles")

    pull_request_budget = policy["pull_request_budget"]
    expected_budget = {
        "eight_hour": {"normal_total": 1, "absolute_max_total": 2},
        "twelve_hour": {
            "max_product": 2,
            "max_evidence_ops": 1,
            "absolute_max_total": 3,
        },
    }
    if pull_request_budget != expected_budget:
        raise DossierError(
            "pull-request budget must remain one/at-most-two for 8h and "
            "two-product-plus-one-evidence for 12h"
        )


def _assert_acyclic(graph: dict[str, set[str]], label: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise DossierError(f"{label} dependency cycle includes {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def load_fixture_documents() -> dict[str, Any]:
    """Load fixture JSON by filename for schema and semantic validation."""
    return {path.name: _load_json(path) for path in sorted(FIXTURE_DIR.glob("*.json"))}


def _fixture_items(document: Any, label: str) -> Iterable[tuple[str, dict[str, Any]]]:
    items = document if isinstance(document, list) else [document]
    if not items:
        raise DossierError(f"{label}: fixture cannot be empty")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise DossierError(f"{label}[{index}]: fixture item must be an object")
        suffix = f"[{index}]" if isinstance(document, list) else ""
        yield f"{label}{suffix}", item


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, str | int):
        raise DossierError(f"{label}: expected a Decimal string")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise DossierError(f"{label}: invalid Decimal value {value!r}") from exc


def _integer(value: Any, label: str) -> int:
    parsed = _decimal(value, label)
    if parsed != parsed.to_integral_value():
        raise DossierError(f"{label}: expected an integer value, got {value!r}")
    return int(parsed)


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or UTC_DATE_TIME.fullmatch(value) is None:
        raise DossierError(f"{label}: expected an explicit UTC date-time")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DossierError(f"{label}: invalid UTC date-time {value!r}") from exc


def _require_decimal_equal(actual: Decimal, expected: Decimal, label: str) -> None:
    if actual != expected:
        raise DossierError(f"{label}: arithmetic mismatch; got {actual}, expected {expected}")


def _canonical_fixture_json(value: Any, path: str = "$") -> str:
    """Serialize the deliberately restricted fixture subset in RFC 8785 form.

    Fixture contracts store financial numbers as Decimal strings.  Therefore the
    only JSON numbers accepted here are safe-range integers; binary floats are
    rejected.  Keys and strings are intentionally ASCII, making Unicode/UTF-16
    ordering unambiguous while preserving RFC 8785 escaping rules.
    """

    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_JSON_INTEGER:
            raise DossierError(f"{path}: integer exceeds the RFC 8785 safe fixture subset")
        return str(value)
    if isinstance(value, float):
        raise DossierError(f"{path}: JSON float is outside the canonical fixture subset")
    if isinstance(value, str):
        if not value.isascii():
            raise DossierError(f"{path}: non-ASCII string is outside the fixture subset")
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return (
            "["
            + ",".join(
                _canonical_fixture_json(item, f"{path}[{index}]")
                for index, item in enumerate(value)
            )
            + "]"
        )
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise DossierError(f"{path}: JSON object key must be a string")
            if not key.isascii():
                raise DossierError(f"{path}: non-ASCII object key is outside the fixture subset")
        members = []
        for key in sorted(value):
            encoded_key = json.dumps(key, ensure_ascii=False, separators=(",", ":"))
            encoded_value = _canonical_fixture_json(value[key], f"{path}.{key}")
            members.append(f"{encoded_key}:{encoded_value}")
        return "{" + ",".join(members) + "}"
    raise DossierError(f"{path}: unsupported canonical fixture type {type(value).__name__}")


def fixture_payload_sha256(item: dict[str, Any]) -> str:
    """Recompute a root fixture digest, excluding exactly the digest field itself."""
    envelope = item.get("canonical_hash")
    if not isinstance(envelope, dict):
        raise DossierError("fixture item has no canonical_hash envelope")
    if "payload_sha256" not in envelope:
        raise DossierError("fixture canonical_hash envelope has no payload_sha256")
    projected = dict(item)
    projected_envelope = dict(envelope)
    del projected_envelope["payload_sha256"]
    projected["canonical_hash"] = projected_envelope
    canonical = _canonical_fixture_json(projected)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def review_context_payload_sha256(item: dict[str, Any]) -> str:
    """Hash the immutable ReviewContext subset, excluding both identity envelopes."""
    if item.get("contract_name") != "review-context-v1":
        raise DossierError("narrow context hash requires a review-context-v1 fixture")
    if "context_sha256" not in item or "canonical_hash" not in item:
        raise DossierError("review-context-v1 is missing a required hash member")
    projected = {
        key: value for key, value in item.items() if key not in {"context_sha256", "canonical_hash"}
    }
    canonical = _canonical_fixture_json(projected)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fixture_artifact_id(item: dict[str, Any]) -> str | None:
    contract_name = item.get("contract_name")
    if contract_name == "investment-case-lineage-v1":
        lineage = item.get("lineage")
        identifier = lineage.get("lineage_id") if isinstance(lineage, dict) else None
    else:
        identifier_field = ARTIFACT_ID_FIELDS.get(contract_name)
        identifier = item.get(identifier_field) if identifier_field else None
    return identifier if isinstance(identifier, str) else None


def _synchronize_fixture_references(fixtures: dict[str, Any]) -> int:
    by_contract_and_id: dict[tuple[str, str], str] = {}
    digest_candidates_by_id: dict[str, set[str]] = {}
    narrow_context_by_id: dict[str, str] = {}
    root_identity_by_object: dict[int, str] = {}
    for filename, document in fixtures.items():
        for _, item in _fixture_items(document, filename):
            contract_name = item.get("contract_name")
            artifact_id = _fixture_artifact_id(item)
            if (
                not isinstance(contract_name, str)
                or artifact_id is None
                or "canonical_hash" not in item
            ):
                continue
            digest = _canonical_hash_identity(item, filename)
            by_contract_and_id[(contract_name, artifact_id)] = digest
            digest_candidates_by_id.setdefault(artifact_id, set()).add(digest)
            root_identity_by_object[id(item)] = artifact_id
            if contract_name == "review-context-v1":
                context_digest = item.get("context_sha256")
                if isinstance(context_digest, str):
                    narrow_context_by_id[artifact_id] = context_digest
    by_unambiguous_id = {
        artifact_id: next(iter(digests))
        for artifact_id, digests in digest_candidates_by_id.items()
        if len(digests) == 1
    }

    changed = 0
    for filename, document in fixtures.items():
        for _, item in _fixture_items(document, filename):
            root_identity = root_identity_by_object.get(id(item))
            for _, node in _walk_values(item):
                if not isinstance(node, dict) or node is item.get("canonical_hash"):
                    continue
                contract_name = node.get("contract_name")
                artifact_id = node.get("artifact_id")
                if (
                    isinstance(contract_name, str)
                    and isinstance(artifact_id, str)
                    and isinstance(node.get("sha256"), str)
                ):
                    digest = by_contract_and_id.get((contract_name, artifact_id))
                    if digest is not None and node["sha256"] != digest:
                        node["sha256"] = digest
                        changed += 1
                reference_id = node.get("id")
                if isinstance(reference_id, str) and isinstance(node.get("sha256"), str):
                    digest = by_unambiguous_id.get(reference_id)
                    if digest is not None and node["sha256"] != digest:
                        node["sha256"] = digest
                        changed += 1
                for key, candidate_id in tuple(node.items()):
                    if not key.endswith("_id") or not isinstance(candidate_id, str):
                        continue
                    if candidate_id == root_identity:
                        continue
                    digest_key = REFERENCE_DIGEST_KEYS.get(key, f"{key.removesuffix('_id')}_sha256")
                    if not isinstance(node.get(digest_key), str):
                        continue
                    reference_contract = REFERENCE_CONTRACT_NAMES.get(key)
                    if reference_contract is not None:
                        digest = by_contract_and_id.get((reference_contract, candidate_id))
                    elif digest_key == "context_sha256":
                        digest = narrow_context_by_id.get(candidate_id)
                    else:
                        digest = by_unambiguous_id.get(candidate_id)
                    if digest is not None and node[digest_key] != digest:
                        node[digest_key] = digest
                        changed += 1
    return changed


def rewrite_fixture_hashes(fixtures: dict[str, Any]) -> int:
    """Repair root hashes and locally resolvable references; never called implicitly."""
    repaired_roots: set[str] = set()
    maximum_passes = max(
        4, sum(1 for document in fixtures.values() for _ in _fixture_items(document, "fixture")) * 2
    )
    for _ in range(maximum_passes):
        changed = 0
        for filename, document in fixtures.items():
            for item_label, item in _fixture_items(document, filename):
                if "canonical_hash" not in item:
                    continue
                if item.get("contract_name") == "review-context-v1":
                    context_digest = review_context_payload_sha256(item)
                    if item.get("context_sha256") != context_digest:
                        item["context_sha256"] = context_digest
                        changed += 1
                digest = fixture_payload_sha256(item)
                envelope = item["canonical_hash"]
                if not isinstance(envelope, dict):
                    raise DossierError(f"{item_label}: canonical_hash must be an object")
                if envelope.get("payload_sha256") != digest:
                    envelope["payload_sha256"] = digest
                    repaired_roots.add(item_label)
                    changed += 1
        changed += _synchronize_fixture_references(fixtures)
        if changed == 0:
            return len(repaired_roots)
    raise DossierError(
        "fixture hash repair did not converge; check for a forbidden self-reference cycle"
    )


def write_fixture_hashes() -> int:
    """Rewrite root fixture hash fields on disk for the explicit CLI repair flag."""
    fixtures = load_fixture_documents()
    repaired = rewrite_fixture_hashes(fixtures)
    if not repaired:
        return 0
    for filename, document in fixtures.items():
        path = FIXTURE_DIR / filename
        rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        if path.read_text(encoding="utf-8") != rendered:
            path.write_text(rendered, encoding="utf-8")
    return repaired


def _validate_fixture_hash_convention(fixtures: dict[str, Any]) -> None:
    """Recompute root hashes; treat only non-root references as opaque identities."""
    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            if isinstance(item.get("contract_name"), str) and "canonical_hash" not in item:
                raise DossierError(
                    f"{item_label}: contract fixture is missing its root canonical_hash"
                )
            for value_path, value in _walk_values(item):
                if not isinstance(value, dict):
                    continue
                for key, candidate in value.items():
                    if key != "sha256" and not key.endswith("_sha256"):
                        continue
                    if candidate is None:
                        continue
                    if not isinstance(candidate, str) or SHA256_HEX.fullmatch(candidate) is None:
                        raise DossierError(
                            f"{item_label}:{value_path}.{key}: opaque hash identity "
                            "must be 64 lower-case hexadecimal characters"
                        )
                envelope = value.get("canonical_hash")
                if not isinstance(envelope, dict):
                    continue
                expected_envelope = {
                    "canonicalization": "RFC8785",
                    "hash_algorithm": "SHA-256",
                    "excluded_json_pointer": "/canonical_hash/payload_sha256",
                }
                for key, expected in expected_envelope.items():
                    if envelope.get(key) != expected:
                        raise DossierError(
                            f"{item_label}:{value_path}.canonical_hash.{key}: "
                            f"expected {expected!r}"
                        )
                digest = envelope.get("payload_sha256")
                if not isinstance(digest, str) or SHA256_HEX.fullmatch(digest) is None:
                    raise DossierError(
                        f"{item_label}:{value_path}.canonical_hash.payload_sha256: "
                        "digest must be 64 lower-case hexadecimal characters"
                    )
            if "canonical_hash" in item:
                expected_digest = fixture_payload_sha256(item)
                actual_digest = item["canonical_hash"].get("payload_sha256")
                if actual_digest != expected_digest:
                    raise DossierError(
                        f"{item_label}: canonical_hash payload mismatch; expected "
                        f"{expected_digest}"
                    )
                if item.get("contract_name") == "review-context-v1":
                    expected_context_digest = review_context_payload_sha256(item)
                    actual_context_digest = item.get("context_sha256")
                    if actual_context_digest != expected_context_digest:
                        raise DossierError(
                            f"{item_label}: context_sha256 subset mismatch; expected "
                            f"{expected_context_digest}"
                        )
                    if actual_context_digest == actual_digest:
                        raise DossierError(
                            f"{item_label}: context_sha256 must not alias the root digest"
                        )


def _is_placeholder_digest(digest: str) -> bool:
    """True for a digest built from at most two distinct characters.

    Catches the obvious stubs -- 64 'd's, all zeroes, a repeated two-character
    pattern. Such digests are legitimate for artifacts the dossier does not
    carry (external ratification records, fee schedules), so this is only a
    signal, never a verdict on its own -- the caller pairs it with evidence that
    the reference SHOULD have resolved.
    """
    return len(set(digest)) <= 2


def _validate_locally_resolvable_reference_hashes(fixtures: dict[str, Any]) -> None:
    # Digest per (contract_name, artifact_id): the contract-scoped resolution
    # index the reference checks below read.
    by_contract_and_id: dict[tuple[str, str], str] = {}
    # (contract_name, source_filename, digest) per bare artifact ID. Doubles as
    # the sole collision guard: an artifact ID may never denote two different
    # payloads, whether or not the contract names match. Without the guard the
    # reused ID drops out of digest_by_id below and every bare-id reference
    # check naming it stops running -- the harness stays green while the
    # forbidden condition exists, and a wrong digest behind such a reference is
    # unobservable to both this validator and the repair path, which builds the
    # same index. Keying on the bare ID subsumes the same-contract case, so the
    # two collisions differ only in how the error names them.
    artifact_owner: dict[str, tuple[str, str, str]] = {}
    narrow_context_by_id: dict[str, str] = {}
    root_identity_by_object: dict[int, str] = {}
    for filename, document in fixtures.items():
        for _, item in _fixture_items(document, filename):
            contract_name = item.get("contract_name")
            artifact_id = _fixture_artifact_id(item)
            if not isinstance(contract_name, str) or artifact_id is None:
                continue
            digest = _canonical_hash_identity(item, filename)
            prior_owner = artifact_owner.get(artifact_id)
            if prior_owner is not None and prior_owner[2] != digest:
                prior_contract, prior_file, prior_digest = prior_owner
                if prior_contract == contract_name:
                    raise DossierError(
                        f"{contract_name} artifact id {artifact_id!r} is reused for two "
                        f"different payloads: {prior_file} ({prior_digest[:12]}...) and "
                        f"{filename} ({digest[:12]}...)"
                    )
                raise DossierError(
                    f"artifact id {artifact_id!r} denotes two different payloads across "
                    f"contracts: {prior_contract} in {prior_file} "
                    f"({prior_digest[:12]}...) and {contract_name} in {filename} "
                    f"({digest[:12]}...); a bare-id reference to it cannot be resolved"
                )
            artifact_owner[artifact_id] = (contract_name, filename, digest)
            by_contract_and_id[(contract_name, artifact_id)] = digest
            root_identity_by_object[id(item)] = artifact_id
            if contract_name == "review-context-v1":
                context_digest = item.get("context_sha256")
                if isinstance(context_digest, str):
                    narrow_context_by_id[artifact_id] = context_digest
    # Every ID is unambiguous by construction: the guard above rejects any ID
    # reused for different bytes, so none can carry a second digest here. Relax
    # that guard and this index must go back to filtering ambiguous IDs out.
    digest_by_id = {artifact_id: owner[2] for artifact_id, owner in artifact_owner.items()}

    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            root_identity = root_identity_by_object.get(id(item))
            for value_path, node in _walk_values(item):
                if not isinstance(node, dict) or node is item.get("canonical_hash"):
                    continue
                contract_name = node.get("contract_name")
                artifact_id = node.get("artifact_id")
                if (
                    isinstance(contract_name, str)
                    and isinstance(artifact_id, str)
                    and isinstance(node.get("sha256"), str)
                ):
                    expected = by_contract_and_id.get((contract_name, artifact_id))
                    if expected is not None and node["sha256"] != expected:
                        raise DossierError(
                            f"{item_label}:{value_path}: local artifact reference hash "
                            f"does not resolve to {contract_name}/{artifact_id}"
                        )
                    # Independent backstop: a placeholder digest is legitimate
                    # for an artifact the dossier does not carry, so absence of
                    # the id is NOT evidence of a stub. But a placeholder aimed
                    # at an id the dossier DOES carry is unambiguously wrong,
                    # and the resolution check above misses it whenever the id
                    # was claimed under a different contract name.
                    if (
                        expected is None
                        and artifact_id in artifact_owner
                        and _is_placeholder_digest(node["sha256"])
                    ):
                        owner_contract, owner_file, _ = artifact_owner[artifact_id]
                        raise DossierError(
                            f"{item_label}:{value_path}: placeholder digest "
                            f"{node['sha256'][:12]}... names {contract_name}/{artifact_id}, but "
                            f"that id is carried by {owner_contract} in {owner_file}"
                        )
                reference_id = node.get("id")
                if isinstance(reference_id, str) and isinstance(node.get("sha256"), str):
                    expected = digest_by_id.get(reference_id)
                    if expected is not None and node["sha256"] != expected:
                        raise DossierError(
                            f"{item_label}:{value_path}: local reference hash does not "
                            f"resolve to {reference_id}"
                        )
                for key, candidate_id in node.items():
                    if (
                        not key.endswith("_id")
                        or not isinstance(candidate_id, str)
                        or candidate_id == root_identity
                    ):
                        continue
                    digest_key = REFERENCE_DIGEST_KEYS.get(key, f"{key.removesuffix('_id')}_sha256")
                    actual = node.get(digest_key)
                    reference_contract = REFERENCE_CONTRACT_NAMES.get(key)
                    if reference_contract is not None:
                        expected = by_contract_and_id.get((reference_contract, candidate_id))
                    elif digest_key == "context_sha256":
                        expected = narrow_context_by_id.get(candidate_id)
                    else:
                        expected = digest_by_id.get(candidate_id)
                    if isinstance(actual, str) and expected is not None and actual != expected:
                        raise DossierError(
                            f"{item_label}:{value_path}.{digest_key}: local reference "
                            f"hash does not resolve to {candidate_id}"
                        )


def _validate_contract_name_references(fixtures: dict[str, Any], store: SchemaStore) -> None:
    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            for value_path, value in _walk_values(item):
                if not isinstance(value, dict):
                    continue
                contract_name = value.get("contract_name")
                if not isinstance(contract_name, str):
                    continue
                schema_path = (SCHEMA_DIR / f"{contract_name}.schema.json").resolve()
                if schema_path not in store.by_path:
                    raise DossierError(
                        f"{item_label}:{value_path}.contract_name: no local schema resolves "
                        f"{contract_name!r}"
                    )
                schema_contract_name = (
                    store.by_path[schema_path]
                    .body.get("properties", {})
                    .get("contract_name", {})
                    .get("const")
                )
                if schema_contract_name != contract_name:
                    raise DossierError(
                        f"{item_label}:{value_path}.contract_name: schema resolves to "
                        f"{schema_contract_name!r}, not {contract_name!r}"
                    )


def _validate_fixture_chronology(fixtures: dict[str, Any]) -> None:
    as_of_fields = ("data_as_of", "as_of", "context_as_of")
    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            root_created_raw = item.get("created_at")
            root_created = (
                _timestamp(root_created_raw, f"{item_label}.created_at")
                if isinstance(root_created_raw, str)
                else None
            )
            for value_path, value in _walk_values(item):
                if not isinstance(value, dict):
                    continue
                created_raw = value.get("created_at")
                if not isinstance(created_raw, str):
                    continue
                created = _timestamp(created_raw, f"{item_label}:{value_path}.created_at")
                for as_of_field in as_of_fields:
                    as_of_raw = value.get(as_of_field)
                    if not isinstance(as_of_raw, str):
                        continue
                    as_of = _timestamp(
                        as_of_raw,
                        f"{item_label}:{value_path}.{as_of_field}",
                    )
                    if created < as_of:
                        raise DossierError(
                            f"{item_label}:{value_path}: created_at precedes {as_of_field}"
                        )
                if root_created is not None and value is not item and created > root_created:
                    raise DossierError(
                        f"{item_label}:{value_path}: referenced artifact was created after "
                        "its consuming fixture"
                    )


def _validate_numeric_wire_shapes(fixtures: dict[str, Any]) -> None:
    integer_string = re.compile(r"^(?:0|[1-9][0-9]*)$")
    decimal6_string = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]{6}$")
    exact_decimal_fields = {
        "maximum_drawdown",
        "one_sided_confidence",
        "one_sided_lower_bound",
        "period_return",
        "point_estimate",
        "priced_nav_day_fraction",
    }
    decimal_suffixes = ("_aud", "_fraction", "_weight", "_return")

    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            for value_path, value in _walk_values(item):
                if not isinstance(value, dict):
                    continue
                for key, candidate in value.items():
                    quantity_field = (
                        key == "quantity" or key.endswith("_quantity") or key == "eligible_volume"
                    )
                    if quantity_field and (
                        not isinstance(candidate, str)
                        or integer_string.fullmatch(candidate) is None
                    ):
                        raise DossierError(
                            f"{item_label}:{value_path}.{key}: share/board-lot/order "
                            "quantity must be a canonical non-negative integer string"
                        )
                    decimal_field = key in exact_decimal_fields or key.endswith(decimal_suffixes)
                    if (
                        decimal_field
                        and candidate is not None
                        and not isinstance(candidate, bool)
                        and (
                            not isinstance(candidate, str)
                            or decimal6_string.fullmatch(candidate) is None
                        )
                    ):
                        raise DossierError(
                            f"{item_label}:{value_path}.{key}: money/rate value must be "
                            "a six-place Decimal string"
                        )


def _validate_origin_snapshot_semantics(fixtures: dict[str, Any]) -> None:
    origin = fixtures.get("evaluation-origin-valid.json")
    config = fixtures.get("evaluator-config-valid.json")
    if not isinstance(origin, dict) or not isinstance(config, dict):
        raise DossierError(
            "origin semantics require evaluation-origin-valid.json and "
            "evaluator-config-valid.json"
        )
    class_contracts: dict[str, set[str]] = {
        "PORTFOLIO": {"portfolio-snapshot-v1"},
        "PROPOSAL": {"portfolio-proposal-v1"},
        "SIZING": {"sizing-policy-v1"},
        "TAX_PROFILE": {"tax-profile-v1"},
        "TRADING_CALENDAR": {"trading-calendar-v1"},
        "BENCHMARK": {"benchmark-snapshot-v1"},
        "REPORT": {"broker-report-v1"},
        "REVIEW": {"review-context-v1", "review-eligibility-v1"},
        "CONSTRUCTION": {"portfolio-construction-policy-v1"},
        "RISK_POLICY": {"risk-policy-v1"},
        "STAGING_POLICY": {"staging-policy-v1"},
        "FILL_MODEL": {"fill-model-v1"},
        "ACCOUNTING_POLICY": {"accounting-policy-v1"},
        "BENCHMARK_POLICY": {"benchmark-policy-v1"},
    }
    required_classes = {
        "PORTFOLIO",
        "PROPOSAL",
        "SIZING",
        "TAX_PROFILE",
        "TRADING_CALENDAR",
        "BENCHMARK",
    }
    configured_classes = config.get("required_snapshot_classes")
    if configured_classes is None:
        source_requirements = config.get("source_requirements")
        if isinstance(source_requirements, dict):
            configured_classes = source_requirements.get("required_snapshot_classes")
    if configured_classes is not None:
        if not isinstance(configured_classes, list) or not all(
            isinstance(value, str) for value in configured_classes
        ):
            raise DossierError(
                "evaluator-config-valid.json: required_snapshot_classes must be an array"
            )
        required_classes.update(configured_classes)

    manifest = origin.get("snapshot_manifest")
    if not isinstance(manifest, list):
        raise DossierError("evaluation-origin-valid.json.snapshot_manifest: expected an array")
    classes = [entry.get("snapshot_class") for entry in manifest]
    if len(classes) != len(set(classes)):
        raise DossierError("evaluation-origin-valid.json: snapshot classes must be unique")
    cutoff = _timestamp(
        origin.get("knowledge_cutoff"),
        "evaluation-origin-valid.json.knowledge_cutoff",
    )
    for index, entry in enumerate(manifest):
        label = f"evaluation-origin-valid.json.snapshot_manifest[{index}]"
        snapshot_class = entry.get("snapshot_class")
        reference = entry.get("ref")
        if not isinstance(reference, dict):
            raise DossierError(f"{label}: missing artifact reference")
        permitted_contracts = class_contracts.get(snapshot_class)
        if permitted_contracts is None:
            raise DossierError(f"{label}: snapshot class has no contract mapping")
        if reference.get("contract_name") not in permitted_contracts:
            raise DossierError(
                f"{label}: {snapshot_class} does not map to " f"{reference.get('contract_name')!r}"
            )
        created_at = _timestamp(reference.get("created_at"), f"{label}.ref.created_at")
        if created_at > cutoff:
            raise DossierError(f"{label}: snapshot was created after the knowledge cutoff")

    if origin.get("origin_status") == "OPEN" and origin.get("missing_required_inputs") == []:
        missing_classes = required_classes - set(classes)
        if missing_classes:
            raise DossierError(
                "evaluation-origin-valid.json: OPEN origin with no missing inputs lacks "
                f"required snapshot classes {sorted(missing_classes)}"
            )

    intent = fixtures.get("paper-intent-valid.json")
    if isinstance(intent, dict) and intent.get("status") == "RECORDED":
        sizing_ref = intent.get("sizing_decision_ref")
        if not isinstance(sizing_ref, dict):
            raise DossierError(
                "paper-intent-valid.json: RECORDED intent lacks a sizing decision reference"
            )
        sizing_matches: list[dict[str, Any]] = []
        for filename, document in fixtures.items():
            for _, item in _fixture_items(document, filename):
                if (
                    item.get("contract_name") == "sizing-decision-v1"
                    and item.get("sizing_decision_id") == sizing_ref.get("artifact_id")
                    and _canonical_hash_identity(item, filename) == sizing_ref.get("sha256")
                ):
                    sizing_matches.append(item)
        if len(sizing_matches) != 1 or sizing_matches[0].get("status") != "SIZED":
            raise DossierError(
                "paper-intent-valid.json: RECORDED intent sizing decision does not resolve "
                "uniquely to SIZED"
            )
        portfolio_entry = next(
            (entry for entry in manifest if entry.get("snapshot_class") == "PORTFOLIO"),
            None,
        )
        frozen_ref = portfolio_entry.get("ref") if isinstance(portfolio_entry, dict) else None
        sizing_snapshot_ref = sizing_matches[0].get("portfolio_snapshot_ref")
        if (
            not isinstance(frozen_ref, dict)
            or not isinstance(sizing_snapshot_ref, dict)
            or sizing_snapshot_ref.get("id") != frozen_ref.get("artifact_id")
            or sizing_snapshot_ref.get("sha256") != frozen_ref.get("sha256")
        ):
            raise DossierError(
                "paper-intent-valid.json: sizing portfolio snapshot does not match "
                "the frozen origin snapshot"
            )


def _canonical_hash_identity(document: dict[str, Any], label: str) -> str:
    envelope = document.get("canonical_hash")
    if not isinstance(envelope, dict):
        raise DossierError(f"{label}: missing canonical_hash identity")
    digest = envelope.get("payload_sha256")
    if not isinstance(digest, str) or SHA256_HEX.fullmatch(digest) is None:
        raise DossierError(f"{label}: invalid canonical_hash identity")
    return digest


def _validate_lineage_semantics(fixtures: dict[str, Any]) -> None:
    stage_rank = {
        "RESEARCH_REVIEWED": 0,
        "EVALUATION_FROZEN": 1,
        "PROPOSAL_BUILT": 2,
        "SIZE_DECIDED": 3,
        "ORDER_STAGED": 4,
    }
    stage_state = {
        "RESEARCH_REVIEWED": "PAPER_ELIGIBLE",
        "EVALUATION_FROZEN": "SHADOW_ACTIVE",
        "PROPOSAL_BUILT": "SHADOW_ACTIVE",
        "SIZE_DECIDED": "ADVICE_READY",
        "ORDER_STAGED": "ORDER_STAGED",
    }
    minimum_stage = {
        "monitor": 1,
        "evaluation": 1,
        "construction_policy_ref": 2,
        "risk_policy_ref": 2,
        "portfolio_proposal_ref": 2,
        "sizing_decision_ref": 3,
        "staging_policy_ref": 4,
        "promotion_decision_ref": 4,
        "staged_order_set_ref": 4,
    }
    lineages: list[tuple[str, dict[str, Any]]] = []
    for filename, document in fixtures.items():
        for item_label, item in _fixture_items(document, filename):
            for value_path, value in _walk_values(item):
                if isinstance(value, dict) and "lineage_stage" in value:
                    lineages.append((f"{item_label}:{value_path}", value))

    if not lineages:
        raise DossierError("fixtures: no investment-case lineage records found")

    by_case: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for label, lineage in lineages:
        stage = lineage.get("lineage_stage")
        if stage not in stage_rank:
            raise DossierError(f"{label}: unknown lineage stage {stage!r}")
        rank = stage_rank[stage]
        if not isinstance(lineage.get("research"), dict) or not isinstance(
            lineage.get("review"), dict
        ):
            raise DossierError(f"{label}: lineage must retain research and review references")
        if lineage.get("case_state") != stage_state[stage]:
            raise DossierError(
                f"{label}: case_state does not match monotonic lineage stage {stage}"
            )
        for field, required_rank in minimum_stage.items():
            present = isinstance(lineage.get(field), dict)
            if rank >= required_rank and not present:
                raise DossierError(f"{label}: {stage} requires {field}")
            if rank < required_rank and lineage.get(field) is not None:
                raise DossierError(f"{label}: {field} is a future-stage reference at {stage}")
        if lineage.get("evidence_tier") == "EVIDENCE_BACKED" and not isinstance(
            lineage.get("promotion_decision_ref"), dict
        ):
            raise DossierError(
                f"{label}: EVIDENCE_BACKED requires an immutable James promotion reference"
            )
        case_id = lineage.get("investment_case_id")
        if not isinstance(case_id, str):
            raise DossierError(f"{label}: missing investment_case_id")
        by_case.setdefault(case_id, []).append((label, lineage))

    stable_fields = (
        "research",
        "review",
        "monitor",
        "evaluation",
        "construction_policy_ref",
        "risk_policy_ref",
        "portfolio_proposal_ref",
        "sizing_decision_ref",
        "staging_policy_ref",
        "promotion_decision_ref",
        "staged_order_set_ref",
    )
    for case_id, records in by_case.items():
        stable_values: dict[str, str] = {}
        stage_times: dict[int, list[tuple[datetime, datetime]]] = {}
        for label, lineage in records:
            rank = stage_rank[lineage["lineage_stage"]]
            stage_times.setdefault(rank, []).append(
                (
                    _timestamp(lineage.get("as_of"), f"{label}.as_of"),
                    _timestamp(lineage.get("created_at"), f"{label}.created_at"),
                )
            )
            for field in stable_fields:
                value = lineage.get(field)
                if value is None:
                    continue
                canonical = _canonical(value)
                previous = stable_values.setdefault(field, canonical)
                if previous != canonical:
                    raise DossierError(f"{label}: {field} drifted within investment case {case_id}")
        ordered_ranks = sorted(stage_times)
        for earlier, later in pairwise(ordered_ranks):
            earlier_as_of = max(item[0] for item in stage_times[earlier])
            later_as_of = min(item[0] for item in stage_times[later])
            earlier_created = max(item[1] for item in stage_times[earlier])
            later_created = min(item[1] for item in stage_times[later])
            if later_as_of < earlier_as_of or later_created < earlier_created:
                raise DossierError(
                    f"investment case {case_id}: lineage stage chronology is not monotonic"
                )

    integrated = fixtures.get("integrated-investment-chain.json")
    if not isinstance(integrated, dict):
        raise DossierError("integrated-investment-chain.json: fixture must be an object")
    lineage = integrated.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("lineage_stage") != "ORDER_STAGED":
        raise DossierError(
            "integrated-investment-chain.json: integrated lineage must finish at ORDER_STAGED"
        )

    identity_specs = {
        "construction_policy_ref": (
            "portfolio-construction-policy-valid.json",
            "policy_id",
        ),
        "risk_policy_ref": ("risk-policy-valid.json", "policy_id"),
        "portfolio_proposal_ref": ("portfolio-proposal-valid.json", "proposal_id"),
        "sizing_decision_ref": ("sizing-valid.json", "sizing_decision_id"),
        "staging_policy_ref": ("staging-policy-valid.json", "policy_id"),
        "promotion_decision_ref": (
            "promotion-decision-valid.json",
            "promotion_decision_id",
        ),
        "staged_order_set_ref": ("staged-order-valid.json", "order_set_id"),
    }
    for ref_field, (fixture_name, identifier_field) in identity_specs.items():
        referenced = lineage.get(ref_field)
        target = fixtures.get(fixture_name)
        if not isinstance(referenced, dict) or not isinstance(target, dict):
            raise DossierError(f"integrated-investment-chain.json: cannot resolve {ref_field}")
        expected_id = target.get(identifier_field)
        expected_hash = _canonical_hash_identity(target, fixture_name)
        if referenced.get("id") != expected_id or referenced.get("sha256") != expected_hash:
            raise DossierError(
                f"integrated-investment-chain.json: {ref_field} does not resolve to "
                f"{fixture_name}"
            )


def _validate_review_semantics(fixtures: dict[str, Any]) -> None:
    """Resolve and recompute the blind-review decision from immutable inputs."""
    report = fixtures.get("broker-report-valid.json")
    context = fixtures.get("review-context-valid.json")
    assessments = fixtures.get("reviewer-assessments-blind.json")
    eligibility = fixtures.get("review-eligibility-valid.json")
    if (
        not isinstance(report, dict)
        or not isinstance(context, dict)
        or not isinstance(assessments, list)
        or not all(isinstance(item, dict) for item in assessments)
        or not isinstance(eligibility, dict)
    ):
        raise DossierError(
            "review semantics require report, context, assessment-batch and eligibility fixtures"
        )

    expected_report_ref = {
        "id": report.get("report_version_id"),
        "sha256": _canonical_hash_identity(report, "broker-report-valid.json"),
    }
    if context.get("report_version_id") != report.get("report_version_id") or context.get(
        "thesis_id"
    ) != report.get("thesis_id"):
        raise DossierError("review-context-valid.json: report/thesis identity does not resolve")
    if eligibility.get("report_ref") != expected_report_ref:
        raise DossierError("review-eligibility-valid.json.report_ref: does not resolve report")
    if (
        eligibility.get("context_id") != context.get("context_id")
        or eligibility.get("context_sha256") != context.get("context_sha256")
        or eligibility.get("review_cycle_id") != context.get("review_cycle_id")
    ):
        raise DossierError("review-eligibility-valid.json: context/cycle identity does not resolve")

    candidate_hash = eligibility.get("report_candidate_sha256")
    if candidate_hash != expected_report_ref["sha256"]:
        raise DossierError(
            "review-eligibility-valid.json.report_candidate_sha256: "
            "does not resolve the exact broker-report bytes"
        )

    report_claims = report.get("claim_register")
    context_claims = context.get("claims")
    context_evidence = context.get("evidence")
    if (
        not isinstance(report_claims, list)
        or not all(isinstance(item, dict) for item in report_claims)
        or not isinstance(context_claims, list)
        or not all(isinstance(item, dict) for item in context_claims)
        or not isinstance(context_evidence, list)
        or not all(isinstance(item, dict) for item in context_evidence)
    ):
        raise DossierError("review context requires typed claim and evidence arrays")
    if context_claims != report_claims:
        raise DossierError(
            "review-context-valid.json.claims: do not resolve the exact report claim register"
        )
    evidence_by_id: dict[int, dict[str, Any]] = {}
    for index, evidence in enumerate(context_evidence):
        evidence_id = evidence.get("evidence_id")
        if (
            not isinstance(evidence_id, int)
            or isinstance(evidence_id, bool)
            or evidence_id in evidence_by_id
        ):
            raise DossierError(
                f"review-context-valid.json.evidence[{index}].evidence_id: " "missing or duplicate"
            )
        evidence_by_id[evidence_id] = evidence
    claim_evidence_by_id: dict[str, set[int]] = {}
    for index, claim in enumerate(context_claims):
        claim_id = claim.get("claim_id")
        evidence_ids = claim.get("evidence_ids")
        if (
            not isinstance(claim_id, str)
            or claim_id in claim_evidence_by_id
            or not isinstance(evidence_ids, list)
            or not all(
                isinstance(item, int) and not isinstance(item, bool) for item in evidence_ids
            )
        ):
            raise DossierError(
                f"review-context-valid.json.claims[{index}]: invalid claim/evidence identity"
            )
        evidence_id_set = set(evidence_ids)
        if not evidence_id_set or not evidence_id_set <= evidence_by_id.keys():
            raise DossierError(
                f"review-context-valid.json.claims[{index}].evidence_ids: "
                "do not resolve frozen evidence"
            )
        claim_evidence_by_id[claim_id] = evidence_id_set
    for index, scenario in enumerate(context.get("scenarios", [])):
        if not isinstance(scenario, dict):
            raise DossierError(f"review-context-valid.json.scenarios[{index}]: invalid")
        scenario_evidence = scenario.get("evidence_ids")
        if (
            not isinstance(scenario_evidence, list)
            or not set(scenario_evidence) <= evidence_by_id.keys()
        ):
            raise DossierError(
                f"review-context-valid.json.scenarios[{index}].evidence_ids: "
                "do not resolve frozen evidence"
            )

    report_data_as_of = _timestamp(report.get("data_as_of"), "broker-report-valid.json.data_as_of")
    report_created_at = _timestamp(report.get("created_at"), "broker-report-valid.json.created_at")
    context_as_of = _timestamp(
        context.get("context_as_of"), "review-context-valid.json.context_as_of"
    )
    context_generated_at = _timestamp(
        context.get("generated_at"), "review-context-valid.json.generated_at"
    )
    if not report_data_as_of <= report_created_at <= context_as_of <= context_generated_at:
        raise DossierError("review report/context chronology is not point-in-time monotonic")
    evidence_by_source_type: dict[str, list[dict[str, Any]]] = {}
    for index, evidence in enumerate(context_evidence):
        label = f"review-context-valid.json.evidence[{index}]"
        data_as_of = _timestamp(evidence.get("data_as_of"), f"{label}.data_as_of")
        observed_at = _timestamp(evidence.get("observed_at"), f"{label}.observed_at")
        retrieved_at = _timestamp(evidence.get("retrieved_at"), f"{label}.retrieved_at")
        if not data_as_of <= observed_at <= retrieved_at <= context_as_of:
            raise DossierError(f"{label}: future or non-monotonic point-in-time evidence")
        source_type = evidence.get("source_type")
        if not isinstance(source_type, str):
            raise DossierError(f"{label}.source_type: invalid")
        evidence_by_source_type.setdefault(source_type, []).append(evidence)
    portfolio = context.get("portfolio")
    if not isinstance(portfolio, dict):
        raise DossierError("review-context-valid.json.portfolio: invalid")
    portfolio_as_of = _timestamp(
        portfolio.get("as_of"), "review-context-valid.json.portfolio.as_of"
    )
    if portfolio_as_of > context_as_of:
        raise DossierError("review-context-valid.json.portfolio: future point-in-time snapshot")
    holdings = portfolio.get("holdings")
    if not isinstance(holdings, list) or not all(isinstance(item, dict) for item in holdings):
        raise DossierError("review-context-valid.json.portfolio.holdings: invalid")
    for index, holding in enumerate(holdings):
        source_as_of = _timestamp(
            holding.get("source_as_of"),
            f"review-context-valid.json.portfolio.holdings[{index}].source_as_of",
        )
        if source_as_of > portfolio_as_of:
            raise DossierError(
                f"review-context-valid.json.portfolio.holdings[{index}]: "
                "source is later than portfolio snapshot"
            )

    freshness = context.get("freshness")
    if not isinstance(freshness, dict):
        raise DossierError("review-context-valid.json: missing freshness state")
    freshness_items = freshness.get("items")
    if (
        freshness.get("policy_id") != "review-freshness-v1"
        or not isinstance(freshness_items, list)
        or not all(isinstance(item, dict) for item in freshness_items)
    ):
        raise DossierError("review-context-valid.json.freshness.items: invalid")
    freshness_names = [item.get("input_name") for item in freshness_items]
    if freshness_names != list(REVIEW_FRESHNESS_SOURCE_TYPES):
        raise DossierError(
            "review-context-valid.json.freshness.items: required coverage/order drifted"
        )
    for index, item in enumerate(freshness_items):
        label = f"review-context-valid.json.freshness.items[{index}]"
        input_name = item.get("input_name")
        source_type = REVIEW_FRESHNESS_SOURCE_TYPES[input_name]
        source_rows = evidence_by_source_type.get(source_type, [])
        if len(source_rows) > 1:
            raise DossierError(f"{label}: freshness source is ambiguous")
        maximum_age = item.get("maximum_age_seconds")
        if not isinstance(maximum_age, int) or isinstance(maximum_age, bool) or maximum_age < 1:
            raise DossierError(f"{label}.maximum_age_seconds: invalid")
        if not source_rows:
            expected_state = "MISSING"
            expected_age: int | None = None
        else:
            observed_at = _timestamp(
                source_rows[0].get("observed_at"),
                f"{label}.source.observed_at",
            )
            if observed_at > context_as_of:
                expected_state = "FUTURE_DATED"
                expected_age = None
            else:
                expected_age = int((context_as_of - observed_at).total_seconds())
                expected_state = "FRESH" if expected_age <= maximum_age else "STALE"
        if item.get("state") != expected_state or item.get("age_seconds") != expected_age:
            raise DossierError(
                f"{label}: freshness state/age disagrees with frozen source timestamps"
            )
    item_states = {item.get("state") for item in freshness_items}
    missing_data = context.get("missing_data")
    if not isinstance(missing_data, list) or not all(
        isinstance(item, dict) for item in missing_data
    ):
        raise DossierError("review-context-valid.json.missing_data: invalid")
    has_blocking_gap = any(item.get("severity") == "blocking" for item in missing_data)
    if "FUTURE_DATED" in item_states:
        derived_context_state = "BLOCKED_INVALID"
        expected_overall = "INCOMPLETE"
    elif "MISSING" in item_states or has_blocking_gap:
        derived_context_state = "BLOCKED_INCOMPLETE"
        expected_overall = "INCOMPLETE"
    elif "STALE" in item_states:
        derived_context_state = "BLOCKED_STALE"
        expected_overall = "STALE"
    else:
        derived_context_state = "COMPLETE_FRESH"
        expected_overall = "FRESH"
    if freshness.get("overall_state") != expected_overall:
        raise DossierError("review-context-valid.json: overall freshness disagrees with items")
    if eligibility.get("context_state") != derived_context_state:
        raise DossierError(
            "review-eligibility-valid.json.context_state: disagrees with frozen context"
        )

    role_order = (
        "evidence_claims",
        "valuation_scenarios",
        "thesis_adversary",
        "portfolio_risk_fit",
        "implementation_liquidity_tax",
    )
    roles = [item.get("role") for item in assessments]
    if roles != list(role_order):
        raise DossierError("reviewer-assessments-blind.json: mandatory role order/set drifted")
    context_digest = context.get("context_sha256")
    decided_at = _timestamp(
        eligibility.get("decided_at"), "review-eligibility-valid.json.decided_at"
    )
    expected_controls = {
        "blind_first_pass": True,
        "other_reviewer_output_visible": False,
        "database_access": False,
        "network_access": False,
        "numeric_authority": False,
        "eligibility_authority": False,
        "non_executable": True,
    }
    expected_refs: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    finding_summary = {
        "open_info": 0,
        "open_low": 0,
        "open_medium": 0,
        "open_high": 0,
        "open_critical": 0,
        "accepted_risk_count": 0,
        "resolved_count": 0,
        "abstention_count": 0,
    }
    any_fail = False
    resolution_ids: set[str] = set()
    for index, assessment in enumerate(assessments):
        label = f"reviewer-assessments-blind.json[{index}]"
        role = assessment.get("role")
        if (
            assessment.get("investment_case_id") != eligibility.get("investment_case_id")
            or assessment.get("review_cycle_id") != context.get("review_cycle_id")
            or assessment.get("report_ref") != expected_report_ref
            or assessment.get("report_candidate_sha256") != candidate_hash
            or assessment.get("context_id") != context.get("context_id")
            or assessment.get("context_sha256") != context_digest
        ):
            raise DossierError(f"{label}: report/context/case identity does not resolve")
        identity_spec = REVIEW_ROLE_IDENTITY_SPECS.get(role)
        if identity_spec is None:
            raise DossierError(f"{label}.role: has no approved reviewer identity")
        agent_id, agent_hash, prompt_id, prompt_hash = identity_spec
        expected_reviewer = {
            "agent_ref": {
                "id": agent_id,
                "version": "1.0.0",
                "sha256": agent_hash,
            },
            "model_ref": REVIEW_MODEL_REF,
            "prompt_ref": {
                "id": prompt_id,
                "version": "1.0.0",
                "sha256": prompt_hash,
            },
            "rubric_ref": REVIEW_RUBRIC_REF,
        }
        if assessment.get("reviewer") != expected_reviewer:
            raise DossierError(
                f"{label}.reviewer: does not resolve the approved role identity bundle"
            )
        if assessment.get("controls") != expected_controls:
            raise DossierError(f"{label}: blind first-pass controls are unsafe")
        submitted_at = _timestamp(assessment.get("submitted_at"), f"{label}.submitted_at")
        if not context_generated_at <= submitted_at <= decided_at:
            raise DossierError(
                f"{label}: assessment submission is outside context/decision chronology"
            )
        verdict = assessment.get("verdict")
        any_fail = any_fail or verdict == "FAIL"
        if verdict == "ABSTAIN":
            finding_summary["abstention_count"] += 1
        expected_refs.append(
            {
                "assessment_id": assessment.get("assessment_id"),
                "assessment_sha256": _canonical_hash_identity(assessment, label),
                "role": assessment.get("role"),
                "verdict": verdict,
            }
        )
        findings = assessment.get("findings")
        if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
            raise DossierError(f"{label}.findings: invalid")
        for finding_index, finding in enumerate(findings):
            finding_label = f"{label}.findings[{finding_index}]"
            finding_id = finding.get("finding_id")
            if not isinstance(finding_id, str) or finding_id in finding_ids:
                raise DossierError(f"{finding_label}.finding_id: missing or duplicate")
            finding_ids.add(finding_id)
            claim_ids = finding.get("claim_ids")
            evidence_ids = finding.get("evidence_ids")
            if (
                not isinstance(claim_ids, list)
                or not claim_ids
                or not all(isinstance(item, str) for item in claim_ids)
                or not set(claim_ids) <= claim_evidence_by_id.keys()
                or not isinstance(evidence_ids, list)
                or not evidence_ids
                or not all(
                    isinstance(item, int) and not isinstance(item, bool) for item in evidence_ids
                )
            ):
                raise DossierError(
                    f"{finding_label}: claim/evidence references do not resolve frozen context"
                )
            claim_evidence = set().union(
                *(claim_evidence_by_id[claim_id] for claim_id in claim_ids)
            )
            if not set(evidence_ids) <= claim_evidence:
                raise DossierError(
                    f"{finding_label}.evidence_ids: do not resolve referenced context claims"
                )
            status = finding.get("status")
            resolution_ref = finding.get("resolution_ref")
            if status == "OPEN":
                if resolution_ref is not None:
                    raise DossierError(f"{finding_label}: OPEN finding has a resolution")
                severity = finding.get("severity")
                summary_field = f"open_{severity}"
                if summary_field not in finding_summary:
                    raise DossierError(f"{finding_label}.severity: invalid")
                finding_summary[summary_field] += 1
            elif status == "ACCEPTED_RISK":
                finding_summary["accepted_risk_count"] += 1
            elif status == "RESOLVED":
                finding_summary["resolved_count"] += 1
            else:
                raise DossierError(f"{finding_label}.status: invalid")
            if status in {"ACCEPTED_RISK", "RESOLVED"}:
                expected_resolution = GOLDEN_REVIEW_RESOLUTIONS.get(finding_id)
                resolution_projection = {
                    "code": finding.get("code"),
                    "severity": finding.get("severity"),
                    "status": status,
                    "claim_ids": claim_ids,
                    "evidence_ids": evidence_ids,
                    "resolution_ref": resolution_ref,
                }
                if expected_resolution is None or resolution_projection != expected_resolution:
                    raise DossierError(
                        f"{finding_label}.resolution_ref: is not an approved immutable "
                        "James/governance resolution"
                    )
                if not isinstance(resolution_ref, dict):
                    raise DossierError(f"{finding_label}.resolution_ref: invalid")
                resolution_id = resolution_ref.get("resolution_id")
                if not isinstance(resolution_id, str) or resolution_id in resolution_ids:
                    raise DossierError(
                        f"{finding_label}.resolution_ref.resolution_id: missing or duplicate"
                    )
                resolution_ids.add(resolution_id)
                resolved_at = _timestamp(
                    resolution_ref.get("resolved_at"),
                    f"{finding_label}.resolution_ref.resolved_at",
                )
                if resolved_at > submitted_at or resolved_at > decided_at:
                    raise DossierError(
                        f"{finding_label}.resolution_ref: post-dates immutable assessment"
                    )

    if eligibility.get("assessment_refs") != expected_refs:
        raise DossierError(
            "review-eligibility-valid.json.assessment_refs: do not resolve exact assessments"
        )
    if eligibility.get("finding_summary") != finding_summary:
        raise DossierError(
            "review-eligibility-valid.json.finding_summary: disagrees with assessments"
        )
    if derived_context_state != "COMPLETE_FRESH" or finding_summary["abstention_count"] > 0:
        expected_decision = "BLOCKED"
    elif any_fail or finding_summary["open_critical"] > 0:
        expected_decision = "FAIL"
    elif finding_summary["open_high"] > 0:
        expected_decision = "BLOCKED"
    else:
        expected_decision = "PAPER_ELIGIBLE"
    if eligibility.get("decision") != expected_decision:
        raise DossierError(
            "review-eligibility-valid.json.decision: disagrees with deterministic synthesis"
        )
    if expected_decision == "PAPER_ELIGIBLE" and set(eligibility.get("reason_codes", [])) != {
        "ALL_MANDATORY_REVIEWS_COMPLETE",
        "NO_OPEN_HIGH_OR_CRITICAL_FINDINGS",
    }:
        raise DossierError("review-eligibility-valid.json.reason_codes: eligibility proof drifted")

    eligibility_digest = _canonical_hash_identity(eligibility, "review-eligibility-valid.json")
    for filename, document in fixtures.items():
        if not isinstance(document, dict):
            continue
        lineage = document.get("lineage")
        if not isinstance(lineage, dict):
            continue
        research = lineage.get("research")
        review = lineage.get("review")
        if not isinstance(research, dict) or not isinstance(review, dict):
            raise DossierError(f"{filename}: incomplete research/review lineage")
        if lineage.get("investment_case_id") != eligibility.get("investment_case_id"):
            raise DossierError(
                f"{filename}: lineage investment_case_id does not resolve eligibility case"
            )
        if (
            research.get("thesis_id") != report.get("thesis_id")
            or research.get("report_ref") != expected_report_ref
            or research.get("report_candidate_sha256") != candidate_hash
        ):
            raise DossierError(f"{filename}: research lineage does not resolve report")
        expected_review = {
            "context_id": context.get("context_id"),
            "context_sha256": context_digest,
            "review_cycle_id": context.get("review_cycle_id"),
            "eligibility_decision_id": eligibility.get("eligibility_decision_id"),
            "eligibility_sha256": eligibility_digest,
        }
        if review != expected_review:
            raise DossierError(f"{filename}: review lineage does not resolve eligibility")


def _validate_accounting_semantics(fixtures: dict[str, Any]) -> None:
    ledger = fixtures.get("branch-ledger-valid.json")
    if not isinstance(ledger, dict):
        raise DossierError("branch-ledger-valid.json: fixture must be an object")
    for branch_index, branch in enumerate(ledger.get("branches", [])):
        for event_index, event in enumerate(branch.get("events", [])):
            label = "branch-ledger-valid.json" f".branches[{branch_index}].events[{event_index}]"
            debit_sum = sum(
                (
                    _decimal(leg.get("amount"), f"{label}.legs.amount")
                    for leg in event.get("legs", [])
                    if leg.get("direction") == "DEBIT"
                ),
                Decimal(0),
            )
            credit_sum = sum(
                (
                    _decimal(leg.get("amount"), f"{label}.legs.amount")
                    for leg in event.get("legs", [])
                    if leg.get("direction") == "CREDIT"
                ),
                Decimal(0),
            )
            declared_debit = _decimal(event.get("debit_total"), f"{label}.debit_total")
            declared_credit = _decimal(event.get("credit_total"), f"{label}.credit_total")
            _require_decimal_equal(declared_debit, debit_sum, f"{label}.debit_total")
            _require_decimal_equal(declared_credit, credit_sum, f"{label}.credit_total")
            balanced = debit_sum == credit_sum
            if event.get("balanced") is not balanced or not balanced:
                raise DossierError(f"{label}: ledger event debits do not equal credits")

    nav = fixtures.get("branch-nav-valid.json")
    if not isinstance(nav, dict):
        raise DossierError("branch-nav-valid.json: fixture must be an object")
    for branch_index, branch in enumerate(nav.get("branches", [])):
        for entry_index, entry in enumerate(branch.get("entries", [])):
            label = f"branch-nav-valid.json.branches[{branch_index}].entries[{entry_index}]"
            expected_nav = (
                _decimal(entry.get("cash_aud"), f"{label}.cash_aud")
                + _decimal(entry.get("positions_aud"), f"{label}.positions_aud")
                + _decimal(entry.get("receivables_aud"), f"{label}.receivables_aud")
                - _decimal(entry.get("payables_aud"), f"{label}.payables_aud")
                - _decimal(entry.get("accrued_fees_aud"), f"{label}.accrued_fees_aud")
                - _decimal(
                    entry.get("realized_tax_payable_aud"),
                    f"{label}.realized_tax_payable_aud",
                )
                - _decimal(
                    entry.get("deferred_tax_liability_aud"),
                    f"{label}.deferred_tax_liability_aud",
                )
            )
            _require_decimal_equal(
                _decimal(entry.get("ending_nav_aud"), f"{label}.ending_nav_aud"),
                expected_nav,
                f"{label}.ending_nav_aud",
            )

    fill = fixtures.get("paper-fill-valid.json")
    if isinstance(fill, dict):
        quantity = _decimal(fill.get("filled_quantity"), "paper-fill-valid.json.filled_quantity")
        fill_price = _decimal(fill.get("fill_price_aud"), "paper-fill-valid.json.fill_price_aud")
        gross = _decimal(
            fill.get("gross_consideration_aud"),
            "paper-fill-valid.json.gross_consideration_aud",
        )
        fee = _decimal(fill.get("fee_aud"), "paper-fill-valid.json.fee_aud")
        _require_decimal_equal(
            gross,
            quantity * fill_price,
            "paper-fill-valid.json.gross_consideration_aud",
        )
        signed_cash = -(gross + fee) if fill.get("side") == "BUY" else gross - fee
        _require_decimal_equal(
            _decimal(
                fill.get("total_cash_effect_aud"),
                "paper-fill-valid.json.total_cash_effect_aud",
            ),
            signed_cash,
            "paper-fill-valid.json.total_cash_effect_aud",
        )
        implementation_cost = sum(
            (
                _decimal(fill.get(field), f"paper-fill-valid.json.{field}")
                for field in (
                    "spread_cost_aud",
                    "slippage_cost_aud",
                    "impact_cost_aud",
                )
            ),
            Decimal(0),
        )
        price_impact = (
            abs(
                fill_price
                - _decimal(
                    fill.get("reference_price_aud"),
                    "paper-fill-valid.json.reference_price_aud",
                )
            )
            * quantity
        )
        _require_decimal_equal(
            implementation_cost,
            price_impact,
            "paper-fill-valid.json implementation-cost components",
        )


def _object_payload_sha256(value: dict[str, Any], excluded_field: str, label: str) -> str:
    if excluded_field not in value:
        raise DossierError(f"{label}: missing {excluded_field}")
    projected = {key: item for key, item in value.items() if key != excluded_field}
    canonical = _canonical_fixture_json(projected, label)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_classification_snapshot_ref(
    reference: Any,
    snapshot: dict[str, Any],
    label: str,
) -> None:
    if not isinstance(reference, dict):
        raise DossierError(f"{label}: missing classification_snapshot_ref")
    expected = {
        "contract_name": "security-classification-snapshot-v1",
        "artifact_id": snapshot.get("classification_snapshot_id"),
        "schema_version": snapshot.get("schema_version"),
        "sha256": _canonical_hash_identity(snapshot, "security-classification-snapshot-valid.json"),
        "created_at": snapshot.get("created_at"),
    }
    for field, expected_value in expected.items():
        if reference.get(field) != expected_value:
            raise DossierError(
                f"{label}.{field}: classification snapshot reference does not resolve "
                f"to the frozen snapshot"
            )


def _require_versioned_policy_ref(
    reference: Any,
    policy: dict[str, Any],
    *,
    identifier_field: str,
    version_field: str,
    label: str,
) -> None:
    if not isinstance(reference, dict):
        raise DossierError(f"{label}: missing policy reference")
    expected = {
        "id": policy.get(identifier_field),
        "version": policy.get(version_field),
        "sha256": _canonical_hash_identity(policy, label),
    }
    for field, expected_value in expected.items():
        if reference.get(field) != expected_value:
            raise DossierError(f"{label}.{field}: policy reference does not resolve")


def _require_ordered_unique(
    items: Any,
    identifier_field: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise DossierError(f"{label}: expected an array")
    identifiers = [item.get(identifier_field) if isinstance(item, dict) else None for item in items]
    if any(not isinstance(identifier, str) for identifier in identifiers):
        raise DossierError(f"{label}: every item requires {identifier_field}")
    if identifiers != sorted(identifiers):
        raise DossierError(f"{label}: items must be sorted by {identifier_field}")
    if len(identifiers) != len(set(identifiers)):
        raise DossierError(f"{label}: duplicate {identifier_field}")
    return {
        identifier: item
        for identifier, item in zip(identifiers, items, strict=True)
        if isinstance(identifier, str) and isinstance(item, dict)
    }


def _require_effective_interval(
    interval: Any,
    moment: datetime,
    label: str,
) -> None:
    if not isinstance(interval, dict):
        raise DossierError(f"{label}: missing effective interval")
    effective_from = _timestamp(interval.get("effective_from"), f"{label}.effective_from")
    effective_to_raw = interval.get("effective_to")
    effective_to = (
        _timestamp(effective_to_raw, f"{label}.effective_to")
        if effective_to_raw is not None
        else None
    )
    if effective_to is not None and effective_to <= effective_from:
        raise DossierError(f"{label}: effective interval is empty or reversed")
    if moment < effective_from or (effective_to is not None and moment >= effective_to):
        raise DossierError(f"{label}: classification is not effective at decision time")


def _validate_tick_rule(
    asset: dict[str, Any],
    moment: datetime,
    label: str,
) -> None:
    tick_rule = asset.get("tick_rule")
    if not isinstance(tick_rule, dict):
        raise DossierError(f"{label}.tick_rule: missing governed tick rule")
    _require_effective_interval(
        tick_rule.get("effective_interval"),
        moment,
        f"{label}.tick_rule.effective_interval",
    )
    bands = tick_rule.get("bands")
    if not isinstance(bands, list) or not bands:
        raise DossierError(f"{label}.tick_rule.bands: expected a non-empty array")
    sequences = [
        _integer(band.get("band_sequence"), f"{label}.tick_rule.bands.band_sequence")
        if isinstance(band, dict)
        else -1
        for band in bands
    ]
    if sequences != list(range(1, len(bands) + 1)):
        raise DossierError(f"{label}.tick_rule.bands: sequence is not contiguous")
    prior_upper: Decimal | None = None
    for index, band in enumerate(bands):
        if not isinstance(band, dict):
            raise DossierError(f"{label}.tick_rule.bands[{index}]: expected an object")
        band_label = f"{label}.tick_rule.bands[{index}]"
        lower = _decimal(band.get("lower_bound_aud"), f"{band_label}.lower_bound_aud")
        upper_raw = band.get("upper_bound_aud")
        upper = (
            _decimal(upper_raw, f"{band_label}.upper_bound_aud") if upper_raw is not None else None
        )
        tick = _decimal(band.get("tick_size_aud"), f"{band_label}.tick_size_aud")
        if lower < 0 or tick <= 0:
            raise DossierError(f"{band_label}: lower bound and tick must be non-negative")
        if band.get("lower_bound_inclusive") is not True:
            raise DossierError(f"{band_label}: lower bound must be inclusive")
        if band.get("upper_bound_exclusive") is not True:
            raise DossierError(f"{band_label}: upper bound must be exclusive")
        if index == 0 and lower != 0:
            raise DossierError(f"{band_label}: first tick band must start at zero")
        if index > 0 and prior_upper != lower:
            raise DossierError(f"{band_label}: tick bands contain a gap or overlap")
        if upper is None:
            if index != len(bands) - 1:
                raise DossierError(f"{band_label}: only the final tick band may be open-ended")
        elif upper <= lower:
            raise DossierError(f"{band_label}: upper bound must exceed lower bound")
        prior_upper = upper


def _tick_size_for_price(
    asset: dict[str, Any],
    price: Decimal,
    label: str,
) -> Decimal:
    tick_rule = asset.get("tick_rule")
    bands = tick_rule.get("bands") if isinstance(tick_rule, dict) else None
    if not isinstance(bands, list):
        raise DossierError(f"{label}: no tick bands available")
    matches: list[Decimal] = []
    for index, band in enumerate(bands):
        if not isinstance(band, dict):
            continue
        lower = _decimal(
            band.get("lower_bound_aud"), f"{label}.tick_rule.bands[{index}].lower_bound_aud"
        )
        upper_raw = band.get("upper_bound_aud")
        upper = (
            _decimal(
                upper_raw,
                f"{label}.tick_rule.bands[{index}].upper_bound_aud",
            )
            if upper_raw is not None
            else None
        )
        if price >= lower and (upper is None or price < upper):
            matches.append(
                _decimal(
                    band.get("tick_size_aud"),
                    f"{label}.tick_rule.bands[{index}].tick_size_aud",
                )
            )
    if len(matches) != 1:
        raise DossierError(f"{label}: price does not resolve to exactly one effective tick band")
    return matches[0]


def _validate_classification_snapshot(
    snapshot: dict[str, Any],
    decision_at: datetime,
) -> dict[str, dict[str, Any]]:
    label = "security-classification-snapshot-valid.json"
    if snapshot.get("status") != "COMPLETE":
        raise DossierError(f"{label}: BUILT/SIZED chain requires a COMPLETE snapshot")
    data_as_of = _timestamp(snapshot.get("data_as_of"), f"{label}.data_as_of")
    knowledge_cutoff = _timestamp(snapshot.get("knowledge_cutoff"), f"{label}.knowledge_cutoff")
    created_at = _timestamp(snapshot.get("created_at"), f"{label}.created_at")
    if not data_as_of <= knowledge_cutoff <= created_at:
        raise DossierError(f"{label}: data/cutoff/creation chronology is invalid")
    assets = _require_ordered_unique(snapshot.get("assets"), "asset_id", f"{label}.assets")
    for asset_id, asset in assets.items():
        asset_label = f"{label}.assets[{asset_id}]"
        themes = asset.get("theme_ids")
        if not isinstance(themes, list) or any(not isinstance(theme, str) for theme in themes):
            raise DossierError(f"{asset_label}.theme_ids: expected known theme membership")
        if themes != sorted(themes) or len(themes) != len(set(themes)):
            raise DossierError(f"{asset_label}.theme_ids: must be sorted and unique")
        _require_effective_interval(
            asset.get("effective_interval"),
            decision_at,
            f"{asset_label}.effective_interval",
        )
        _validate_tick_rule(asset, decision_at, asset_label)
        provenance = asset.get("provenance")
        if not isinstance(provenance, dict) or not provenance:
            raise DossierError(f"{asset_label}.provenance: missing source evidence")
        for source_name, source in provenance.items():
            if not isinstance(source, dict):
                raise DossierError(f"{asset_label}.provenance.{source_name}: invalid source")
            source_label = f"{asset_label}.provenance.{source_name}"
            observed = _timestamp(source.get("observed_at"), f"{source_label}.observed_at")
            published = _timestamp(source.get("published_at"), f"{source_label}.published_at")
            available = _timestamp(source.get("available_at"), f"{source_label}.available_at")
            if not observed <= published <= available <= knowledge_cutoff:
                raise DossierError(
                    f"{source_label}: provenance is not point-in-time available by cutoff"
                )
    return assets


def _require_classification_identity(
    classified: dict[str, Any],
    consumer: dict[str, Any],
    label: str,
) -> None:
    for field in (
        "asset_id",
        "security_id",
        "issuer_id",
        "corporate_group_id",
        "sector_id",
        "theme_ids",
        "board_lot_quantity",
    ):
        if consumer.get(field) != classified.get(field):
            suffix = (
                " (whole board lot/classification mismatch)"
                if field == "board_lot_quantity"
                else ""
            )
            raise DossierError(
                f"{label}.{field}: value does not match frozen classification{suffix}"
            )
    tick_rule = classified.get("tick_rule")
    provenance = classified.get("provenance")
    trading_source = provenance.get("trading_rule") if isinstance(provenance, dict) else None
    expected_tick_ref = {
        "id": tick_rule.get("tick_rule_id") if isinstance(tick_rule, dict) else None,
        "version": tick_rule.get("tick_rule_version") if isinstance(tick_rule, dict) else None,
        "sha256": (
            trading_source.get("record_sha256") if isinstance(trading_source, dict) else None
        ),
    }
    actual_tick_ref = consumer.get("tick_rule_ref")
    if not isinstance(actual_tick_ref, dict) or any(
        actual_tick_ref.get(field) != value for field, value in expected_tick_ref.items()
    ):
        raise DossierError(f"{label}.tick_rule_ref: does not match governed trading rule")


def _aggregate_classification_weights(
    rows: Iterable[tuple[dict[str, Any], Decimal]],
    classification_field: str,
) -> dict[str, Decimal]:
    aggregate: dict[str, Decimal] = {}
    for row, weight in rows:
        raw_identifiers = row.get(classification_field)
        identifiers = raw_identifiers if classification_field == "theme_ids" else [raw_identifiers]
        if not isinstance(identifiers, list):
            raise DossierError(f"{classification_field}: expected classification identifiers")
        for identifier in identifiers:
            if not isinstance(identifier, str):
                raise DossierError(f"{classification_field}: invalid classification identifier")
            aggregate[identifier] = aggregate.get(identifier, Decimal(0)) + weight
    return aggregate


def _require_exposure_summary(
    actual: Any,
    expected: dict[str, Decimal],
    *,
    weight_field: str,
    label: str,
) -> None:
    if not isinstance(actual, list):
        raise DossierError(f"{label}: expected an exposure array")
    actual_ids = [row.get("classification_id") if isinstance(row, dict) else None for row in actual]
    expected_ids = sorted(expected)
    if actual_ids != expected_ids:
        raise DossierError(
            f"{label}: exposure classifications do not match deterministic aggregation"
        )
    for row in actual:
        if not isinstance(row, dict):
            raise DossierError(f"{label}: exposure row must be an object")
        identifier = row.get("classification_id")
        _require_decimal_equal(
            _decimal(row.get(weight_field), f"{label}.{identifier}.{weight_field}"),
            expected[identifier],
            f"{label}.{identifier}.{weight_field}",
        )


def _validate_portfolio_semantics(fixtures: dict[str, Any]) -> None:
    proposal = fixtures.get("portfolio-proposal-valid.json")
    classification = fixtures.get("security-classification-snapshot-valid.json")
    construction_policy = fixtures.get("portfolio-construction-policy-valid.json")
    risk_policy = fixtures.get("risk-policy-valid.json")
    sizing_policy = fixtures.get("sizing-policy-valid.json")
    if not all(
        isinstance(document, dict)
        for document in (
            proposal,
            classification,
            construction_policy,
            risk_policy,
            sizing_policy,
        )
    ):
        raise DossierError(
            "portfolio semantics require proposal, classification, construction, "
            "risk, and sizing-policy fixtures"
        )
    assert isinstance(proposal, dict)
    assert isinstance(classification, dict)
    assert isinstance(construction_policy, dict)
    assert isinstance(risk_policy, dict)
    assert isinstance(sizing_policy, dict)

    cap_waterfall = construction_policy.get("cap_waterfall")
    construction_order = (
        cap_waterfall.get("ordered_caps") if isinstance(cap_waterfall, dict) else None
    )
    if construction_order != list(CONSTRUCTION_CAP_ORDER):
        raise DossierError(
            "portfolio-construction-policy-valid.json: ordered cap waterfall is not "
            "the institutional fail-closed sequence"
        )
    if sizing_policy.get("constraint_sequence") != list(SIZING_CONSTRAINT_ORDER):
        raise DossierError(
            "sizing-policy-valid.json: constraint sequence is not the institutional "
            "fail-closed sequence"
        )

    built = proposal.get("status") == "BUILT"
    targets = proposal.get("targets")
    if not isinstance(targets, list):
        raise DossierError("portfolio-proposal-valid.json.targets: expected an array")
    if proposal.get("eligible_for_sizing") is not built:
        raise DossierError("portfolio-proposal-valid.json: status and eligible_for_sizing disagree")
    if built != bool(targets):
        raise DossierError(
            "portfolio-proposal-valid.json: BUILT must contain targets and rejection must not"
        )

    target_by_asset: dict[str, dict[str, Any]] = {}
    if built:
        proposal_data_as_of = _timestamp(
            proposal.get("data_as_of"), "portfolio-proposal-valid.json.data_as_of"
        )
        proposal_cutoff = _timestamp(
            proposal.get("knowledge_cutoff"),
            "portfolio-proposal-valid.json.knowledge_cutoff",
        )
        proposal_decision = _timestamp(
            proposal.get("decision_at"), "portfolio-proposal-valid.json.decision_at"
        )
        proposal_created = _timestamp(
            proposal.get("created_at"), "portfolio-proposal-valid.json.created_at"
        )
        if not proposal_data_as_of <= proposal_cutoff <= proposal_decision <= proposal_created:
            raise DossierError(
                "portfolio-proposal-valid.json: data/cutoff/decision/creation chronology "
                "is invalid"
            )
        _require_classification_snapshot_ref(
            proposal.get("classification_snapshot_ref"),
            classification,
            "portfolio-proposal-valid.json.classification_snapshot_ref",
        )
        classification_cutoff = _timestamp(
            classification.get("knowledge_cutoff"),
            "security-classification-snapshot-valid.json.knowledge_cutoff",
        )
        classification_created = _timestamp(
            classification.get("created_at"),
            "security-classification-snapshot-valid.json.created_at",
        )
        freshness = construction_policy.get("classification_freshness")
        if not isinstance(freshness, dict):
            raise DossierError(
                "portfolio-construction-policy-valid.json: missing classification freshness"
            )
        maximum_age = freshness.get("maximum_age_seconds")
        if isinstance(maximum_age, bool) or not isinstance(maximum_age, int):
            raise DossierError(
                "portfolio-construction-policy-valid.json: invalid classification maximum age"
            )
        classification_age = proposal_cutoff - classification_cutoff
        if (
            classification_age < timedelta(0)
            or classification_age > timedelta(seconds=maximum_age)
            or classification_created > proposal_cutoff
        ):
            raise DossierError(
                "portfolio-proposal-valid.json: classification snapshot is stale or "
                "was unavailable by cutoff"
            )
        if freshness.get("require_effective_at_decision") is not True:
            raise DossierError(
                "portfolio-construction-policy-valid.json: effective classification "
                "must be mandatory"
            )
        if freshness.get("require_snapshot_available_by_cutoff") is not True:
            raise DossierError(
                "portfolio-construction-policy-valid.json: point-in-time availability "
                "must be mandatory"
            )

        classified_assets = _validate_classification_snapshot(classification, proposal_decision)
        _require_versioned_policy_ref(
            proposal.get("construction_policy_ref"),
            construction_policy,
            identifier_field="policy_id",
            version_field="policy_version",
            label="portfolio-proposal-valid.json.construction_policy_ref",
        )
        _require_versioned_policy_ref(
            proposal.get("risk_policy_ref"),
            risk_policy,
            identifier_field="policy_id",
            version_field="policy_version",
            label="portfolio-proposal-valid.json.risk_policy_ref",
        )

        manifest = proposal.get("input_manifest")
        if not isinstance(manifest, list):
            raise DossierError("portfolio-proposal-valid.json.input_manifest: expected an array")
        classification_inputs = [
            source
            for source in manifest
            if isinstance(source, dict)
            and source.get("source") == "security-classification-snapshot"
        ]
        if len(classification_inputs) != 1:
            raise DossierError(
                "portfolio-proposal-valid.json.input_manifest: requires exactly one "
                "classification snapshot observation"
            )
        classification_input = classification_inputs[0]
        classification_digest = _canonical_hash_identity(
            classification, "security-classification-snapshot-valid.json"
        )
        if (
            classification_input.get("record_id")
            != classification.get("classification_snapshot_id")
            or classification_input.get("content_sha256") != classification_digest
            or _timestamp(
                classification_input.get("available_at"),
                "portfolio-proposal-valid.json.input_manifest.classification.available_at",
            )
            > proposal_cutoff
        ):
            raise DossierError(
                "portfolio-proposal-valid.json.input_manifest: classification lineage "
                "does not resolve or was unavailable"
            )
        classification_sources = [
            source
            for source in proposal.get("source_hashes", [])
            if isinstance(source, dict)
            and source.get("source") == "security-classification-snapshot"
        ]
        if (
            len(classification_sources) != 1
            or classification_sources[0].get("sha256") != classification_digest
        ):
            raise DossierError(
                "portfolio-proposal-valid.json.source_hashes: classification digest mismatch"
            )

        candidate_by_asset = _require_ordered_unique(
            proposal.get("candidate_inputs"),
            "asset_id",
            "portfolio-proposal-valid.json.candidate_inputs",
        )
        target_by_asset = _require_ordered_unique(
            targets,
            "asset_id",
            "portfolio-proposal-valid.json.targets",
        )
        for asset_id, candidate in candidate_by_asset.items():
            classified = classified_assets.get(asset_id)
            if classified is None:
                raise DossierError(
                    f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}]: "
                    "classification is missing or ambiguous"
                )
            if (
                classified.get("classification_status") != "COMPLETE"
                or classified.get("admissible_for_construction") is not True
                or candidate.get("classification_status") != "COMPLETE"
                or candidate.get("admissible_for_construction") is not True
                or candidate.get("input_state") != "COMPLETE"
            ):
                raise DossierError(
                    f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}]: "
                    "classification/input is not complete and admissible"
                )
            _require_classification_identity(
                classified,
                candidate,
                f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}]",
            )
            reference_price = _decimal(
                candidate.get("reference_price_aud"),
                f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}].reference_price_aud",
            )
            expected_tick = _tick_size_for_price(
                classified,
                reference_price,
                f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}]",
            )
            _require_decimal_equal(
                _decimal(
                    candidate.get("tick_size_aud"),
                    f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}].tick_size_aud",
                ),
                expected_tick,
                f"portfolio-proposal-valid.json.candidate_inputs[{asset_id}].tick_size_aud",
            )

        target_weights: list[Decimal] = []
        current_weights: list[Decimal] = []
        expected_losses: list[Decimal] = []
        target_weight_rows: list[tuple[dict[str, Any], Decimal]] = []
        for asset_id, target in target_by_asset.items():
            label = f"portfolio-proposal-valid.json.targets[{asset_id}]"
            candidate = candidate_by_asset.get(asset_id)
            classified = classified_assets.get(asset_id)
            if candidate is None or classified is None:
                raise DossierError(f"{label}: target lacks a unique classified candidate")
            _require_classification_identity(classified, target, label)
            for field in ("tick_size_aud",):
                if target.get(field) != candidate.get(field):
                    raise DossierError(f"{label}.{field}: target differs from candidate input")
            if target.get("construction_status") not in {"INCLUDED", "REDUCED_BY_CAP"}:
                raise DossierError(f"{label}: non-constructible target in BUILT proposal")
            checks = target.get("cap_checks", [])
            if not isinstance(checks, list):
                raise DossierError(f"{label}.cap_checks: expected an array")
            sequences = [check.get("sequence") for check in checks]
            codes = [check.get("cap_code") for check in checks]
            if sequences != list(range(1, len(CONSTRUCTION_CAP_ORDER) + 1)):
                raise DossierError(f"{label}: cap-check sequence is not exact and contiguous")
            if codes != list(CONSTRUCTION_CAP_ORDER):
                raise DossierError(f"{label}: cap-check codes do not match policy order exactly")
            for check in checks:
                code = check.get("cap_code")
                if code == "CLASSIFICATION":
                    source_ref = check.get("source_ref")
                    if (
                        check.get("check_type") != "BOOLEAN_PRECONDITION"
                        or check.get("passed") is not True
                        or not isinstance(source_ref, dict)
                        or source_ref.get("id") != classification.get("classification_snapshot_id")
                        or source_ref.get("sha256") != classification_digest
                    ):
                        raise DossierError(f"{label}: classification precondition did not pass")
                    continue
                if check.get("check_type") != "WEIGHT_CAP" or check.get("action") not in {
                    "UNCHANGED",
                    "REDUCED",
                }:
                    raise DossierError(f"{label}: fail-open or mistyped cap check {code!r}")
                before = _decimal(
                    check.get("before_weight"), f"{label}.cap_checks[{code}].before_weight"
                )
                after = _decimal(
                    check.get("after_weight"), f"{label}.cap_checks[{code}].after_weight"
                )
                if after > before:
                    raise DossierError(f"{label}: later cap {code!r} increased target weight")
                if check.get("action") == "UNCHANGED" and after != before:
                    raise DossierError(f"{label}: UNCHANGED cap {code!r} changed weight")
                if check.get("action") == "REDUCED" and after >= before:
                    raise DossierError(f"{label}: REDUCED cap {code!r} did not reduce weight")
            current = _decimal(target.get("current_weight"), f"{label}.current_weight")
            target_weight = _decimal(target.get("target_weight"), f"{label}.target_weight")
            stop_distance = _decimal(
                target.get("effective_stop_distance_fraction"),
                f"{label}.effective_stop_distance_fraction",
            )
            risk_budget = _decimal(
                target.get("risk_budget_fraction"), f"{label}.risk_budget_fraction"
            )
            uncapped = _decimal(
                target.get("uncapped_target_weight"), f"{label}.uncapped_target_weight"
            )
            if stop_distance <= 0:
                raise DossierError(f"{label}: stop distance must be positive")
            _require_decimal_equal(
                uncapped,
                risk_budget / stop_distance,
                f"{label}.uncapped_target_weight",
            )
            _require_decimal_equal(
                _decimal(
                    target.get("requested_delta_weight"),
                    f"{label}.requested_delta_weight",
                ),
                target_weight - current,
                f"{label}.requested_delta_weight",
            )
            expected_loss = target_weight * stop_distance
            _require_decimal_equal(
                _decimal(
                    target.get("expected_loss_at_stop_fraction"),
                    f"{label}.expected_loss_at_stop_fraction",
                ),
                expected_loss,
                f"{label}.expected_loss_at_stop_fraction",
            )
            expected_target_digest = _object_payload_sha256(target, "target_sha256", label)
            if target.get("target_sha256") != expected_target_digest:
                raise DossierError(f"{label}.target_sha256: deterministic target hash mismatch")
            target_weights.append(target_weight)
            current_weights.append(current)
            expected_losses.append(expected_loss)
            target_weight_rows.append((target, target_weight))

        summary = proposal.get("summary")
        if not isinstance(summary, dict):
            raise DossierError("portfolio-proposal-valid.json.summary: expected an object")
        invested = sum(target_weights, Decimal(0))
        gross = sum((abs(value) for value in target_weights), Decimal(0))
        net = sum(target_weights, Decimal(0))
        turnover = sum(
            (
                abs(target - current)
                for target, current in zip(target_weights, current_weights, strict=False)
            ),
            Decimal(0),
        )
        summary_expectations = {
            "target_invested_weight": invested,
            "cash_target_weight": Decimal(1) - invested,
            "target_gross_weight": gross,
            "target_net_weight": net,
            "target_turnover_weight": turnover,
            "total_risk_at_stop_fraction": sum(expected_losses, Decimal(0)),
            "portfolio_loss_at_stop_fraction": sum(expected_losses, Decimal(0)),
        }
        for field, expected in summary_expectations.items():
            _require_decimal_equal(
                _decimal(summary.get(field), f"portfolio-proposal-valid.json.summary.{field}"),
                expected,
                f"portfolio-proposal-valid.json.summary.{field}",
            )
        exposure_specs = (
            ("issuer_id", "issuer_exposures"),
            ("corporate_group_id", "corporate_group_exposures"),
            ("sector_id", "sector_exposures"),
            ("theme_ids", "theme_exposures"),
        )
        exposure_maps: dict[str, dict[str, Decimal]] = {}
        for classification_field, summary_field in exposure_specs:
            exposure_maps[classification_field] = _aggregate_classification_weights(
                target_weight_rows, classification_field
            )
            _require_exposure_summary(
                summary.get(summary_field),
                exposure_maps[classification_field],
                weight_field="target_weight",
                label=f"portfolio-proposal-valid.json.summary.{summary_field}",
            )

        portfolio_limits = risk_policy.get("portfolio_limits")
        loss_limits = risk_policy.get("loss_limits")
        if not isinstance(portfolio_limits, dict) or not isinstance(loss_limits, dict):
            raise DossierError("risk-policy-valid.json: missing portfolio/loss limits")
        limit_checks = (
            (
                max(exposure_maps["issuer_id"].values(), default=Decimal(0)),
                "max_issuer_weight",
            ),
            (
                max(exposure_maps["corporate_group_id"].values(), default=Decimal(0)),
                "max_corporate_group_weight",
            ),
            (
                max(target_weights, default=Decimal(0)),
                "max_single_name_weight",
            ),
            (
                max(exposure_maps["sector_id"].values(), default=Decimal(0)),
                "max_sector_weight",
            ),
            (
                max(exposure_maps["theme_ids"].values(), default=Decimal(0)),
                "max_theme_weight",
            ),
            (gross, "max_gross_weight"),
            (abs(net), "max_net_weight"),
            (turnover, "max_daily_turnover_weight"),
        )
        for observed, limit_field in limit_checks:
            limit = _decimal(
                portfolio_limits.get(limit_field), f"risk-policy-valid.json.{limit_field}"
            )
            if observed > limit:
                raise DossierError(f"portfolio-proposal-valid.json: {limit_field} is breached")
        if Decimal(1) - invested < _decimal(
            portfolio_limits.get("min_cash_weight"),
            "risk-policy-valid.json.portfolio_limits.min_cash_weight",
        ):
            raise DossierError("portfolio-proposal-valid.json: minimum cash reserve is breached")
        portfolio_loss = sum(expected_losses, Decimal(0))
        if portfolio_loss > _decimal(
            loss_limits.get("max_portfolio_loss_at_stop_fraction"),
            "risk-policy-valid.json.loss_limits.max_portfolio_loss_at_stop_fraction",
        ):
            raise DossierError(
                "portfolio-proposal-valid.json: portfolio loss-at-stop limit is breached"
            )

        portfolio_snapshot = fixtures.get("portfolio-snapshot-valid.json")
        embedded_snapshot = proposal.get("portfolio_snapshot")
        if not isinstance(portfolio_snapshot, dict) or not isinstance(embedded_snapshot, dict):
            raise DossierError("portfolio-proposal-valid.json: portfolio snapshot is missing")
        portfolio_snapshot_digest = _canonical_hash_identity(
            portfolio_snapshot, "portfolio-snapshot-valid.json"
        )
        if (
            embedded_snapshot.get("snapshot_id") != portfolio_snapshot.get("portfolio_snapshot_id")
            or embedded_snapshot.get("snapshot_sha256") != portfolio_snapshot_digest
        ):
            raise DossierError(
                "portfolio-proposal-valid.json: embedded portfolio snapshot does not resolve"
            )
        nav = _decimal(
            portfolio_snapshot.get("total_nav_aud"),
            "portfolio-snapshot-valid.json.total_nav_aud",
        )
        reserved_aud = sum(
            (
                _decimal(
                    balance.get("reserved_aud"),
                    "portfolio-snapshot-valid.json.cash_balances.reserved_aud",
                )
                for balance in portfolio_snapshot.get("cash_balances", [])
                if isinstance(balance, dict)
            ),
            Decimal(0),
        )
        reserved_fraction = reserved_aud / nav if nav else Decimal(0)
        for asset_id, target in target_by_asset.items():
            reservation_check = next(
                (
                    check
                    for check in target.get("cap_checks", [])
                    if check.get("cap_code") == "RESERVATIONS"
                ),
                None,
            )
            reservation_ref = (
                reservation_check.get("source_ref") if isinstance(reservation_check, dict) else None
            )
            if (
                not isinstance(reservation_check, dict)
                or not isinstance(reservation_ref, dict)
                or reservation_ref.get("id") != portfolio_snapshot.get("portfolio_snapshot_id")
                or reservation_ref.get("sha256") != portfolio_snapshot_digest
            ):
                raise DossierError(
                    f"portfolio-proposal-valid.json.targets[{asset_id}]: "
                    "reservation proof does not resolve"
                )
            _require_decimal_equal(
                _decimal(
                    reservation_check.get("before_weight"),
                    f"portfolio-proposal-valid.json.targets[{asset_id}].RESERVATIONS",
                ),
                reserved_fraction,
                f"portfolio-proposal-valid.json.targets[{asset_id}].RESERVATIONS",
            )
        lineage = proposal.get("lineage")
        if not isinstance(lineage, dict) or lineage.get("lineage_stage") != "EVALUATION_FROZEN":
            raise DossierError(
                "portfolio-proposal-valid.json: proposal must embed predecessor "
                "EVALUATION_FROZEN lineage without a proposal self-reference"
            )
        if lineage.get("portfolio_proposal_ref") is not None:
            raise DossierError(
                "portfolio-proposal-valid.json: proposal lineage cannot self-reference "
                "its unhashed artifact"
            )

    sizing_documents = [
        (filename, document)
        for filename, document in fixtures.items()
        if isinstance(document, dict) and document.get("contract_name") == "sizing-decision-v1"
    ]
    for filename, sizing in sizing_documents:
        status = sizing.get("status")
        sized = status == "SIZED"
        lines = sizing.get("line_items")
        if not isinstance(lines, list):
            raise DossierError(f"{filename}.line_items: expected an array")
        if sizing.get("eligible_for_staging") is not sized:
            raise DossierError(f"{filename}: status and eligible_for_staging disagree")
        if sized != bool(lines):
            raise DossierError(f"{filename}: SIZED must contain lines and rejection must not")
        lineage = sizing.get("lineage")
        expected_stage = {
            "SIZED": "PROPOSAL_BUILT",
            "REJECTED_NO_POLICY": "EVALUATION_FROZEN",
            "REJECTED_POLICY_VIOLATION": "PROPOSAL_BUILT",
        }.get(status)
        if not isinstance(lineage, dict) or lineage.get("lineage_stage") != expected_stage:
            raise DossierError(f"{filename}: sizing status and lineage stage disagree")
        if sized and lineage.get("sizing_decision_ref") is not None:
            raise DossierError(
                f"{filename}: sizing lineage cannot self-reference its unhashed artifact"
            )
        if not sized:
            continue

        _require_classification_snapshot_ref(
            sizing.get("classification_snapshot_ref"),
            classification,
            f"{filename}.classification_snapshot_ref",
        )
        if sizing.get("classification_snapshot_ref") != proposal.get("classification_snapshot_ref"):
            raise DossierError(
                f"{filename}: sizing classification snapshot differs from frozen proposal"
            )
        proposal_ref = sizing.get("proposal_ref")
        if (
            not isinstance(proposal_ref, dict)
            or proposal_ref.get("id") != proposal.get("proposal_id")
            or proposal_ref.get("sha256")
            != _canonical_hash_identity(proposal, "portfolio-proposal-valid.json")
        ):
            raise DossierError(f"{filename}: proposal reference does not resolve")
        _require_versioned_policy_ref(
            sizing.get("construction_policy_ref"),
            construction_policy,
            identifier_field="policy_id",
            version_field="policy_version",
            label=f"{filename}.construction_policy_ref",
        )
        _require_versioned_policy_ref(
            sizing.get("risk_policy_ref"),
            risk_policy,
            identifier_field="policy_id",
            version_field="policy_version",
            label=f"{filename}.risk_policy_ref",
        )
        _require_versioned_policy_ref(
            sizing.get("sizing_policy_ref"),
            sizing_policy,
            identifier_field="sizing_policy_id",
            version_field="sizing_policy_version",
            label=f"{filename}.sizing_policy_ref",
        )
        sizing_decision_at = _timestamp(sizing.get("decision_at"), f"{filename}.decision_at")
        classified_assets = _validate_classification_snapshot(classification, sizing_decision_at)
        line_by_asset = _require_ordered_unique(lines, "asset_id", f"{filename}.line_items")
        snapshot_ref = sizing.get("portfolio_snapshot_ref")
        snapshot_matches = [
            document
            for document in fixtures.values()
            if isinstance(document, dict)
            and document.get("contract_name") == "portfolio-snapshot-v1"
            and isinstance(snapshot_ref, dict)
            and document.get("portfolio_snapshot_id") == snapshot_ref.get("id")
            and _canonical_hash_identity(document, filename) == snapshot_ref.get("sha256")
        ]
        if len(snapshot_matches) != 1:
            raise DossierError(f"{filename}: portfolio snapshot reference is unresolved")
        sizing_snapshot = snapshot_matches[0]
        sizing_nav = _decimal(
            sizing_snapshot.get("total_nav_aud"), f"{filename}.portfolio_snapshot.total_nav_aud"
        )
        if sizing_nav <= 0:
            raise DossierError(f"{filename}: portfolio NAV must be positive")
        sizing_cash = _decimal(
            sizing_snapshot.get("components", {}).get("cash_aud"),
            f"{filename}.portfolio_snapshot.components.cash_aud",
        )
        reserved_aud = sum(
            (
                _decimal(
                    balance.get("reserved_aud"),
                    f"{filename}.portfolio_snapshot.cash_balances.reserved_aud",
                )
                for balance in sizing_snapshot.get("cash_balances", [])
                if isinstance(balance, dict)
            ),
            Decimal(0),
        )
        reserved_fraction = reserved_aud / sizing_nav

        requested_total = Decimal(0)
        approved_total = Decimal(0)
        fee_total = Decimal(0)
        cash_delta = Decimal(0)
        projected_rows: list[tuple[dict[str, Any], Decimal]] = []
        expected_sizing_losses: list[Decimal] = []
        turnover_weight = Decimal(0)
        checks_by_asset: dict[str, dict[str, dict[str, Any]]] = {}
        for asset_id, line in line_by_asset.items():
            label = f"{filename}.line_items[{asset_id}]"
            decision = line.get("decision")
            if decision not in {"APPROVED", "REDUCED"}:
                raise DossierError(f"{label}: SIZED contains a rejected line")
            checks = line.get("constraint_checks", [])
            if not isinstance(checks, list):
                raise DossierError(f"{label}.constraint_checks: expected an array")
            sequences = [check.get("sequence") for check in checks]
            codes = [check.get("constraint_code") for check in checks]
            if sequences != list(range(1, len(SIZING_CONSTRAINT_ORDER) + 1)):
                raise DossierError(f"{label}: constraint-check sequence is not exact")
            if codes != list(SIZING_CONSTRAINT_ORDER):
                raise DossierError(
                    f"{label}: constraint-check codes do not match policy order exactly"
                )
            check_map: dict[str, dict[str, Any]] = {}
            for check in checks:
                code = check.get("constraint_code")
                if not isinstance(code, str):
                    raise DossierError(f"{label}: invalid constraint code")
                check_map[code] = check
                if code in {"CLASSIFICATION", "TICK_RULE"}:
                    if (
                        check.get("check_type") != "BOOLEAN_PRECONDITION"
                        or check.get("passed") is not True
                    ):
                        raise DossierError(f"{label}: Boolean precondition {code} failed")
                elif check.get("check_type") != "NUMERIC_LIMIT" or check.get("action") not in {
                    "PASS",
                    "REDUCE",
                }:
                    raise DossierError(
                        f"{label}: SIZED contains a rejected or mistyped constraint check"
                    )
            checks_by_asset[asset_id] = check_map
            price = _decimal(line.get("reference_price_aud"), f"{label}.reference_price_aud")
            board_lot = _decimal(line.get("board_lot_quantity"), f"{label}.board_lot_quantity")
            requested_quantity = _decimal(
                line.get("requested_quantity"), f"{label}.requested_quantity"
            )
            approved_quantity = _decimal(
                line.get("approved_quantity"), f"{label}.approved_quantity"
            )
            if board_lot <= 0 or requested_quantity % board_lot != 0:
                raise DossierError(f"{label}: requested quantity is not a whole board lot")
            if approved_quantity % board_lot != 0:
                raise DossierError(f"{label}: approved quantity is not a whole board lot")
            if approved_quantity > requested_quantity:
                raise DossierError(f"{label}: approved quantity exceeds requested quantity")
            if decision == "APPROVED" and approved_quantity != requested_quantity:
                raise DossierError(f"{label}: APPROVED line changed quantity")
            if decision == "REDUCED" and approved_quantity >= requested_quantity:
                raise DossierError(f"{label}: REDUCED line did not reduce quantity")
            target = target_by_asset.get(asset_id)
            classified = classified_assets.get(asset_id)
            if target is None or classified is None:
                raise DossierError(f"{label}: line lacks unique proposal/classification lineage")
            if line.get("proposal_target_sha256") != target.get("target_sha256"):
                raise DossierError(f"{label}: proposal target hash does not resolve")
            _require_classification_identity(classified, line, label)
            expected_tick = _tick_size_for_price(classified, price, label)
            _require_decimal_equal(
                _decimal(line.get("tick_size_aud"), f"{label}.tick_size_aud"),
                expected_tick,
                f"{label}.tick_size_aud",
            )
            if price % expected_tick != 0:
                raise DossierError(f"{label}: reference price is not on the effective tick")
            classification_check_ref = check_map["CLASSIFICATION"].get("source_ref")
            tick_check_ref = check_map["TICK_RULE"].get("source_ref")
            trading_source = classified.get("provenance", {}).get("trading_rule", {})
            if (
                not isinstance(classification_check_ref, dict)
                or classification_check_ref.get("id")
                != classification.get("classification_snapshot_id")
                or classification_check_ref.get("sha256") != classification_digest
            ):
                raise DossierError(f"{label}: classification precondition source is unresolved")
            if (
                not isinstance(tick_check_ref, dict)
                or tick_check_ref.get("id") != classified.get("tick_rule", {}).get("tick_rule_id")
                or tick_check_ref.get("sha256") != trading_source.get("record_sha256")
            ):
                raise DossierError(f"{label}: tick-rule precondition source is unresolved")
            requested_notional = _decimal(
                line.get("requested_notional_aud"), f"{label}.requested_notional_aud"
            )
            approved_notional = _decimal(
                line.get("approved_notional_aud"), f"{label}.approved_notional_aud"
            )
            _require_decimal_equal(
                requested_notional,
                requested_quantity * price,
                f"{label}.requested_notional_aud",
            )
            _require_decimal_equal(
                approved_notional,
                approved_quantity * price,
                f"{label}.approved_notional_aud",
            )
            for field in ("current_weight", "target_weight", "requested_delta_weight"):
                if line.get(field) != target.get(field):
                    raise DossierError(f"{label}.{field}: differs from frozen proposal target")
            expected_line_digest = _object_payload_sha256(line, "line_item_sha256", label)
            if line.get("line_item_sha256") != expected_line_digest:
                raise DossierError(f"{label}.line_item_sha256: deterministic line hash mismatch")
            requested_total += requested_notional
            approved_total += approved_notional
            fee = _decimal(line.get("estimated_fees_aud"), f"{label}.estimated_fees_aud")
            fee_total += fee
            signed_notional = approved_notional if line.get("side") == "BUY" else -approved_notional
            cash_delta -= signed_notional + fee
            projected_weight = (
                _decimal(line.get("current_weight"), f"{label}.current_weight")
                + signed_notional / sizing_nav
            )
            projected_rows.append((line, projected_weight))
            turnover_weight += abs(signed_notional) / sizing_nav
            expected_sizing_losses.append(
                abs(projected_weight)
                * _decimal(
                    target.get("effective_stop_distance_fraction"),
                    f"{label}.effective_stop_distance_fraction",
                )
            )
        summary = sizing.get("summary")
        if not isinstance(summary, dict):
            raise DossierError(f"{filename}.summary: expected an object")
        for field, expected in {
            "requested_notional_aud": requested_total,
            "approved_notional_aud": approved_total,
            "estimated_fees_aud": fee_total,
        }.items():
            _require_decimal_equal(
                _decimal(summary.get(field), f"{filename}.summary.{field}"),
                expected,
                f"{filename}.summary.{field}",
            )
        projected_gross = sum((abs(weight) for _, weight in projected_rows), Decimal(0))
        projected_net = sum((weight for _, weight in projected_rows), Decimal(0))
        projected_loss = sum(expected_sizing_losses, Decimal(0))
        for field, expected in {
            "projected_cash_aud": sizing_cash + cash_delta,
            "projected_gross_weight": projected_gross,
            "projected_net_weight": projected_net,
            "projected_turnover_weight": turnover_weight,
            "projected_portfolio_loss_at_stop_fraction": projected_loss,
        }.items():
            _require_decimal_equal(
                _decimal(summary.get(field), f"{filename}.summary.{field}"),
                expected,
                f"{filename}.summary.{field}",
            )
        projected_exposure_specs = (
            ("issuer_id", "projected_issuer_exposures"),
            ("corporate_group_id", "projected_corporate_group_exposures"),
            ("sector_id", "projected_sector_exposures"),
            ("theme_ids", "projected_theme_exposures"),
        )
        projected_exposures: dict[str, dict[str, Decimal]] = {}
        for classification_field, summary_field in projected_exposure_specs:
            projected_exposures[classification_field] = _aggregate_classification_weights(
                projected_rows, classification_field
            )
            _require_exposure_summary(
                summary.get(summary_field),
                projected_exposures[classification_field],
                weight_field="projected_weight",
                label=f"{filename}.summary.{summary_field}",
            )

        # R0-A1: limits that resolve from a ratified policy are identical for
        # every line of this sizing decision, so resolve them once.
        sizing_limits = sizing_policy.get("limits", {})
        policy_limits: dict[str, Decimal] = {
            code: _decimal(
                risk_policy.get(section, {}).get(field),
                f"{filename}.risk_policy.{section}.{field}",
            )
            for code, (section, field) in SIZING_LIMIT_FROM_RISK_POLICY.items()
        }
        policy_limits.update(
            {
                code: _decimal(
                    sizing_limits.get(field),
                    f"{filename}.sizing_policy.limits.{field}",
                )
                for code, field in SIZING_LIMIT_FROM_SIZING_POLICY.items()
            }
        )
        maximum_fee_fraction = _decimal(
            sizing_limits.get("maximum_fee_fraction"),
            f"{filename}.sizing_policy.limits.maximum_fee_fraction",
        )
        # Liquidity caps resolve from THIS policy, not risk-policy-v1:
        # sizing-policy-v1 freezes liquidity caps and is authoritative.
        maximum_order_adv_fraction = _decimal(
            sizing_limits.get("maximum_order_adv_fraction"),
            f"{filename}.sizing_policy.limits.maximum_order_adv_fraction",
        )
        available_cash_reserve_fraction = _decimal(
            sizing_limits.get("available_cash_reserve_fraction"),
            f"{filename}.sizing_policy.limits.available_cash_reserve_fraction",
        )

        for asset_id, line in line_by_asset.items():
            label = f"{filename}.line_items[{asset_id}]"
            check_map = checks_by_asset[asset_id]
            candidate = candidate_by_asset.get(asset_id, {})
            projected_weight = next(weight for row, weight in projected_rows if row is line)
            themes = line.get("theme_ids")
            theme_observed = max(
                (projected_exposures["theme_ids"].get(theme, Decimal(0)) for theme in themes),
                default=Decimal(0),
            )
            numeric_observed = {
                "TARGET_NOTIONAL": _decimal(
                    line.get("requested_notional_aud"), f"{label}.requested_notional_aud"
                ),
                "ISSUER": projected_exposures["issuer_id"][line["issuer_id"]],
                "CORPORATE_GROUP": projected_exposures["corporate_group_id"][
                    line["corporate_group_id"]
                ],
                "SINGLE_NAME": abs(projected_weight),
                "SECTOR": projected_exposures["sector_id"][line["sector_id"]],
                "THEME": theme_observed,
                "PORTFOLIO_LOSS_AT_STOP": projected_loss,
                "GROSS_EXPOSURE": projected_gross,
                "NET_EXPOSURE": projected_net,
                "RESERVATIONS": reserved_fraction,
                "TURNOVER": turnover_weight,
                "BOARD_LOT": _decimal(
                    line.get("requested_quantity"), f"{label}.requested_quantity"
                ),
                "MINIMUM_ORDER": _decimal(
                    line.get("requested_notional_aud"), f"{label}.requested_notional_aud"
                ),
                "FEES": _decimal(line.get("estimated_fees_aud"), f"{label}.estimated_fees_aud"),
                "ADV_PARTICIPATION": _decimal(
                    line.get("requested_notional_aud"), f"{label}.requested_notional_aud"
                ),
                "AVAILABLE_CASH": sizing_cash,
                "SPREAD": _decimal(
                    candidate.get("spread_fraction"), f"{label}.candidate.spread_fraction"
                ),
            }
            for code, expected in numeric_observed.items():
                _require_decimal_equal(
                    _decimal(
                        check_map[code].get("observed_value"),
                        f"{label}.constraint_checks[{code}].observed_value",
                    ),
                    expected,
                    f"{label}.constraint_checks[{code}].observed_value",
                )

            # R0-A1: every numeric check declares and honours a comparison
            # direction, and its limit resolves from a ratified artifact
            # rather than being producer-supplied.
            for code in SIZING_CONSTRAINT_COMPARISON:
                _assert_constraint_comparison(check_map[code], code, label)

            numeric_limits: dict[str, Decimal] = {
                **policy_limits,
                "FEES": _decimal(
                    line.get("approved_notional_aud"), f"{label}.approved_notional_aud"
                )
                * maximum_fee_fraction,
                "BOARD_LOT": _decimal(
                    line.get("board_lot_quantity"), f"{label}.board_lot_quantity"
                ),
                "ADV_PARTICIPATION": _decimal(
                    candidate.get("average_daily_value_aud"),
                    f"{label}.candidate.average_daily_value_aud",
                )
                * maximum_order_adv_fraction,
                # Cash sufficiency is the capital-path solvency guard: the
                # spendable balance is the frozen snapshot cash less the
                # ratified reserve, and the applied notional is capped by it.
                "AVAILABLE_CASH": sizing_cash * (Decimal(1) - available_cash_reserve_fraction),
                "TARGET_NOTIONAL": _decimal(
                    target_by_asset[asset_id].get("target_weight"),
                    f"{label}.proposal_target.target_weight",
                )
                * sizing_nav,
            }
            for code, expected_limit in numeric_limits.items():
                _require_decimal_equal(
                    _decimal(
                        check_map[code].get("limit_value"),
                        f"{label}.constraint_checks[{code}].limit_value",
                    ),
                    expected_limit,
                    f"{label}.constraint_checks[{code}].limit_value",
                )

        risk_limit_checks = (
            (
                max(projected_exposures["issuer_id"].values(), default=Decimal(0)),
                "max_issuer_weight",
            ),
            (
                max(
                    projected_exposures["corporate_group_id"].values(),
                    default=Decimal(0),
                ),
                "max_corporate_group_weight",
            ),
            (
                max((abs(weight) for _, weight in projected_rows), default=Decimal(0)),
                "max_single_name_weight",
            ),
            (
                max(projected_exposures["sector_id"].values(), default=Decimal(0)),
                "max_sector_weight",
            ),
            (
                max(projected_exposures["theme_ids"].values(), default=Decimal(0)),
                "max_theme_weight",
            ),
            (projected_gross, "max_gross_weight"),
            (abs(projected_net), "max_net_weight"),
            (turnover_weight, "max_daily_turnover_weight"),
        )
        portfolio_limits = risk_policy["portfolio_limits"]
        for observed, field in risk_limit_checks:
            if observed > _decimal(portfolio_limits.get(field), f"risk-policy-valid.json.{field}"):
                raise DossierError(f"{filename}: projected {field} is breached")
        if projected_loss > _decimal(
            risk_policy["loss_limits"].get("max_portfolio_loss_at_stop_fraction"),
            "risk-policy-valid.json.loss_limits.max_portfolio_loss_at_stop_fraction",
        ):
            raise DossierError(f"{filename}: projected portfolio loss at stop is breached")


def _validate_staging_semantics(fixtures: dict[str, Any]) -> None:
    staged = fixtures.get("staged-order-valid.json")
    sizing = fixtures.get("sizing-valid.json")
    if not isinstance(staged, dict) or not isinstance(sizing, dict):
        raise DossierError(
            "staging semantics require staged-order-valid.json and sizing-valid.json"
        )
    sizing_ref = staged.get("sizing_decision_ref")
    if (
        not isinstance(sizing_ref, dict)
        or sizing_ref.get("status") != "SIZED"
        or sizing_ref.get("eligible_for_staging") is not True
    ):
        raise DossierError(
            "staged-order-valid.json: referenced sizing decision is not staging-eligible"
        )
    if (
        sizing.get("status") != "SIZED"
        or sizing.get("eligible_for_staging") is not True
        or sizing_ref.get("id") != sizing.get("sizing_decision_id")
        or sizing_ref.get("sha256") != _canonical_hash_identity(sizing, "sizing-valid.json")
    ):
        raise DossierError(
            "staged-order-valid.json: sizing reference does not resolve to the SIZED fixture"
        )
    lineage = staged.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("lineage_stage") != "SIZE_DECIDED":
        raise DossierError(
            "staged-order-valid.json: staged set must embed predecessor SIZE_DECIDED lineage"
        )
    if any(
        lineage.get(field) is not None
        for field in (
            "staging_policy_ref",
            "promotion_decision_ref",
            "staged_order_set_ref",
        )
    ):
        raise DossierError(
            "staged-order-valid.json: staged-set lineage cannot self-reference or "
            "advance before the artifact is hashed"
        )

    tier = staged.get("evidence_tier")
    promotion = staged.get("promotion_evidence")
    gates = staged.get("gate_evidence")
    if not isinstance(promotion, dict) or not isinstance(gates, dict):
        raise DossierError("staged-order-valid.json: missing promotion or gate evidence")
    if promotion.get("permitted_evidence_tier") != tier:
        raise DossierError("staged-order-valid.json: evidence tier and James promotion disagree")
    expected_decision = {
        "PAPER_ONLY": "HOLD_PAPER_ONLY",
        "UNCALIBRATED": "APPROVE_UNCALIBRATED_VISIBILITY",
        "EVIDENCE_BACKED": "APPROVE_EVIDENCE_BACKED_LANGUAGE",
    }.get(tier)
    if promotion.get("decision") != expected_decision:
        raise DossierError("staged-order-valid.json: promotion decision and tier disagree")
    if tier in {"UNCALIBRATED", "EVIDENCE_BACKED"} and promotion.get("decided_by") != "James":
        raise DossierError(
            "staged-order-valid.json: promoted evidence language lacks James approval"
        )
    if tier == "EVIDENCE_BACKED" and not (
        gates.get("operational_gate_passed") is True and gates.get("strategy_gate_passed") is True
    ):
        raise DossierError("staged-order-valid.json: EVIDENCE_BACKED requires both evidence gates")
    if tier == "UNCALIBRATED" and not (
        gates.get("operational_gate_passed") is True and gates.get("strategy_gate_passed") is False
    ):
        raise DossierError(
            "staged-order-valid.json: UNCALIBRATED requires operational-only gate passage"
        )

    sized_quantities = {
        line["asset_id"]: _decimal(
            line.get("approved_quantity"),
            f"sizing-valid.json.line_items[{index}].approved_quantity",
        )
        for index, line in enumerate(sizing.get("line_items", []))
    }
    order_notional_total = Decimal(0)
    order_fee_total = Decimal(0)
    for index, order in enumerate(staged.get("orders", [])):
        label = f"staged-order-valid.json.orders[{index}]"
        quantity = _decimal(order.get("total_quantity"), f"{label}.total_quantity")
        if sized_quantities.get(order.get("asset_id")) != quantity:
            raise DossierError(f"{label}: staged quantity does not match sizing decision")
        reference = _decimal(order.get("reference_price_aud"), f"{label}.reference_price_aud")
        adverse = _decimal(order.get("max_adverse_fraction"), f"{label}.max_adverse_fraction")
        expected_raw = (
            reference * (Decimal(1) + adverse)
            if order.get("side") == "BUY"
            else reference * (Decimal(1) - adverse)
        )
        raw = _decimal(order.get("raw_limit_price_aud"), f"{label}.raw_limit_price_aud")
        _require_decimal_equal(raw, expected_raw, f"{label}.raw_limit_price_aud")
        tick = _decimal(order.get("tick_size_aud"), f"{label}.tick_size_aud")
        limit_price = _decimal(order.get("limit_price_aud"), f"{label}.limit_price_aud")
        if tick <= 0 or limit_price % tick != 0:
            raise DossierError(f"{label}: limit price is not on the tick grid")
        rounding = order.get("tick_rounding")
        expected_rounding = "BUY_FLOOR" if order.get("side") == "BUY" else "SELL_CEILING"
        if rounding != expected_rounding:
            raise DossierError(f"{label}: side and tick-rounding rule disagree")
        rounding_mode = ROUND_FLOOR if rounding == "BUY_FLOOR" else ROUND_CEILING
        expected_limit = (raw / tick).to_integral_value(rounding=rounding_mode) * tick
        _require_decimal_equal(limit_price, expected_limit, f"{label}.limit_price_aud")
        notional = _decimal(order.get("estimated_notional_aud"), f"{label}.estimated_notional_aud")
        _require_decimal_equal(notional, quantity * limit_price, f"{label}.estimated_notional_aud")

        stages = order.get("stages", [])
        stage_numbers = [stage.get("stage_number") for stage in stages]
        if stage_numbers != list(range(1, len(stages) + 1)):
            raise DossierError(f"{label}: stage numbers are not contiguous")
        stage_quantity = sum(
            (_decimal(stage.get("quantity"), f"{label}.stages.quantity") for stage in stages),
            Decimal(0),
        )
        stage_fraction = sum(
            (
                _decimal(stage.get("policy_fraction"), f"{label}.stages.policy_fraction")
                for stage in stages
            ),
            Decimal(0),
        )
        _require_decimal_equal(stage_quantity, quantity, f"{label}.stages quantities")
        _require_decimal_equal(stage_fraction, Decimal(1), f"{label}.stages policy fractions")
        for stage_index, stage in enumerate(stages):
            not_before = _timestamp(
                stage.get("not_before"), f"{label}.stages[{stage_index}].not_before"
            )
            expires_at = _timestamp(
                stage.get("expires_at"), f"{label}.stages[{stage_index}].expires_at"
            )
            if expires_at <= not_before:
                raise DossierError(f"{label}.stages[{stage_index}]: expiry is not later")

        order_notional_total += notional
        order_fee_total += _decimal(order.get("estimated_fees_aud"), f"{label}.estimated_fees_aud")
    _require_decimal_equal(
        _decimal(
            staged.get("estimated_total_notional_aud"),
            "staged-order-valid.json.estimated_total_notional_aud",
        ),
        order_notional_total,
        "staged-order-valid.json.estimated_total_notional_aud",
    )
    _require_decimal_equal(
        _decimal(
            staged.get("estimated_total_fees_aud"),
            "staged-order-valid.json.estimated_total_fees_aud",
        ),
        order_fee_total,
        "staged-order-valid.json.estimated_total_fees_aud",
    )


def _validate_evaluator_semantics(fixtures: dict[str, Any]) -> None:
    evaluator = fixtures.get("paper-episode-golden.json")
    cohort = fixtures.get("cohort-statistics-valid.json")
    config = fixtures.get("evaluator-config-valid.json")
    policy = fixtures.get("evaluation-policy-valid.json")
    if not all(isinstance(item, dict) for item in (evaluator, cohort, config, policy)):
        raise DossierError(
            "evaluator semantics require evaluator, cohort, config, and policy fixtures"
        )

    policy_sha256 = _canonical_hash_identity(policy, "evaluation-policy-valid.json")
    policy_protocol = policy.get("bootstrap")
    config_protocol = config.get("statistical_protocol")
    cohort_protocol = cohort.get("protocol")
    if not all(
        isinstance(item, dict) for item in (policy_protocol, config_protocol, cohort_protocol)
    ):
        raise DossierError("S11 statistical protocol is missing from policy/config/cohort")
    cohort_protocol_without_identity = {
        key: value for key, value in cohort_protocol.items() if key != "evaluation_policy_sha256"
    }
    if (
        config_protocol != policy_protocol
        or cohort_protocol_without_identity != policy_protocol
        or cohort_protocol.get("evaluation_policy_sha256") != policy_sha256
    ):
        raise DossierError(
            "S11 statistical protocol drifted between evaluation policy, config, and cohort"
        )

    family = config.get("candidate_family")
    multiple_testing = cohort.get("multiple_testing")
    if (
        not isinstance(family, dict)
        or not isinstance(multiple_testing, dict)
        or cohort.get("candidate_family_id") != family.get("family_id")
        or multiple_testing.get("registered_candidate_count")
        != family.get("registered_candidate_count")
        or multiple_testing.get("familywise_method") != "HOLM"
        or policy_protocol.get("multiple_testing_method") != "HOLM_FAMILYWISE_DIAGNOSTIC"
        or (
            family.get("selection_events_permitted") is False
            and multiple_testing.get("selection_event_count") != "0"
        )
    ):
        raise DossierError("S11 candidate-family Holm diagnostics drifted from policy")

    for index, result in enumerate(cohort.get("bootstrap_results", [])):
        metric_id = result.get("metric_id") if isinstance(result, dict) else None
        if not isinstance(metric_id, str):
            raise DossierError(
                f"cohort-statistics-valid.json.bootstrap_results[{index}]: missing metric_id"
            )
        expected_seed_material = hashlib.sha256(
            f"{cohort.get('cohort_id')}|{metric_id}|{policy_sha256}".encode()
        ).hexdigest()
        if (
            result.get("seed_material_sha256") != expected_seed_material
            or result.get("seed_uint128_hex") != expected_seed_material[:32]
        ):
            raise DossierError(
                f"cohort-statistics-valid.json.bootstrap_results[{index}]: "
                "seed derivation drifted from evaluation policy"
            )

    register = evaluator.get("episode_register")
    counts = evaluator.get("episode_counts")
    if not isinstance(register, list) or not isinstance(counts, dict):
        raise DossierError("paper-episode-golden.json: missing episode register or counts")
    observed_statuses = Counter(str(item.get("status", "")).lower() for item in register)
    expected_counts = {
        "scheduled": len(register),
        **{
            status: observed_statuses.get(status, 0)
            for status in (
                "open",
                "blocked",
                "rejected",
                "no_action",
                "invalid",
                "matured",
                "unavailable",
            )
        },
    }
    actual_counts = {
        key: _integer(counts.get(key), f"paper-episode-golden.json.episode_counts.{key}")
        for key in expected_counts
    }
    if actual_counts != expected_counts:
        raise DossierError(
            "paper-episode-golden.json: episode_counts drifted from episode_register"
        )
    sequences = [
        _integer(
            episode.get("origin_sequence"),
            f"paper-episode-golden.json.episode_register[{index}].origin_sequence",
        )
        for index, episode in enumerate(register)
    ]
    if sequences != list(range(1, len(register) + 1)):
        raise DossierError("paper-episode-golden.json: episode origin sequence is not contiguous")
    for index, episode in enumerate(register):
        matured = episode.get("status") == "MATURED"
        has_outcome = isinstance(episode.get("outcome_ref"), dict)
        if matured is not has_outcome:
            raise DossierError(
                f"paper-episode-golden.json.episode_register[{index}]: "
                "outcome reference does not match maturity state"
            )

    strategy = evaluator.get("strategy_gate")
    operational = evaluator.get("operational_gate")
    promotion = evaluator.get("promotion_gate")
    if not all(isinstance(item, dict) for item in (strategy, operational, promotion)):
        raise DossierError("paper-episode-golden.json: missing evaluator gates")

    operational_thresholds = operational["thresholds"]
    operational_evidence = operational["evidence"]
    top_defects = evaluator.get("unresolved_material_defects")
    if top_defects != operational_evidence.get("unresolved_material_defects"):
        raise DossierError("paper-episode-golden.json: defect register and gate evidence disagree")
    defect_limit = _integer(
        operational_thresholds.get("maximum_each_unresolved_material_defect"),
        "paper-episode-golden.json.operational_gate.thresholds."
        "maximum_each_unresolved_material_defect",
    )
    defect_counts = operational_evidence.get("unresolved_material_defects")
    if not isinstance(defect_counts, dict):
        raise DossierError("paper-episode-golden.json: missing operational defect counts")
    operational_prerequisites = (
        _integer(
            operational_evidence.get("consecutive_complete_sessions"),
            "paper-episode-golden.json.operational_gate.evidence." "consecutive_complete_sessions",
        )
        >= _integer(
            operational_thresholds.get("minimum_consecutive_complete_sessions"),
            "paper-episode-golden.json.operational_gate.thresholds."
            "minimum_consecutive_complete_sessions",
        )
        and _decimal(
            operational_evidence.get("priced_nav_day_fraction"),
            "paper-episode-golden.json.operational_gate.evidence." "priced_nav_day_fraction",
        )
        >= _decimal(
            operational_thresholds.get("minimum_priced_nav_day_fraction"),
            "paper-episode-golden.json.operational_gate.thresholds."
            "minimum_priced_nav_day_fraction",
        )
        and all(
            _integer(value, f"paper-episode-golden.json defect {key}") <= defect_limit
            for key, value in defect_counts.items()
        )
        and all(
            operational_evidence.get(field) is True
            for field in (
                "bit_identical_replay",
                "genuine_xjo_tr_present",
                "effective_fee_schedule_present",
                "ratified_risk_policy_present",
                "dependency_isolation_passed",
                "evidence_chain_complete",
            )
        )
    )
    if operational.get("passed") is not operational_prerequisites:
        raise DossierError(
            "paper-episode-golden.json: operational gate boolean does not equal "
            "recomputed replay/benchmark/fee/risk/defect/runway prerequisites"
        )

    strategy_thresholds = strategy["thresholds"]
    strategy_evidence = strategy["evidence"]
    if (
        _integer(
            strategy_evidence.get("matured_episode_count"),
            "paper-episode-golden.json.strategy_gate.evidence.matured_episode_count",
        )
        != expected_counts["matured"]
    ):
        raise DossierError(
            "paper-episode-golden.json: strategy matured count drifted from episode register"
        )
    observed_sessions = _integer(
        strategy_evidence.get("observed_sessions"),
        "paper-episode-golden.json.strategy_gate.evidence.observed_sessions",
    )
    if observed_sessions != _integer(
        evaluator.get("evaluation_window", {}).get("observed_sessions"),
        "paper-episode-golden.json.evaluation_window.observed_sessions",
    ):
        raise DossierError("paper-episode-golden.json: observed-session counts are inconsistent")
    complete_sessions = _integer(
        operational_evidence.get("consecutive_complete_sessions"),
        "paper-episode-golden.json.operational_gate.evidence.consecutive_complete_sessions",
    )
    if complete_sessions > observed_sessions:
        raise DossierError(
            "paper-episode-golden.json: consecutive complete sessions exceed observations"
        )

    positive_fields = (
        "active_return_vs_hold",
        "active_return_vs_xjo_tr",
        "bootstrap_lower_bound_vs_hold",
        "bootstrap_lower_bound_vs_xjo_tr",
    )
    positive_results = all(
        strategy_evidence.get(field) is not None
        and _decimal(
            strategy_evidence.get(field),
            f"paper-episode-golden.json.strategy_gate.evidence.{field}",
        )
        > 0
        for field in positive_fields
    )
    strategy_prerequisites = (
        observed_sessions
        >= _integer(
            strategy_thresholds.get("minimum_sessions"),
            "paper-episode-golden.json.strategy_gate.thresholds.minimum_sessions",
        )
        and expected_counts["matured"]
        >= _integer(
            strategy_thresholds.get("minimum_matured_episodes"),
            "paper-episode-golden.json.strategy_gate.thresholds." "minimum_matured_episodes",
        )
        and strategy_evidence.get("episode_horizon_sessions")
        == strategy_thresholds.get("episode_horizon_sessions")
        and strategy_evidence.get("versions_fixed") is True
        and positive_results
        and strategy_evidence.get("bootstrap_status") == "COMPLETE"
        and _decimal(
            strategy_evidence.get("fill_fraction_within_5_sessions"),
            "paper-episode-golden.json.strategy_gate.evidence." "fill_fraction_within_5_sessions",
        )
        >= _decimal(
            strategy_thresholds.get("minimum_fill_fraction_5_sessions"),
            "paper-episode-golden.json.strategy_gate.thresholds."
            "minimum_fill_fraction_5_sessions",
        )
        and _integer(
            strategy_evidence.get("policy_breach_count"),
            "paper-episode-golden.json.strategy_gate.evidence.policy_breach_count",
        )
        <= _integer(
            strategy_thresholds.get("maximum_policy_breaches"),
            "paper-episode-golden.json.strategy_gate.thresholds." "maximum_policy_breaches",
        )
        and _integer(
            strategy_evidence.get("mandate_drawdown_breach_count"),
            "paper-episode-golden.json.strategy_gate.evidence." "mandate_drawdown_breach_count",
        )
        <= _integer(
            strategy_thresholds.get("maximum_mandate_drawdown_breaches"),
            "paper-episode-golden.json.strategy_gate.thresholds."
            "maximum_mandate_drawdown_breaches",
        )
        and strategy_evidence.get("all_registered_origins_retained") is True
        and strategy_evidence.get("familywise_diagnostic_passed") is True
        and strategy_evidence.get("strategy_inputs_complete") is True
    )
    if strategy.get("passed") is not strategy_prerequisites:
        raise DossierError(
            "paper-episode-golden.json: strategy gate boolean does not equal "
            "recomputed observation/episode/bootstrap/risk prerequisites"
        )

    if promotion.get("operational_gate_passed") is not operational.get("passed"):
        raise DossierError(
            "paper-episode-golden.json: promotion and operational gate booleans disagree"
        )
    if promotion.get("strategy_gate_passed") is not strategy.get("passed"):
        raise DossierError(
            "paper-episode-golden.json: promotion and strategy gate booleans disagree"
        )
    expected_promotion = {
        (False, False): ("PAPER_ONLY_HOLD", "PAPER_ONLY"),
        (True, False): ("HOLD_UNCALIBRATED", "UNCALIBRATED"),
        (True, True): ("ELIGIBLE_FOR_JAMES_REVIEW", "UNCALIBRATED"),
    }.get((operational.get("passed"), strategy.get("passed")))
    if (
        expected_promotion is None
        or (
            promotion.get("decision"),
            promotion.get("maximum_evidence_tier"),
        )
        != expected_promotion
    ):
        raise DossierError(
            "paper-episode-golden.json: promotion gate is not the recomputed fail-closed state"
        )

    cohort_counts = cohort.get("origin_counts")
    if (
        not isinstance(cohort_counts, dict)
        or {
            key: _integer(value, f"cohort-statistics-valid.json.origin_counts.{key}")
            for key, value in cohort_counts.items()
        }
        != expected_counts
    ):
        raise DossierError(
            "cohort-statistics-valid.json: origin counts drifted from evaluator register"
        )
    if (
        _integer(
            cohort.get("observed_sessions"),
            "cohort-statistics-valid.json.observed_sessions",
        )
        != observed_sessions
    ):
        raise DossierError("cohort-statistics-valid.json: observed sessions drifted from evaluator")
    diagnostics = cohort.get("episode_diagnostics")
    if (
        not isinstance(diagnostics, dict)
        or _integer(
            diagnostics.get("matured_episode_count"),
            "cohort-statistics-valid.json.episode_diagnostics.matured_episode_count",
        )
        != expected_counts["matured"]
    ):
        raise DossierError(
            "cohort-statistics-valid.json: matured episode count drifted from register"
        )
    cohort_crosswalk = {
        "fill_fraction_within_5_sessions": cohort.get("fill_fraction_within_5_sessions"),
        "policy_breach_count": cohort.get("policy_breach_count"),
        "mandate_drawdown_breach_count": cohort.get("mandate_drawdown_breach_count"),
        "strategy_inputs_complete": cohort.get("strategy_inputs_complete"),
        "all_registered_origins_retained": cohort.get("controls", {}).get(
            "all_registered_origins_retained"
        ),
        "familywise_diagnostic_passed": cohort.get("multiple_testing", {}).get(
            "family_adjusted_pass"
        ),
    }
    for field, cohort_value in cohort_crosswalk.items():
        if strategy_evidence.get(field) != cohort_value:
            raise DossierError(
                f"paper-episode-golden.json: strategy evidence {field} drifted "
                "from cohort statistics"
            )
    bootstrap_results = cohort.get("bootstrap_results", [])
    by_comparison = {
        result.get("comparison"): result for result in bootstrap_results if isinstance(result, dict)
    }
    for comparison, field in (
        ("HOLD", "bootstrap_lower_bound_vs_hold"),
        ("XJO_TR", "bootstrap_lower_bound_vs_xjo_tr"),
    ):
        result = by_comparison.get(comparison)
        if not isinstance(result, dict):
            raise DossierError(
                f"cohort-statistics-valid.json: missing {comparison} bootstrap result"
            )
        if result.get("status") != strategy_evidence.get("bootstrap_status"):
            raise DossierError(
                f"paper-episode-golden.json: {comparison} bootstrap status drifted "
                "from cohort statistics"
            )
        if result.get("one_sided_lower_bound") != strategy_evidence.get(field):
            raise DossierError(
                f"paper-episode-golden.json: {comparison} bootstrap bound drifted "
                "from cohort statistics"
            )


def _validate_model_a_archive_semantics(fixtures: dict[str, Any]) -> None:
    """Recompute the synthetic M-A1 archive/restore proof instead of trusting flags."""
    manifest = fixtures.get("model-a-archive-manifest-valid.json")
    restore = fixtures.get("model-a-archive-restore-evidence-valid.json")
    if not isinstance(manifest, dict) or not isinstance(restore, dict):
        raise DossierError(
            "Model A archive semantics require manifest and restore-evidence fixtures"
        )

    manifest_label = "model-a-archive-manifest-valid.json"
    restore_label = "model-a-archive-restore-evidence-valid.json"
    manifest_controls = manifest.get("controls")
    restore_controls = restore.get("controls")
    expected_manifest_controls = {
        "mission_mode": "READ_ONLY_ARCHIVE",
        "source_snapshot_read_only": True,
        "source_mutation_performed": False,
        "production_configuration_change": False,
        "runtime_shutdown_claimed": False,
        "runtime_change_authority": "ABSENT",
        "production_evidence_claimed": False,
        "runtime_retirement_approval_claimed": False,
        "destructive_action": False,
        "non_executable": True,
    }
    expected_restore_controls = {
        "attended": True,
        "isolated": True,
        "production_environment": False,
        "read_only": True,
        "production_write": False,
        "archive_write": False,
        "archive_mutation": False,
        "destructive_action": False,
        "runtime_shutdown_claimed": False,
        "production_evidence_claimed": False,
        "runtime_retirement_approval_claimed": False,
        "non_executable": True,
    }
    if manifest_controls != expected_manifest_controls:
        raise DossierError(f"{manifest_label}: unsafe or overstated M-A1 controls")
    if restore_controls != expected_restore_controls:
        raise DossierError(f"{restore_label}: unsafe or overstated restore controls")
    if (
        manifest.get("evidence_scope") != "SYNTHETIC_GOLDEN"
        or manifest.get("deployment_environment") != "synthetic-test"
        or restore.get("evidence_scope") != "SYNTHETIC_GOLDEN"
    ):
        raise DossierError("Model A archive golden fixtures may not masquerade as production")
    if (
        manifest.get("writer_state_at_snapshot") != "ACTIVE"
        or manifest.get("writer_disabled_at") is not None
    ):
        raise DossierError(
            f"{manifest_label}: SEALED golden archive must not claim writer shutdown"
        )
    if manifest.get("manifest_status") != "SEALED" or manifest.get("reason_codes") != []:
        raise DossierError(f"{manifest_label}: golden manifest must be SEALED without reasons")

    source_started = _timestamp(
        manifest.get("source_snapshot_started_at"),
        f"{manifest_label}.source_snapshot_started_at",
    )
    source_completed = _timestamp(
        manifest.get("source_snapshot_completed_at"),
        f"{manifest_label}.source_snapshot_completed_at",
    )
    manifest_created = _timestamp(manifest.get("created_at"), f"{manifest_label}.created_at")
    secret_scan = manifest.get("secret_scan")
    if not isinstance(secret_scan, dict):
        raise DossierError(f"{manifest_label}: missing secret_scan")
    secret_scan_completed = _timestamp(
        secret_scan.get("completed_at"),
        f"{manifest_label}.secret_scan.completed_at",
    )
    restore_started = _timestamp(restore.get("started_at"), f"{restore_label}.started_at")
    restore_completed = _timestamp(restore.get("completed_at"), f"{restore_label}.completed_at")
    restore_created = _timestamp(restore.get("created_at"), f"{restore_label}.created_at")
    if not (
        source_started
        <= source_completed
        <= secret_scan_completed
        <= manifest_created
        <= restore_started
        <= restore_completed
        <= restore_created
    ):
        raise DossierError("Model A archive/restore chronology is not monotonic")
    if _timestamp(
        manifest.get("data_as_of"), f"{manifest_label}.data_as_of"
    ) != source_started or restore.get("data_as_of") != manifest.get("data_as_of"):
        raise DossierError("Model A archive/restore data_as_of does not pin the source snapshot")

    expected_classes = manifest.get("expected_classes")
    archive_classes = manifest.get("archive_classes")
    if not isinstance(expected_classes, list) or not all(
        isinstance(value, str) for value in expected_classes
    ):
        raise DossierError(f"{manifest_label}.expected_classes: invalid class set")
    if expected_classes != sorted(expected_classes) or len(expected_classes) != len(
        set(expected_classes)
    ):
        raise DossierError(f"{manifest_label}.expected_classes: must be sorted and unique")
    if not isinstance(archive_classes, list) or not all(
        isinstance(value, dict) for value in archive_classes
    ):
        raise DossierError(f"{manifest_label}.archive_classes: invalid class records")
    class_names = [record.get("dataset_or_artifact_class") for record in archive_classes]
    if class_names != expected_classes:
        raise DossierError(
            f"{manifest_label}.archive_classes: class order/set does not match expected_classes"
        )

    archive_id = manifest.get("archive_id")
    manifest_as_of = _timestamp(manifest.get("data_as_of"), f"{manifest_label}.data_as_of")
    locators: list[str] = []
    for index, record in enumerate(archive_classes):
        class_label = f"{manifest_label}.archive_classes[{index}]"
        class_name = record.get("dataset_or_artifact_class")
        expected_class_id = (
            f"{archive_id}:{class_name.lower()}" if isinstance(class_name, str) else None
        )
        if record.get("archive_class_id") != expected_class_id:
            raise DossierError(f"{class_label}.archive_class_id: identity drift")
        locator = record.get("logical_locator")
        if not isinstance(locator, str):
            raise DossierError(f"{class_label}.logical_locator: invalid locator")
        locators.append(locator)
        identities = record.get("model_identities")
        if (
            not isinstance(identities, list)
            or not all(isinstance(value, str) for value in identities)
            or identities != sorted(identities)
            or len(identities) != len(set(identities))
        ):
            raise DossierError(f"{class_label}.model_identities: must be sorted and unique")
        for field in ("record_count", "file_count", "raw_byte_count"):
            if _integer(record.get(field), f"{class_label}.{field}") < 0:
                raise DossierError(f"{class_label}.{field}: cannot be negative")
        observed_range = record.get("observed_range")
        if not isinstance(observed_range, dict):
            raise DossierError(f"{class_label}.observed_range: expected an object")
        range_field = observed_range.get("range_field")
        minimum = observed_range.get("minimum_observed_at")
        maximum = observed_range.get("maximum_observed_at")
        if range_field is None:
            if minimum is not None or maximum is not None:
                raise DossierError(f"{class_label}.observed_range: null range is inconsistent")
        else:
            minimum_at = _timestamp(minimum, f"{class_label}.minimum_observed_at")
            maximum_at = _timestamp(maximum, f"{class_label}.maximum_observed_at")
            if minimum_at > maximum_at or maximum_at > manifest_as_of:
                raise DossierError(f"{class_label}.observed_range: invalid or future range")
        if record.get("class_status") != "COMPLETE" or record.get("reason_codes") != []:
            raise DossierError(f"{class_label}: SEALED archive class is not complete")
    if len(locators) != len(set(locators)):
        raise DossierError(f"{manifest_label}.archive_classes: logical locators must be unique")

    manifest_digest = _canonical_hash_identity(manifest, manifest_label)
    expected_manifest_ref = {
        "contract_name": "model-a-archive-manifest-v1",
        "artifact_id": archive_id,
        "schema_version": manifest.get("schema_version"),
        "sha256": manifest_digest,
        "created_at": manifest.get("created_at"),
    }
    if restore.get("manifest_ref") != expected_manifest_ref:
        raise DossierError(f"{restore_label}.manifest_ref: does not resolve exact manifest")
    restore_source_hashes = restore.get("source_hashes")
    if (
        not isinstance(restore_source_hashes, list)
        or len(restore_source_hashes) != 1
        or restore_source_hashes[0].get("sha256") != manifest_digest
    ):
        raise DossierError(f"{restore_label}.source_hashes: manifest digest is not exact")
    attempt = _integer(restore.get("attempt_sequence"), f"{restore_label}.attempt_sequence")
    if restore.get("restore_evidence_id") != f"{archive_id}:restore:{attempt}":
        raise DossierError(f"{restore_label}.restore_evidence_id: identity drift")

    comparisons = restore.get("comparisons")
    if not isinstance(comparisons, list) or not all(
        isinstance(value, dict) for value in comparisons
    ):
        raise DossierError(f"{restore_label}.comparisons: invalid comparison records")
    comparison_names = [row.get("dataset_or_artifact_class") for row in comparisons]
    if comparison_names != expected_classes or len(comparisons) != len(archive_classes):
        raise DossierError(
            f"{restore_label}.comparisons: order/set does not match archive manifest"
        )

    all_match = True
    for index, (record, comparison) in enumerate(zip(archive_classes, comparisons, strict=True)):
        comparison_label = f"{restore_label}.comparisons[{index}]"
        if comparison.get("archive_class_id") != record.get("archive_class_id") or comparison.get(
            "dataset_or_artifact_class"
        ) != record.get("dataset_or_artifact_class"):
            raise DossierError(f"{comparison_label}: archive class identity drift")
        count_match = all(
            comparison.get(observed_field) == record.get(expected_field)
            for observed_field, expected_field in (
                ("observed_record_count", "record_count"),
                ("observed_file_count", "file_count"),
                ("observed_raw_byte_count", "raw_byte_count"),
            )
        )
        range_match = comparison.get("observed_range") == record.get("observed_range")
        raw_hash_match = comparison.get("observed_raw_sha256") == record.get("raw_sha256")
        canonical_hash_match = comparison.get("observed_canonical_sha256") == record.get(
            "canonical_sha256"
        )
        recomputed = {
            "count_match": count_match,
            "range_match": range_match,
            "raw_hash_match": raw_hash_match,
            "canonical_hash_match": canonical_hash_match,
        }
        for field, expected in recomputed.items():
            if comparison.get(field) is not expected:
                raise DossierError(
                    f"{comparison_label}.{field}: producer flag disagrees with recomputation"
                )
        comparison_matches = all(recomputed.values())
        expected_result = "MATCH" if comparison_matches else "MISMATCH"
        if comparison.get("comparison_result") != expected_result:
            raise DossierError(
                f"{comparison_label}.comparison_result: disagrees with recomputation"
            )
        reasons = comparison.get("reason_codes")
        if (comparison_matches and reasons != []) or (
            not comparison_matches and (not isinstance(reasons, list) or not reasons)
        ):
            raise DossierError(f"{comparison_label}.reason_codes: inconsistent result evidence")
        all_match = all_match and comparison_matches

    if (restore.get("verdict") == "PASS") != all_match:
        raise DossierError(f"{restore_label}.verdict: PASS disagrees with recomputed comparisons")
    if all_match and restore.get("reason_codes") != []:
        raise DossierError(f"{restore_label}.reason_codes: PASS must have no reasons")


def _validate_promotion_semantics(fixtures: dict[str, Any]) -> None:
    decision = fixtures.get("promotion-decision-valid.json")
    if not isinstance(decision, dict):
        raise DossierError("promotion-decision-valid.json: fixture must be an object")
    requested = decision.get("requested_evidence_tier")
    permitted = decision.get("permitted_evidence_tier")
    action = decision.get("decision")
    gates = decision.get("gate_evidence")
    if not isinstance(gates, dict):
        raise DossierError("promotion-decision-valid.json: missing gate evidence")
    if action == "APPROVE_EVIDENCE_BACKED_LANGUAGE":
        if (
            requested != "EVIDENCE_BACKED"
            or permitted != "EVIDENCE_BACKED"
            or gates.get("operational_gate_passed") is not True
            or gates.get("strategy_gate_passed") is not True
            or gates.get("evidence_complete") is not True
            or decision.get("decided_by") != "James"
        ):
            raise DossierError(
                "promotion-decision-valid.json: EVIDENCE_BACKED lacks James approval "
                "or complete gates"
            )
    elif action == "APPROVE_UNCALIBRATED_VISIBILITY":
        if (
            requested != "UNCALIBRATED"
            or permitted != "UNCALIBRATED"
            or gates.get("operational_gate_passed") is not True
            or gates.get("strategy_gate_passed") is not False
            or decision.get("decided_by") != "James"
        ):
            raise DossierError(
                "promotion-decision-valid.json: UNCALIBRATED promotion prerequisites fail"
            )
    elif action in {"HOLD_PAPER_ONLY", "REJECT_PROMOTION"}:
        if permitted != "PAPER_ONLY":
            raise DossierError(
                "promotion-decision-valid.json: held/rejected promotion must remain PAPER_ONLY"
            )
    else:
        raise DossierError(f"promotion-decision-valid.json: unknown promotion decision {action!r}")
    evaluated_at = _timestamp(
        gates.get("evaluated_at"),
        "promotion-decision-valid.json.gate_evidence.evaluated_at",
    )
    decided_at = _timestamp(decision.get("decided_at"), "promotion-decision-valid.json.decided_at")
    if decided_at < evaluated_at:
        raise DossierError(
            "promotion-decision-valid.json: decision predates evaluated gate evidence"
        )


def validate_fixture_semantics(fixtures: dict[str, Any], store: SchemaStore | None = None) -> None:
    """Apply cross-contract invariants that JSON Schema cannot express."""
    schema_store = store if store is not None else SchemaStore(SCHEMA_DIR)
    _validate_contract_name_references(fixtures, schema_store)
    _validate_fixture_chronology(fixtures)
    _validate_numeric_wire_shapes(fixtures)
    _validate_origin_snapshot_semantics(fixtures)
    _validate_fixture_hash_convention(fixtures)
    _validate_locally_resolvable_reference_hashes(fixtures)
    _validate_review_semantics(fixtures)
    _validate_lineage_semantics(fixtures)
    _validate_accounting_semantics(fixtures)
    _validate_portfolio_semantics(fixtures)
    _validate_staging_semantics(fixtures)
    _validate_evaluator_semantics(fixtures)
    _validate_model_a_archive_semantics(fixtures)
    _validate_promotion_semantics(fixtures)


def _validate_fixtures(store: SchemaStore) -> int:
    fixtures = load_fixture_documents()
    count = 0
    for filename, instance in fixtures.items():
        path = FIXTURE_DIR / filename
        label = str(path.relative_to(ROOT))
        if filename == "synthetic-evidence.json":
            if instance.get("synthetic") is not True:
                raise DossierError(f"{label}: must be explicitly synthetic")
            for index, evidence in enumerate(instance.get("evidence", [])):
                store.validate_fragment(
                    evidence,
                    SCHEMA_DIR / "review-context-v1.schema.json",
                    "#/$defs/evidenceSnapshot",
                    f"{label}.evidence[{index}]",
                )
            count += 1
            continue

        for item_label, item in _fixture_items(instance, label):
            contract_name = item.get("contract_name")
            if not isinstance(contract_name, str):
                raise DossierError(f"{item_label}: missing contract_name")
            schema_path = SCHEMA_DIR / f"{contract_name}.schema.json"
            if not schema_path.exists():
                raise DossierError(f"{item_label}: no schema for {contract_name!r}")
            store.validate(item, schema_path, item_label)
            for value_path, value in _walk_values(item):
                if isinstance(value, float):
                    raise DossierError(
                        f"{item_label}: JSON float at {value_path}; use Decimal string"
                    )
                if isinstance(value, str):
                    matches = _fixture_forbidden_tokens(value, contract_name)
                    if matches:
                        raise DossierError(
                            f"{item_label}: forbidden capital coupling token(s) "
                            f"{matches} at {value_path}"
                        )
        count += 1

    validate_fixture_semantics(fixtures, store)
    review_batch = _load_json(FIXTURE_DIR / "reviewer-assessments-blind.json")
    roles = {item["role"] for item in review_batch}
    if roles != REVIEW_ROLES:
        raise DossierError(f"blind-review fixture roles drifted: expected {sorted(REVIEW_ROLES)}")
    if len({item["assessment_id"] for item in review_batch}) != len(review_batch):
        raise DossierError("blind-review fixture assessment IDs must be unique")
    if any("peer" in _canonical(item).lower() for item in review_batch):
        raise DossierError("blind first-pass fixture must not contain peer assessments")
    return count


def _validate_markdown_links() -> int:
    markdown_paths = [*sorted(PROGRAM.rglob("*.md")), ROADMAP_VIEW_PATH]
    checked = 0
    for path in markdown_paths:
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group(1).strip()
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            target_without_fragment = raw_target.split("#", 1)[0]
            if not target_without_fragment:
                continue
            parsed = urlparse(target_without_fragment)
            if parsed.scheme or target_without_fragment.startswith("//"):
                continue
            target = (path.parent / unquote(target_without_fragment)).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError as exc:
                raise DossierError(
                    f"{path.relative_to(ROOT)}: link escapes repository: {raw_target}"
                ) from exc
            if not target.exists():
                raise DossierError(f"{path.relative_to(ROOT)}: broken local link {raw_target!r}")
            checked += 1
    return checked


def _validate_sprint_documents(roadmap: dict[str, Any]) -> None:
    sprint_paths = sorted((PROGRAM / "sprints").glob("*.md"))
    if len(sprint_paths) != 12:
        raise DossierError(f"expected exactly 12 sprint files, found {len(sprint_paths)}")
    required_sections = ("## Observability", "## Rollback", "## Definition of Done")
    for sprint, path in zip(roadmap["sprints"], sprint_paths, strict=True):
        text = path.read_text(encoding="utf-8")
        if not text.startswith(f"# {sprint['id']}"):
            raise DossierError(f"{path.relative_to(ROOT)}: heading does not match {sprint['id']}")
        missing = [section for section in required_sections if section not in text]
        if missing:
            raise DossierError(f"{path.relative_to(ROOT)}: missing sections {missing}")
        if "## Implementation sequence" not in text and "## Mission decomposition" not in text:
            raise DossierError(
                f"{path.relative_to(ROOT)}: must define an implementation sequence "
                "or mission decomposition"
            )
        if "Model A" not in text or "broker" not in text.lower():
            raise DossierError(
                f"{path.relative_to(ROOT)}: must state Model A and broker boundaries"
            )


def _validate_model_a_decommission_controls(
    template: str,
    command: str,
    s01_text: str,
    registry_text: str,
    prompt_paths: list[Path],
) -> None:
    if not MODEL_A_DECOMMISSION_PATH.exists():
        raise DossierError(
            f"mission control is missing: {MODEL_A_DECOMMISSION_PATH.relative_to(ROOT)}"
        )
    decommission = MODEL_A_DECOMMISSION_PATH.read_text(encoding="utf-8")
    docs_index_path = ROOT / "docs/README.md"
    docs_index = docs_index_path.read_text(encoding="utf-8")

    template_tokens = (
        MODEL_A_FAIL_CLOSED_TOKEN,
        'model_a_runtime_target: "decommissioned_after_explicit_James_approval"',
        'model_a_history_retention: "checksummed_read_only_audit"',
        "model_a_decommission_requires_separate_james_approval: true",
        "model_a_decommission_approved: false",
        "model_a_decommission_contract: "
        '"docs/programs/investment-engine/model-a-decommission.md"',
        *MODEL_A_M02_RECORD_PATHS,
    )
    for token in template_tokens:
        if token not in template:
            raise DossierError(
                f"{MISSION_TEMPLATE_PATH.relative_to(ROOT)}: missing Model A "
                f"decommission control {token!r}"
            )

    command_tokens = (
        MODEL_A_FAIL_CLOSED_TOKEN,
        "model-a-decommission.md",
        "James approval",
        "checksummed read-only archive",
        "no-write",
        *MODEL_A_M02_RECORD_PATHS,
    )
    for token in command_tokens:
        if token not in command:
            raise DossierError(
                f"{SPRINT_COMMAND_PATH.relative_to(ROOT)}: missing Model A "
                f"decommission control {token!r}"
            )

    for path, text in (
        (SPRINT_COMMAND_PATH, command),
        (
            PROGRAM / "sprints/s01-programme-guardrails-and-proposal-registry.md",
            s01_text,
        ),
        (PROGRAM / "contracts/proposal-registry.md", registry_text),
    ):
        if MODEL_A_FAIL_CLOSED_TOKEN not in text:
            raise DossierError(
                f"{path.relative_to(ROOT)}: legacy Model A path must fail closed with "
                f"{MODEL_A_FAIL_CLOSED_TOKEN}"
            )
        normalized = text.lower().replace("-", " ")
        if "fail closed" not in normalized:
            raise DossierError(
                f"{path.relative_to(ROOT)}: legacy Model A path must state fail-closed " "semantics"
            )

    for prompt_path in (
        path for path in prompt_paths if path.name in {"sprint-start.md", "sprint-close.md"}
    ):
        prompt = prompt_path.read_text(encoding="utf-8")
        normalized = prompt.lower().replace("-", " ")
        for concept in ("archive", "approval", "no write", "fail closed"):
            if concept not in normalized:
                raise DossierError(
                    f"{prompt_path.relative_to(ROOT)}: missing Model A mission concept "
                    f"{concept!r}"
                )

    normalized_contract = decommission.lower().replace("-", " ")
    for phrase in (
        "recommended target state",
        "separate james approved mission",
        "does not authorise",
        "destructive data deletion",
        "production configuration changes",
        "migration apply",
        "deploy",
        "checksummed, read only audit archive",
        "no write proof",
        "not ready",
    ):
        if phrase not in normalized_contract:
            raise DossierError(
                f"{MODEL_A_DECOMMISSION_PATH.relative_to(ROOT)}: missing fail-closed "
                f"decommission boundary {phrase!r}"
            )

    forbidden_passive_tokens = (
        "passive_observation_only_until_S04",
        "LEGACY OBSERVATION — PAPER_ONLY — NOT CAPITAL AUTHORITATIVE",
    )
    for path, text in (
        (MISSION_TEMPLATE_PATH, template),
        (SPRINT_COMMAND_PATH, command),
        (
            PROGRAM / "sprints/s01-programme-guardrails-and-proposal-registry.md",
            s01_text,
        ),
        (PROGRAM / "contracts/proposal-registry.md", registry_text),
        (docs_index_path, docs_index),
    ):
        stale = [token for token in forbidden_passive_tokens if token in text]
        if path == docs_index_path and "legacy observation" in text.lower():
            stale.append("legacy observation")
        if stale:
            raise DossierError(
                f"{path.relative_to(ROOT)}: passive Model A target is superseded; "
                f"remove {stale}"
            )
    for token in (MODEL_A_FAIL_CLOSED_TOKEN, "model-a-decommission.md"):
        if token not in docs_index:
            raise DossierError(
                f"{docs_index_path.relative_to(ROOT)}: missing Model A decommission "
                f"index token {token!r}"
            )


def _validate_mission_controls() -> int:
    """Keep the executable S01 mission boundary aligned across entry points."""
    _require_paths(TAILORED_OUTPUT_AUTHORITY_DOCUMENTS, "tailored-output authority")

    s01_path = PROGRAM / "sprints/s01-programme-guardrails-and-proposal-registry.md"
    registry_path = PROGRAM / "contracts/proposal-registry.md"
    prompt_paths = sorted((PROGRAM / "prompts").glob("*.md"))
    control_paths = [
        MISSION_TEMPLATE_PATH,
        SPRINT_COMMAND_PATH,
        s01_path,
        registry_path,
        *prompt_paths,
    ]
    for path in control_paths:
        if not path.exists():
            raise DossierError(f"mission control is missing: {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        if "S01" not in text or "PAPER_ONLY" not in text:
            raise DossierError(
                f"{path.relative_to(ROOT)}: must preserve the S01 PAPER_ONLY ceiling"
            )

    template = MISSION_TEMPLATE_PATH.read_text(encoding="utf-8")
    for token in (
        'copy_to: "docs/programs/investment-engine/missions/SXX/MXX/mission.yaml"',
        'close_record_at: "docs/programs/investment-engine/missions/SXX/MXX/close.md"',
        'maximum_evidence_tier: "PAPER_ONLY"',
        'earned_evidence_tier: "PAPER_ONLY"',
        "tailored_output_enabled: false",
        's01_instance: "docs/programs/investment-engine/missions/S01/M01/mission.yaml"',
        's01_close_record: "docs/programs/investment-engine/missions/S01/M01/close.md"',
    ):
        if token not in template:
            raise DossierError(
                f"{MISSION_TEMPLATE_PATH.relative_to(ROOT)}: missing control {token!r}"
            )
    if 'calibration_label: "UNCALIBRATED"' in template:
        raise DossierError(
            f"{MISSION_TEMPLATE_PATH.relative_to(ROOT)}: "
            "must not default missions to UNCALIBRATED"
        )

    authority_surfaces = (
        MISSION_TEMPLATE_PATH,
        SPRINT_COMMAND_PATH,
        s01_path,
        registry_path,
        PROGRAM / "prompts/sprint-start.md",
    )
    for path in authority_surfaces:
        text = path.read_text(encoding="utf-8")
        missing = [
            authority_path
            for authority_path in TAILORED_OUTPUT_AUTHORITY_DOCUMENTS
            if authority_path not in text
        ]
        if missing:
            raise DossierError(
                f"{path.relative_to(ROOT)}: missing tailored-output authority "
                f"documents {missing}"
            )

    command = SPRINT_COMMAND_PATH.read_text(encoding="utf-8")
    for token in (
        ".venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'",
        ".venv/bin/python scripts/validate_investment_program.py",
        ".venv/bin/python -m pytest tests/test_investment_program_dossier.py -q",
        "docs/programs/investment-engine/missions/SXX/MXX/mission.yaml",
        "docs/programs/investment-engine/missions/SXX/MXX/close.md",
        "docs/programs/investment-engine/missions/S01/M01/mission.yaml",
        "docs/programs/investment-engine/missions/S01/M01/close.md",
    ):
        if token not in command:
            raise DossierError(
                f"{SPRINT_COMMAND_PATH.relative_to(ROOT)}: missing command control {token!r}"
            )
    _validate_model_a_decommission_controls(
        template,
        command,
        s01_path.read_text(encoding="utf-8"),
        registry_path.read_text(encoding="utf-8"),
        prompt_paths,
    )
    return len(control_paths) + 1


def render_roadmap_view(roadmap: dict[str, Any]) -> str:
    """Render the compact human view generated from the canonical manifest."""

    lines = [
        "# Investment engine roadmap",
        "",
        "<!-- GENERATED by scripts/validate_investment_program.py; edit docs/product/roadmap.yaml. -->",
        "",
        f"**Status:** {roadmap['status']}",
        f"**Manifest:** `{roadmap['manifest_id']}`",
        f"**Baseline:** `{roadmap['baseline']['default_branch']}@{roadmap['baseline']['commit']}`",
        "**Canonical source:** [`roadmap.yaml`](roadmap.yaml)",
        "",
        "This is the compact human view of the accepted twelve-week investment-engine",
        "programme. The manifest, contracts, schemas, fixtures, and sprint work orders—not",
        "this generated page—govern implementation.",
        "",
        "## North stars",
        "",
        "| ID | Outcome | Target |",
        "|---|---|---|",
    ]
    for north_star in roadmap["north_stars"]:
        lines.append(f"| {north_star['id']} | {north_star['name']} | {north_star['target']} |")
    lines.extend(
        [
            "",
            "## Twelve-week sequence",
            "",
            "| Sprint | Outcome | Initiatives | Depends on | Maximum evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for sprint in roadmap["sprints"]:
        initiative_ids = ", ".join(sprint["initiative_ids"])
        dependencies = ", ".join(sprint["depends_on"]) or "—"
        lines.append(
            f"| {sprint['id']} | {sprint['title']} | {initiative_ids} | "
            f"{dependencies} | {sprint['maximum_evidence_tier']} |"
        )
    lines.extend(
        [
            "",
            "## Release gates",
            "",
            "| Gate | Allows | Failure state |",
            "|---|---|---|",
        ]
    )
    for gate_name, gate in roadmap["release_gates"].items():
        lines.append(f"| `{gate_name}` | {gate['allows']} | {gate['failure_state']} |")
    lines.extend(
        [
            "",
            "The operational gate requires a frozen evaluator and thirty consecutive complete",
            "sessions. An evidence-backed claim remains prohibited until the prospective",
            "strategy gate and James-controlled promotion gate both pass. No gate adds broker",
            "execution authority.",
            "",
            "## Delivery envelope",
            "",
            f"- Surfaces: {'; '.join(roadmap['delivery_policy']['surfaces'])}.",
            f"- Excluded surfaces: {'; '.join(roadmap['delivery_policy']['excluded_surfaces'])}.",
            f"- Execution boundary: {roadmap['delivery_policy']['execution_boundary']}",
            f"- Model routing: {roadmap['delivery_policy']['model_routing']}",
            f"- Pull-request budget: {roadmap['delivery_policy']['pull_request_budget']}",
            "- James is the sole user, policy governor, approver, and external order placer.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_program(*, require_generated_view: bool = True) -> dict[str, int]:
    store = SchemaStore(SCHEMA_DIR)
    store.lint()

    roadmap = _load_json(ROADMAP_PATH)
    if not isinstance(roadmap, dict):
        raise DossierError("docs/product/roadmap.yaml must contain a JSON object")
    _validate_roadmap(roadmap, store)
    _validate_capital_schema_boundaries(store, roadmap)
    _validate_sprint_documents(roadmap)
    mission_control_count = _validate_mission_controls()
    fixture_count = _validate_fixtures(store)
    link_count = _validate_markdown_links()

    expected_view = render_roadmap_view(roadmap)
    if require_generated_view:
        if not ROADMAP_VIEW_PATH.exists():
            raise DossierError(
                "generated roadmap view is missing; run "
                ".venv/bin/python scripts/validate_investment_program.py "
                "--write-roadmap-view"
            )
        actual_view = ROADMAP_VIEW_PATH.read_text(encoding="utf-8")
        if actual_view != expected_view:
            raise DossierError("docs/product/investment-engine-roadmap.md is stale; regenerate it")

    return {
        "schemas": len(store.by_path),
        "fixtures": fixture_count,
        "sprints": len(roadmap["sprints"]),
        "initiatives": len(roadmap["initiatives"]),
        "contracts": len(required_contract_names(roadmap)),
        "mission_controls": mission_control_count,
        "links": link_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-roadmap-view",
        action="store_true",
        help="regenerate the compact roadmap view from docs/product/roadmap.yaml",
    )
    parser.add_argument(
        "--write-fixture-hashes",
        action="store_true",
        help=(
            "mechanically recompute root fixture canonical_hash values; "
            "validation never rewrites them implicitly"
        ),
    )
    args = parser.parse_args(argv)

    try:
        if args.write_fixture_hashes:
            repaired = write_fixture_hashes()
            print(f"investment-engine dossier: repaired {repaired} root fixture hash(es)")
        if args.write_roadmap_view:
            roadmap = _load_json(ROADMAP_PATH)
            if not isinstance(roadmap, dict):
                raise DossierError("roadmap root must be an object")
            ROADMAP_VIEW_PATH.write_text(render_roadmap_view(roadmap), encoding="utf-8")
        report = validate_program()
    except DossierError as exc:
        print(f"investment-engine dossier: FAIL\n{exc}", file=sys.stderr)
        return 1

    print(
        "investment-engine dossier: PASS "
        f"({report['sprints']} sprints, {report['initiatives']} initiatives, "
        f"{report['contracts']} contracts, {report['schemas']} schemas, "
        f"{report['fixtures']} fixtures, {report['mission_controls']} mission controls, "
        f"{report['links']} local links)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
