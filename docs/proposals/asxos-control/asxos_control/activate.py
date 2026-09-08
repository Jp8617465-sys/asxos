"""Activation attestation. This module never writes AUTONOMY."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from asxos_control.hashes import is_git_sha, is_sha256, sha256_hex

GateStatus = Literal["PASS", "PARTIAL", "FAIL", "OWNER_ACTION"]
PRE_ACTIVATION_GATES = tuple(range(1, 17))  # items 1-16


@dataclass(frozen=True)
class GateEvidence:
    gate: int
    status: GateStatus
    evidence_digest: str | None
    note: str = ""


@dataclass(frozen=True)
class ActivationRecord:
    agents_md_digest: str
    verifier_commit: str
    publisher_identity: str
    state_controller_identity: str
    gates: tuple[GateEvidence, ...]


@dataclass(frozen=True)
class ActivationDecision:
    allow: bool
    reason: str


def evaluate_activation(
    record: ActivationRecord,
    *,
    agents_md_bytes: bytes,
    expected_verifier_commit: str,
    expected_publisher_identity: str,
    expected_state_controller_identity: str,
) -> ActivationDecision:
    if not agents_md_bytes:
        return ActivationDecision(False, "missing_agents_md")
    actual = sha256_hex(agents_md_bytes)
    if not is_sha256(record.agents_md_digest) or record.agents_md_digest != actual:
        return ActivationDecision(False, "agents_md_digest_mismatch")
    if not is_git_sha(record.verifier_commit) or not is_git_sha(expected_verifier_commit):
        return ActivationDecision(False, "mutable_verifier_commit")
    if record.verifier_commit != expected_verifier_commit:
        return ActivationDecision(False, "verifier_commit_mismatch")
    if record.publisher_identity != expected_publisher_identity:
        return ActivationDecision(False, "publisher_identity_mismatch")
    if record.state_controller_identity != expected_state_controller_identity:
        return ActivationDecision(False, "state_controller_identity_mismatch")
    if record.publisher_identity == record.state_controller_identity:
        return ActivationDecision(False, "state_controller_not_separated")
    seen = {gate.gate: gate for gate in record.gates}
    if set(seen) != set(PRE_ACTIVATION_GATES):
        return ActivationDecision(False, "incomplete_or_extra_gates")
    for number in PRE_ACTIVATION_GATES:
        gate = seen[number]
        if gate.status != "PASS":
            return ActivationDecision(False, f"gate_{number}_{gate.status.lower()}")
        if not gate.evidence_digest or not is_sha256(gate.evidence_digest):
            return ActivationDecision(False, f"gate_{number}_missing_evidence")
    return ActivationDecision(True, "gates_1_to_16_pass")
