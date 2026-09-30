"""End-to-end Worldshepherd QCRYPTO control plane for a local signing workflow.

This module is deliberately authorization-only: it prepares and governs a Bitcoin
PSBT but never finalizes, broadcasts, or grants mainnet authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .approval_quorum import SignedApproval
from .bitcoin_quantum_policy import CryptoPolicyState
from .chain_context import ChainContextError, validate_chain_context_report
from .emergency_state import EmergencyStateError, EmergencyStateLedger
from .crypto_agility import CryptoAgilityPolicy
from .governance_plane import (
    PrimePolicyProfile,
    SaraWorkflowJournal,
    SaraWorkflowState,
    build_echo_evidence,
    evaluate_prime_decision,
    render_overwatch_openmetrics,
    sign_echo_evidence,
)
from .key_lifecycle import KeyRegistry
from .migration_engine import MigrationBatchBinding
from .output_intent import OutputIntentPolicy
from .policy_epoch import PolicyEpochError, QuantumPolicyLedger
from .pq_quorum import (
    LatencyBudget,
    PqAuthorizationProvider,
    PqProviderAttestation,
    execute_and_verify_pq_quorum,
    verify_pq_quorum,
)
from .resource_budget import ResourceBudgetPolicy
from .signing_gate import PreparedSigningGate, SigningGateError, authorize_prepared_signing, prepare_psbt_signing
from .source_integrity import SourceIntegrityPolicy, verify_source_manifest


class ControlPlaneError(RuntimeError):
    pass


@dataclass(frozen=True)
class GovernedSigningPolicy:
    prime: PrimePolicyProfile
    crypto_agility: CryptoAgilityPolicy
    resource_budget: ResourceBudgetPolicy
    source_integrity: SourceIntegrityPolicy = SourceIntegrityPolicy()
    pq_algorithms: tuple[str, ...] = ("ML-DSA-65",)
    latency_budget: LatencyBudget = LatencyBudget()
    require_quantum_policy_anchor: bool = True
    require_external_parser_quorum: bool = False
    minimum_external_parser_libraries: int = 2
    require_external_pq_evidence: bool = False
    minimum_external_pq_execution_targets: int = 1
    require_external_pq_family_diversity: bool = False

    @property
    def policy_sha256(self) -> str:
        payload = {
            "prime_policy_sha256": self.prime.policy_sha256,
            "crypto_agility_policy_sha256": self.crypto_agility.policy_sha256,
            "resource_policy_sha256": self.resource_budget.policy_sha256,
            "source_integrity_policy_sha256": self.source_integrity.policy_sha256,
            "pq_algorithms": list(self.pq_algorithms),
            "latency_budget": asdict(self.latency_budget),
            "require_quantum_policy_anchor": self.require_quantum_policy_anchor,
            "require_external_parser_quorum": self.require_external_parser_quorum,
            "minimum_external_parser_libraries": self.minimum_external_parser_libraries,
            "require_external_pq_evidence": self.require_external_pq_evidence,
            "minimum_external_pq_execution_targets": self.minimum_external_pq_execution_targets,
            "require_external_pq_family_diversity": self.require_external_pq_family_diversity,
        }
        return hashlib.sha256(b"WS-QCRYPTO-GOVERNED-POLICY-V1\x00" + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class GovernedPreparation:
    prepared: PreparedSigningGate
    governed_policy_sha256: str
    source_integrity_report: dict
    quantum_policy_anchor: dict | None = None
    chain_context_report: dict | None = None
    emergency_state_anchor: dict | None = None

    def to_dict(self) -> dict:
        return {
            "schema": "WS-QCRYPTO-GOVERNED-PREPARATION-V1",
            "governed_policy_sha256": self.governed_policy_sha256,
            "source_integrity_report": self.source_integrity_report,
            "quantum_policy_anchor": self.quantum_policy_anchor,
            "chain_context_report": self.chain_context_report,
            "emergency_state_anchor": self.emergency_state_anchor,
            "prepared": self.prepared.to_dict(),
        }


def prepare_governed_signing(
    raw_psbt: bytes | str,
    *,
    network: str,
    policy_state: CryptoPolicyState,
    policy_epoch: str,
    max_fee_sat: int,
    authorization_nonce: str,
    expires_at: str,
    governed_policy: GovernedSigningPolicy,
    package_root: str | Path,
    source_manifest: Mapping[str, Any],
    quantum_policy_ledger: QuantumPolicyLedger | None = None,
    migration_binding: MigrationBatchBinding | None = None,
    output_intent_policy: OutputIntentPolicy | None = None,
    require_output_intent: bool = False,
    pq_recovery_output_indexes: Sequence[int] = (),
    descriptors: Sequence[str] = (),
    allowed_proprietary_prefixes: Sequence[bytes] = (),
    chain_context_report: Mapping[str, Any] | None = None,
    emergency_state_ledger: EmergencyStateLedger | None = None,
    external_parser_quorum_report: Mapping[str, Any] | None = None,
    external_pq_evidence_report: Mapping[str, Any] | None = None,
) -> GovernedPreparation:
    source_report = verify_source_manifest(package_root, source_manifest, policy=governed_policy.source_integrity)
    if not source_report["satisfied"]:
        raise ControlPlaneError("source-integrity/dependency verification failed before signing preparation")
    quantum_policy_anchor = None
    if governed_policy.require_quantum_policy_anchor:
        if quantum_policy_ledger is None:
            raise ControlPlaneError("governed policy requires a durable quantum-policy anti-rollback anchor")
        try:
            quantum_policy_anchor = quantum_policy_ledger.assert_current(policy_state=policy_state, policy_epoch=policy_epoch)
        except PolicyEpochError as exc:
            raise ControlPlaneError(str(exc)) from exc
    elif quantum_policy_ledger is not None:
        try:
            quantum_policy_anchor = quantum_policy_ledger.assert_current(policy_state=policy_state, policy_epoch=policy_epoch)
        except PolicyEpochError as exc:
            raise ControlPlaneError(str(exc)) from exc
    emergency_state_anchor = None
    if governed_policy.prime.require_emergency_state_anchor:
        if emergency_state_ledger is None:
            raise ControlPlaneError("PRIME policy requires a durable emergency-state anchor")
        try:
            emergency_state_anchor = emergency_state_ledger.assert_current(governed_policy.prime.emergency_mode)
        except EmergencyStateError as exc:
            raise ControlPlaneError(str(exc)) from exc
    elif emergency_state_ledger is not None:
        try:
            emergency_state_anchor = emergency_state_ledger.assert_current(governed_policy.prime.emergency_mode)
        except EmergencyStateError as exc:
            raise ControlPlaneError(str(exc)) from exc

    if governed_policy.prime.require_migration_binding and migration_binding is None:
        raise ControlPlaneError("governed policy requires a migration binding")
    if governed_policy.prime.require_chain_context and chain_context_report is None:
        raise ControlPlaneError("governed policy requires a verified live chain-context report")
    chain_context_sha256 = str((chain_context_report or {}).get("chain_context_sha256", "")) or None
    try:
        prepared = prepare_psbt_signing(
            raw_psbt,
            network=network,
            policy_state=policy_state,
            policy_epoch=policy_epoch,
            max_fee_sat=max_fee_sat,
            authorization_nonce=authorization_nonce,
            expires_at=expires_at,
            pq_recovery_output_indexes=pq_recovery_output_indexes,
            descriptors=descriptors,
            output_intent_policy=output_intent_policy,
            require_output_intent=require_output_intent,
            allowed_proprietary_prefixes=allowed_proprietary_prefixes,
            resource_budget_policy=governed_policy.resource_budget,
            detached_pq_algorithms=governed_policy.pq_algorithms if policy_state == CryptoPolicyState.HYBRID_REQUIRED else (),
            crypto_agility_policy=governed_policy.crypto_agility if policy_state == CryptoPolicyState.HYBRID_REQUIRED else None,
            migration_binding=migration_binding,
            chain_context_sha256=chain_context_sha256,
            external_parser_quorum_report=external_parser_quorum_report,
            require_external_parser_quorum=governed_policy.require_external_parser_quorum,
            minimum_external_parser_libraries=governed_policy.minimum_external_parser_libraries,
            external_pq_evidence_report=external_pq_evidence_report,
            require_external_pq_evidence=governed_policy.require_external_pq_evidence,
            minimum_external_pq_execution_targets=governed_policy.minimum_external_pq_execution_targets,
            require_external_pq_family_diversity=governed_policy.require_external_pq_family_diversity,
        )
    except SigningGateError as exc:
        raise ControlPlaneError(str(exc)) from exc
    if chain_context_report is not None:
        try:
            validate_chain_context_report(dict(chain_context_report), network=prepared.network, txid=prepared.txid)
        except ChainContextError as exc:
            raise ControlPlaneError(str(exc)) from exc
    return GovernedPreparation(prepared, governed_policy.policy_sha256, source_report, quantum_policy_anchor, dict(chain_context_report) if chain_context_report is not None else None, emergency_state_anchor)


def authorize_governed_signing(
    preparation: GovernedPreparation,
    *,
    governed_policy: GovernedSigningPolicy,
    approvals: Sequence[SignedApproval],
    trusted_approvers: Mapping[str, bytes],
    pq_providers: Sequence[PqAuthorizationProvider] = (),
    pq_attestations: Sequence[PqProviderAttestation] = (),
    pq_verifiers: Mapping[tuple[str, str], Any] | None = None,
    key_registry: KeyRegistry | None = None,
    runtime_attestation_reports: Mapping[str, Mapping[str, Any]] | None = None,
    authorization_ledger_path: str | None = None,
    sara_workflow_journal: SaraWorkflowJournal | None = None,
    echo_signing_key: Ed25519PrivateKey | None = None,
) -> dict:
    if preparation.governed_policy_sha256 != governed_policy.policy_sha256:
        raise ControlPlaneError("governed policy changed after preparation")
    prepared = preparation.prepared
    pq_report: dict | None = None
    timings = []
    if prepared.policy_state == CryptoPolicyState.HYBRID_REQUIRED:
        if pq_providers and pq_attestations:
            raise ControlPlaneError("choose provider execution or pre-existing attestations, not both")
        if pq_providers:
            try:
                _, pq_report, timing_rows = execute_and_verify_pq_quorum(
                    intent=prepared.intent,
                    providers=pq_providers,
                    policy=governed_policy.crypto_agility,
                    latency_budget=governed_policy.latency_budget,
                    key_registry=key_registry,
                    runtime_attestation_reports=runtime_attestation_reports,
                    require_runtime_attestation=governed_policy.prime.require_runtime_attestation_for_pq,
                )
                timings = [t.to_dict() for t in timing_rows]
            except Exception as exc:
                raise ControlPlaneError(f"PQ provider authorization failed: {exc}") from exc
        elif pq_attestations:
            if pq_verifiers is None:
                raise ControlPlaneError("trusted PQ verifiers are required for supplied attestations")
            try:
                pq_report = verify_pq_quorum(
                    intent=prepared.intent,
                    attestations=pq_attestations,
                    verifiers=pq_verifiers,
                    policy=governed_policy.crypto_agility,
                    key_registry=key_registry,
                    runtime_attestation_reports=runtime_attestation_reports,
                    require_runtime_attestation=governed_policy.prime.require_runtime_attestation_for_pq,
                )
            except Exception as exc:
                raise ControlPlaneError(f"PQ attestation verification failed: {exc}") from exc
        else:
            raise ControlPlaneError("HYBRID_REQUIRED needs a verified PQ provider quorum")

    # Establish SARA's immutable prepared state before any release decision.
    if sara_workflow_journal is not None and sara_workflow_journal.verify()["records"] == 0:
        sara_workflow_journal.append(
            SaraWorkflowState.PREPARED,
            {"intent_sha256": prepared.intent.intent_sha256, "psbt_sha256": prepared.psbt_sha256, "governed_policy_sha256": governed_policy.policy_sha256},
            expected_sequence=0,
        )
    if sara_workflow_journal is not None and pq_report is not None:
        seq = sara_workflow_journal.verify()["records"]
        sara_workflow_journal.append(SaraWorkflowState.PQ_AUTHORIZED, {"quorum_sha256": pq_report["quorum_sha256"]}, expected_sequence=seq)

    try:
        authorization = authorize_prepared_signing(
            prepared,
            pq_quorum_report=pq_report,
            approvals=approvals,
            trusted_approvers=trusted_approvers,
            required_approval_count=governed_policy.prime.minimum_operator_approvals if governed_policy.prime.require_operator_quorum else 0,
            required_approval_roles=governed_policy.prime.required_operator_roles if governed_policy.prime.require_operator_quorum else (),
            authorization_ledger_path=authorization_ledger_path,
        )
    except SigningGateError as exc:
        if sara_workflow_journal is not None:
            seq = sara_workflow_journal.verify()["records"]
            sara_workflow_journal.append(SaraWorkflowState.BLOCKED, {"reason": str(exc)}, expected_sequence=seq)
        raise ControlPlaneError(str(exc)) from exc

    if sara_workflow_journal is not None:
        seq = sara_workflow_journal.verify()["records"]
        sara_workflow_journal.append(SaraWorkflowState.OPERATOR_APPROVED, {"operator_quorum": authorization["operator_quorum"]}, expected_sequence=seq)

    prime = evaluate_prime_decision(
        prepared,
        authorization,
        profile=governed_policy.prime,
        pq_quorum_report=pq_report,
        runtime_attestation_reports=runtime_attestation_reports,
        source_integrity_report=preparation.source_integrity_report,
        chain_context_report=preparation.chain_context_report,
    )

    if sara_workflow_journal is not None:
        seq = sara_workflow_journal.verify()["records"]
        if prime.allowed:
            sara_workflow_journal.append(SaraWorkflowState.PRIME_APPROVED, prime.to_dict(), expected_sequence=seq)
            seq += 1
            sara_workflow_journal.append(SaraWorkflowState.RELEASED, {"intent_sha256": prepared.intent.intent_sha256}, expected_sequence=seq)
        else:
            sara_workflow_journal.append(SaraWorkflowState.BLOCKED, prime.to_dict(), expected_sequence=seq)

    sara_release_tip = sara_workflow_journal.verify()["tip_hash"] if sara_workflow_journal is not None else None
    echo = build_echo_evidence(
        prepared, authorization, prime, pq_quorum_report=pq_report, sara_tip_hash=sara_release_tip,
        emergency_state_tip_sha256=(preparation.emergency_state_anchor or {}).get("tip_sha256"),
    )
    signed_echo = sign_echo_evidence(echo, echo_signing_key) if echo_signing_key is not None else None

    if sara_workflow_journal is not None and prime.allowed:
        seq = sara_workflow_journal.verify()["records"]
        sara_workflow_journal.append(SaraWorkflowState.EVIDENCE_COMMITTED, {"echo_evidence_sha256": echo.evidence_sha256}, expected_sequence=seq)

    metrics = render_overwatch_openmetrics(prepared=prepared, authorization=authorization, prime_decision=prime, pq_quorum_report=pq_report)
    return {
        "schema": "WS-QCRYPTO-GOVERNED-AUTHORIZATION-V1",
        "governed_policy_sha256": governed_policy.policy_sha256,
        "intent_sha256": prepared.intent.intent_sha256,
        "authorization": authorization,
        "pq_quorum": pq_report,
        "provider_timings": timings,
        "prime_decision": prime.to_dict(),
        "release_authorized_for_local_signing": bool(prime.allowed),
        "sara_workflow": sara_workflow_journal.verify() if sara_workflow_journal is not None else None,
        "echo_evidence": json.loads(echo.canonical_bytes()),
        "echo_evidence_sha256": echo.evidence_sha256,
        "signed_echo_evidence": signed_echo,
        "overwatch_openmetrics": metrics,
        "transaction_broadcast_authorized": False,
        "mainnet_authority": False,
        "bitcoin_consensus_pq_security_established": False,
    }
