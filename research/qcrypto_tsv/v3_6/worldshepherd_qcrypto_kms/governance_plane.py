"""Integrated SARA / PRIME / ECHO / OVERWATCH enforcement for QCRYPTO.

These are operational controls around the Bitcoin signing boundary.  They do not
change Bitcoin consensus.  PRIME makes the release decision, SARA enforces workflow
state transitions, ECHO binds evidence lineage, and OVERWATCH emits machine-readable
OpenMetrics from the exact decision record.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .bitcoin_quantum_policy import CryptoPolicyState
from .signing_gate import PreparedSigningGate


class GovernancePlaneError(RuntimeError):
    pass


class EmergencyMode(str, Enum):
    NORMAL = "NORMAL"
    FREEZE = "FREEZE"
    MIGRATION_ONLY = "MIGRATION_ONLY"


@dataclass(frozen=True)
class PrimePolicyProfile:
    profile_id: str
    allowed_networks: tuple[str, ...] = ("SIGNET", "REGTEST", "TESTNET4")
    require_resource_budget: bool = True
    require_pq_quorum_for_hybrid: bool = True
    require_runtime_attestation_for_pq: bool = False
    require_operator_quorum: bool = True
    minimum_operator_approvals: int = 2
    required_operator_roles: tuple[str, ...] = ("CREATOR", "OPERATOR")
    require_migration_binding: bool = False
    require_source_integrity: bool = True
    require_chain_context: bool = False
    require_emergency_state_anchor: bool = False
    emergency_mode: EmergencyMode = EmergencyMode.NORMAL

    def canonical_dict(self) -> dict:
        if not self.profile_id or len(self.profile_id) > 128:
            raise GovernancePlaneError("PRIME profile_id is required")
        networks = tuple(sorted(set(n.strip().upper() for n in self.allowed_networks)))
        if not networks or any(n not in {"SIGNET", "REGTEST", "TESTNET4"} for n in networks):
            raise GovernancePlaneError("PRIME allowed networks must be explicit non-mainnet networks")
        if self.minimum_operator_approvals < 0:
            raise GovernancePlaneError("minimum_operator_approvals must be non-negative")
        return {
            "profile_id": self.profile_id,
            "allowed_networks": networks,
            "require_resource_budget": self.require_resource_budget,
            "require_pq_quorum_for_hybrid": self.require_pq_quorum_for_hybrid,
            "require_runtime_attestation_for_pq": self.require_runtime_attestation_for_pq,
            "require_operator_quorum": self.require_operator_quorum,
            "minimum_operator_approvals": self.minimum_operator_approvals,
            "required_operator_roles": tuple(sorted(set(self.required_operator_roles))),
            "require_migration_binding": self.require_migration_binding,
            "require_source_integrity": self.require_source_integrity,
            "require_chain_context": self.require_chain_context,
            "require_emergency_state_anchor": self.require_emergency_state_anchor,
            "emergency_mode": self.emergency_mode.value,
        }

    @property
    def policy_sha256(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-PRIME-QCRYPTO-POLICY-V1\x00" + body).hexdigest()


@dataclass(frozen=True)
class PrimeDecision:
    allowed: bool
    profile_id: str
    policy_sha256: str
    intent_sha256: str
    gates: dict[str, bool]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_prime_decision(
    prepared: PreparedSigningGate,
    authorization: Mapping[str, Any],
    *,
    profile: PrimePolicyProfile,
    pq_quorum_report: Mapping[str, Any] | None = None,
    runtime_attestation_reports: Mapping[str, Mapping[str, Any]] | None = None,
    source_integrity_report: Mapping[str, Any] | None = None,
    chain_context_report: Mapping[str, Any] | None = None,
) -> PrimeDecision:
    cfg = profile.canonical_dict()
    reasons: list[str] = []
    gates: dict[str, bool] = {}
    gates["network"] = prepared.network in cfg["allowed_networks"]
    if not gates["network"]:
        reasons.append("network is not allowed by PRIME profile")
    gates["base_authorization"] = bool(authorization.get("authorized_for_local_signing_workflow"))
    if not gates["base_authorization"]:
        reasons.append("base signing authorization is not satisfied")
    gates["resource_budget"] = (prepared.resource_budget_report is not None and prepared.resource_budget_report.satisfied) if profile.require_resource_budget else True
    if not gates["resource_budget"]:
        reasons.append("resource budget evidence is required and must pass")
    hybrid = prepared.policy_state == CryptoPolicyState.HYBRID_REQUIRED
    if hybrid and profile.require_pq_quorum_for_hybrid:
        gates["pq_quorum"] = bool(pq_quorum_report and pq_quorum_report.get("satisfied") is True and pq_quorum_report.get("intent_sha256") == prepared.intent.intent_sha256)
    else:
        gates["pq_quorum"] = True
    if not gates["pq_quorum"]:
        reasons.append("verified provider-diverse PQ quorum is required")
    if hybrid and profile.require_runtime_attestation_for_pq:
        provider_ids = [p.get("provider_id") for p in (pq_quorum_report or {}).get("providers", [])]
        runtime = runtime_attestation_reports or {}
        gates["runtime_attestation"] = bool(provider_ids) and all(runtime.get(pid, {}).get("verified") is True for pid in provider_ids)
    else:
        gates["runtime_attestation"] = True
    if not gates["runtime_attestation"]:
        reasons.append("verified runtime attestation is required for every PQ provider")
    q = authorization.get("operator_quorum") or {}
    if profile.require_operator_quorum:
        roles = set(q.get("roles", []))
        gates["operator_quorum"] = bool(q.get("satisfied")) and int(q.get("verified_count", 0)) >= profile.minimum_operator_approvals and set(profile.required_operator_roles).issubset(roles)
    else:
        gates["operator_quorum"] = True
    if not gates["operator_quorum"]:
        reasons.append("operator quorum does not meet PRIME count/role requirements")
    gates["migration_binding"] = bool(prepared.migration_binding_sha256 and prepared.migration_report and prepared.migration_report.get("satisfied")) if profile.require_migration_binding else True
    if not gates["migration_binding"]:
        reasons.append("migration-only profile requires a validated migration reservation binding")
    gates["source_integrity"] = bool(source_integrity_report and source_integrity_report.get("satisfied") is True) if profile.require_source_integrity else True
    if profile.require_chain_context:
        bound = prepared.chain_context_sha256
        gates["chain_context"] = bool(
            bound and chain_context_report and chain_context_report.get("satisfied") is True
            and chain_context_report.get("chain_context_sha256") == bound
            and chain_context_report.get("txid") == prepared.txid
            and str(chain_context_report.get("network", "")).upper() == prepared.network
        )
    else:
        gates["chain_context"] = True
    if not gates["chain_context"]:
        reasons.append("live chain/UTXO context is required and must be bound to this transaction")
    if not gates["source_integrity"]:
        reasons.append("source-integrity/dependency gate is required and did not pass")
    if profile.emergency_mode == EmergencyMode.FREEZE:
        gates["emergency_mode"] = False
        reasons.append("PRIME emergency FREEZE blocks signing release")
    elif profile.emergency_mode == EmergencyMode.MIGRATION_ONLY:
        gates["emergency_mode"] = bool(prepared.migration_binding_sha256 and prepared.migration_report and prepared.migration_report.get("satisfied"))
        if not gates["emergency_mode"]:
            reasons.append("PRIME emergency MIGRATION_ONLY permits only reserved migration transactions")
    else:
        gates["emergency_mode"] = True
    return PrimeDecision(
        allowed=all(gates.values()),
        profile_id=profile.profile_id,
        policy_sha256=profile.policy_sha256,
        intent_sha256=prepared.intent.intent_sha256,
        gates=gates,
        reasons=tuple(reasons),
    )


class SaraWorkflowState(str, Enum):
    PREPARED = "PREPARED"
    PRIME_APPROVED = "PRIME_APPROVED"
    PQ_AUTHORIZED = "PQ_AUTHORIZED"
    OPERATOR_APPROVED = "OPERATOR_APPROVED"
    RELEASED = "RELEASED"
    EVIDENCE_COMMITTED = "EVIDENCE_COMMITTED"
    BLOCKED = "BLOCKED"


_ALLOWED_TRANSITIONS = {
    None: {SaraWorkflowState.PREPARED},
    SaraWorkflowState.PREPARED: {SaraWorkflowState.PQ_AUTHORIZED, SaraWorkflowState.OPERATOR_APPROVED, SaraWorkflowState.BLOCKED},
    SaraWorkflowState.PQ_AUTHORIZED: {SaraWorkflowState.OPERATOR_APPROVED, SaraWorkflowState.BLOCKED},
    SaraWorkflowState.OPERATOR_APPROVED: {SaraWorkflowState.PRIME_APPROVED, SaraWorkflowState.BLOCKED},
    SaraWorkflowState.PRIME_APPROVED: {SaraWorkflowState.RELEASED, SaraWorkflowState.BLOCKED},
    SaraWorkflowState.RELEASED: {SaraWorkflowState.EVIDENCE_COMMITTED, SaraWorkflowState.BLOCKED},
    SaraWorkflowState.EVIDENCE_COMMITTED: set(),
    SaraWorkflowState.BLOCKED: set(),
}


class SaraWorkflowJournal:
    """Append-only, hash-chained workflow state machine with stale-writer protection."""

    def __init__(self, path: str | os.PathLike, *, workflow_id: str) -> None:
        if not workflow_id or len(workflow_id) > 128:
            raise GovernancePlaneError("workflow_id is required")
        self.path = Path(path)
        self.workflow_id = workflow_id
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise GovernancePlaneError("SARA workflow path/parent must not be a symlink")

    def _lock(self, *, exclusive: bool):
        if self.lock_path.is_symlink():
            raise GovernancePlaneError("SARA workflow lock path must not be a symlink")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.lock_path, flags, 0o600)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise GovernancePlaneError("SARA workflow lock must be a regular file")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        return fd

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        st = self.path.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
            raise GovernancePlaneError("SARA workflow journal must be a private regular file")
        rows: list[dict] = []
        previous = "0" * 64
        for line_no, line in enumerate(self.path.read_text().splitlines(), 1):
            try:
                row = json.loads(line)
            except Exception as exc:
                raise GovernancePlaneError(f"invalid SARA workflow JSON at line {line_no}") from exc
            claimed = row.pop("record_hash", None)
            expected = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if claimed != expected or row.get("previous_hash") != previous or row.get("sequence") != line_no or row.get("workflow_id") != self.workflow_id:
                raise GovernancePlaneError(f"SARA workflow chain validation failed at line {line_no}")
            row["record_hash"] = claimed
            previous = claimed
            rows.append(row)
        return rows

    def append(self, state: SaraWorkflowState, payload: Mapping[str, Any], *, expected_sequence: int) -> dict:
        lock_fd = self._lock(exclusive=True)
        try:
            rows = self._read()
            if len(rows) != expected_sequence:
                raise GovernancePlaneError("stale SARA workflow writer sequence")
            previous_state = SaraWorkflowState(rows[-1]["state"]) if rows else None
            if state not in _ALLOWED_TRANSITIONS[previous_state]:
                raise GovernancePlaneError(f"invalid SARA workflow transition {previous_state} -> {state}")
            payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            base = {
                "schema": "WS-SARA-QCRYPTO-WORKFLOW-RECORD-V1",
                "workflow_id": self.workflow_id,
                "sequence": len(rows) + 1,
                "previous_hash": rows[-1]["record_hash"] if rows else "0" * 64,
                "state": state.value,
                "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
            record = {**base, "record_hash": hashlib.sha256(json.dumps(base, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(self.path, flags, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            return record
        finally:
            os.close(lock_fd)

    def verify(self) -> dict:
        lock_fd = self._lock(exclusive=False)
        try:
            rows = self._read()
            return {
                "valid": True,
                "records": len(rows),
                "state": rows[-1]["state"] if rows else None,
                "tip_hash": rows[-1]["record_hash"] if rows else "0" * 64,
            }
        finally:
            os.close(lock_fd)


@dataclass(frozen=True)
class EchoEvidenceBundle:
    intent_sha256: str
    psbt_sha256: str
    signing_policy_sha256: str
    prime_policy_sha256: str
    prime_allowed: bool
    pq_quorum_sha256: str | None
    resource_policy_sha256: str | None
    migration_binding_sha256: str | None
    chain_context_sha256: str | None
    emergency_state_tip_sha256: str | None
    authorization_record_hash: str | None
    sara_tip_hash: str | None
    claims: tuple[str, ...]

    def canonical_bytes(self) -> bytes:
        payload = {"schema": "WS-ECHO-QCRYPTO-EVIDENCE-V1", **asdict(self)}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def evidence_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def build_echo_evidence(
    prepared: PreparedSigningGate,
    authorization: Mapping[str, Any],
    prime_decision: PrimeDecision,
    *,
    pq_quorum_report: Mapping[str, Any] | None = None,
    sara_tip_hash: str | None = None,
    emergency_state_tip_sha256: str | None = None,
) -> EchoEvidenceBundle:
    if prime_decision.intent_sha256 != prepared.intent.intent_sha256:
        raise GovernancePlaneError("PRIME decision does not belong to prepared intent")
    return EchoEvidenceBundle(
        intent_sha256=prepared.intent.intent_sha256,
        psbt_sha256=prepared.psbt_sha256,
        signing_policy_sha256=prepared.signing_policy_sha256,
        prime_policy_sha256=prime_decision.policy_sha256,
        prime_allowed=prime_decision.allowed,
        pq_quorum_sha256=None if pq_quorum_report is None else pq_quorum_report.get("quorum_sha256"),
        resource_policy_sha256=None if prepared.resource_budget_report is None else prepared.resource_budget_report.policy_sha256,
        migration_binding_sha256=prepared.migration_binding_sha256,
        chain_context_sha256=prepared.chain_context_sha256,
        emergency_state_tip_sha256=emergency_state_tip_sha256,
        authorization_record_hash=authorization.get("authorization_ledger_record_hash"),
        sara_tip_hash=sara_tip_hash,
        claims=(
            "APPLICATION_LAYER_AUTHORIZATION_ONLY",
            "NO_BITCOIN_MAINNET_AUTHORITY",
            "NO_TRANSACTION_BROADCAST_AUTHORITY",
            "NO_BITCOIN_CONSENSUS_PQ_CLAIM",
        ),
    )


def sign_echo_evidence(bundle: EchoEvidenceBundle, private_key: Ed25519PrivateKey) -> dict:
    pub = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    sig = private_key.sign(bundle.canonical_bytes())
    return {
        "schema": "WS-ECHO-QCRYPTO-SIGNED-EVIDENCE-V1",
        "evidence": json.loads(bundle.canonical_bytes()),
        "evidence_sha256": bundle.evidence_sha256,
        "signing_algorithm": "ED25519",
        "public_key_b64url": base64.urlsafe_b64encode(pub).rstrip(b"=").decode(),
        "signature_b64url": base64.urlsafe_b64encode(sig).rstrip(b"=").decode(),
    }


def render_overwatch_openmetrics(
    *,
    prepared: PreparedSigningGate,
    authorization: Mapping[str, Any],
    prime_decision: PrimeDecision,
    pq_quorum_report: Mapping[str, Any] | None = None,
) -> str:
    """Render low-cardinality OpenMetrics suitable for an OVERWATCH collector."""
    pq_count = int((pq_quorum_report or {}).get("verified_count", 0))
    resource_ok = int(bool(prepared.resource_budget_report and prepared.resource_budget_report.satisfied))
    migration_bound = int(bool(prepared.migration_binding_sha256))
    chain_context_bound = int(bool(prepared.chain_context_sha256))
    fault_domains = int((pq_quorum_report or {}).get("fault_domain_count", 0))
    lines = [
        "# TYPE worldshepherd_qcrypto_prime_allowed gauge",
        f"worldshepherd_qcrypto_prime_allowed {1 if prime_decision.allowed else 0}",
        "# TYPE worldshepherd_qcrypto_local_signing_authorized gauge",
        f"worldshepherd_qcrypto_local_signing_authorized {1 if authorization.get('authorized_for_local_signing_workflow') else 0}",
        "# TYPE worldshepherd_qcrypto_pq_verified_providers gauge",
        f"worldshepherd_qcrypto_pq_verified_providers {pq_count}",
        "# TYPE worldshepherd_qcrypto_resource_budget_satisfied gauge",
        f"worldshepherd_qcrypto_resource_budget_satisfied {resource_ok}",
        "# TYPE worldshepherd_qcrypto_migration_binding_present gauge",
        f"worldshepherd_qcrypto_migration_binding_present {migration_bound}",
        "# TYPE worldshepherd_qcrypto_chain_context_bound gauge",
        f"worldshepherd_qcrypto_chain_context_bound {chain_context_bound}",
        "# TYPE worldshepherd_qcrypto_pq_fault_domains gauge",
        f"worldshepherd_qcrypto_pq_fault_domains {fault_domains}",
        "# TYPE worldshepherd_qcrypto_emergency_gate_open gauge",
        f"worldshepherd_qcrypto_emergency_gate_open {1 if prime_decision.gates.get('emergency_mode') else 0}",
        "# TYPE worldshepherd_qcrypto_fee_sat gauge",
        f"worldshepherd_qcrypto_fee_sat {prepared.audit.fee_sat}",
        "# TYPE worldshepherd_qcrypto_projected_signed_vsize gauge",
        f"worldshepherd_qcrypto_projected_signed_vsize {prepared.resource_budget_report.projected_signed_vsize if prepared.resource_budget_report else 0}",
        "# EOF",
    ]
    return "\n".join(lines) + "\n"
