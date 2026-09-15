"""Fail-closed hybrid post-quantum authority migration controls.

This module models migration envelopes for cryptocurrency authority surfaces:
accounts, consensus validators, bridge/custody authorities, and governance/admin
keys.  It is a claims-control and readiness component only.  It does not create
keys, sign transactions, move value, modify live wallets, or authorize execution.

The model deliberately separates semantic migration readiness from end-to-end
post-quantum security.  Whole-system readiness is bounded by the weakest critical
layer; a PQ-capable account layer cannot compensate for classical consensus,
bridges, tooling, commitments, or recovery.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum

from security.qcrypto.pqc_algorithm_policy import (
    CryptoRole,
    REGISTRY,
    StandardizationState,
    validate_registry,
)


class AuthorityLayer(StrEnum):
    ACCOUNT = "ACCOUNT"
    CONSENSUS_VALIDATOR = "CONSENSUS_VALIDATOR"
    BRIDGE_CUSTODY = "BRIDGE_CUSTODY"
    GOVERNANCE_ADMIN = "GOVERNANCE_ADMIN"


class MigrationRequirement(IntEnum):
    CLASSICAL_ALLOWED = 0
    HYBRID_REQUIRED = 1
    PQ_REQUIRED = 2


class CriticalLayer(StrEnum):
    ACCOUNTS = "ACCOUNTS"
    CONSENSUS = "CONSENSUS"
    COMMITMENTS_ZK = "COMMITMENTS_ZK"
    BRIDGES_CUSTODY_ADMIN = "BRIDGES_CUSTODY_ADMIN"
    TOOLING_INTEROP = "TOOLING_INTEROP"
    RECOVERY = "RECOVERY"


class ReadinessLevel(IntEnum):
    CLASSICAL = 0
    HYBRID = 1
    PQ_CAPABLE = 2
    PQ_REQUIRED = 3


@dataclass(frozen=True)
class AuthorityEnvelope:
    network_id: str
    domain_separator: str
    payload_digest: str
    authority_id: str
    authority_layer: AuthorityLayer
    declared_requirement: MigrationRequirement
    envelope_version: int
    key_epoch: int
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None
    classical_signature_present: bool
    pq_signature_present: bool
    classical_required_for_acceptance: bool
    pq_required_for_acceptance: bool
    recovery_evidence_present: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False


@dataclass(frozen=True)
class AuthorityPolicy:
    network_id: str
    domain_separator: str
    minimum_requirement: MigrationRequirement
    minimum_envelope_version: int = 1
    minimum_key_epoch: int = 0
    require_recovery_evidence: bool = False


@dataclass(frozen=True)
class AuthorityDecision:
    verdict: str
    accepted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    authority_layer: str
    declared_requirement: str
    minimum_requirement: str
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None
    execution_authority: bool = False
    live_value_authorized: bool = False
    end_to_end_pq_security_established: bool = False
    claim_boundary: str = (
        "Migration-envelope policy result only; this does not establish production "
        "transaction authorization, movement of value, protocol conformance, Federal "
        "compliance, third-party validation, or end-to-end post-quantum security."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


@dataclass(frozen=True)
class SystemReadinessDecision:
    verdict: str
    weakest_level: str
    weakest_rank: int
    blocking_layers: tuple[str, ...]
    layer_levels: dict[str, str]
    migration_target_reached: bool
    execution_authority: bool = False
    live_value_authorized: bool = False
    whole_chain_pq_security_established: bool = False
    claim_boundary: str = (
        "Cross-layer migration-readiness classification only.  PQ_MIGRATION_READY "
        "means every tracked critical layer reached the modeled PQ-capable floor; it "
        "does not establish production deployment or end-to-end quantum safety."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blocking_layers"] = list(self.blocking_layers)
        return data


def _role_for_layer(layer: AuthorityLayer) -> CryptoRole:
    if layer is AuthorityLayer.CONSENSUS_VALIDATOR:
        return CryptoRole.CONSENSUS_AUTH
    return CryptoRole.DIGITAL_SIGNATURE


def _algorithm_slot_blockers(
    envelope: AuthorityEnvelope,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    role = _role_for_layer(envelope.authority_layer)

    if envelope.classical_signature_present:
        if not envelope.classical_algorithm_id:
            blockers.append("Classical signature is present but classical algorithm id is missing.")
        else:
            classical = REGISTRY.get(envelope.classical_algorithm_id)
            if classical is None:
                blockers.append("Classical algorithm is not present in the controlled registry.")
            elif classical.pq_resistant:
                blockers.append("Algorithm confusion: PQ algorithm was placed in the classical slot.")
            elif role not in classical.roles:
                blockers.append(f"Classical algorithm is not registered for role {role.value}.")
    elif envelope.classical_algorithm_id:
        warnings.append("Classical algorithm id is declared but no classical signature is present.")

    if envelope.pq_signature_present:
        if not envelope.pq_algorithm_id:
            blockers.append("PQ signature is present but PQ algorithm id is missing.")
        else:
            pq = REGISTRY.get(envelope.pq_algorithm_id)
            if pq is None:
                blockers.append("PQ algorithm is not present in the controlled registry.")
            elif not pq.pq_resistant:
                blockers.append("Algorithm confusion: classical algorithm was placed in the PQ slot.")
            elif role not in pq.roles:
                blockers.append(f"PQ algorithm is not registered for role {role.value}.")
            elif pq.standardization_state is not StandardizationState.FINAL_FIPS:
                blockers.append("PQ algorithm does not have finalized-FIPS status in the controlled registry.")
    elif envelope.pq_algorithm_id:
        warnings.append("PQ algorithm id is declared but no PQ signature is present.")

    return blockers, warnings


def assess_authority_envelope(
    envelope: AuthorityEnvelope,
    policy: AuthorityPolicy,
) -> AuthorityDecision:
    """Assess one authority envelope without performing any cryptographic action."""

    validate_registry()
    blockers: list[str] = []
    warnings: list[str] = []

    if envelope.execution_authority:
        blockers.append("Envelope cannot self-assert execution authority.")
    if envelope.live_value_authorized:
        blockers.append("Envelope cannot self-assert live-value authorization.")
    if not envelope.network_id or envelope.network_id != policy.network_id:
        blockers.append("Network id does not match the governed policy scope.")
    if not envelope.domain_separator or envelope.domain_separator != policy.domain_separator:
        blockers.append("Domain separator does not match the governed policy scope.")
    if len(envelope.payload_digest) != 64:
        blockers.append("Payload digest must be a 64-character hexadecimal SHA-256 digest.")
    else:
        try:
            int(envelope.payload_digest, 16)
        except ValueError:
            blockers.append("Payload digest is not valid hexadecimal SHA-256 text.")
    if not envelope.authority_id:
        blockers.append("Authority id is required.")
    if envelope.envelope_version < policy.minimum_envelope_version:
        blockers.append("Envelope version rollback rejected.")
    if envelope.key_epoch < policy.minimum_key_epoch:
        blockers.append("Key epoch rollback rejected.")
    if envelope.declared_requirement < policy.minimum_requirement:
        blockers.append("Migration-policy downgrade rejected.")

    slot_blockers, slot_warnings = _algorithm_slot_blockers(envelope)
    blockers.extend(slot_blockers)
    warnings.extend(slot_warnings)

    requirement = MigrationRequirement(
        max(int(policy.minimum_requirement), int(envelope.declared_requirement))
    )
    if requirement is MigrationRequirement.CLASSICAL_ALLOWED:
        if not (envelope.classical_signature_present or envelope.pq_signature_present):
            blockers.append("At least one governed signature slot must be present.")
    elif requirement is MigrationRequirement.HYBRID_REQUIRED:
        if not envelope.classical_signature_present or not envelope.pq_signature_present:
            blockers.append("Hybrid policy requires both classical and PQ signature slots.")
        if not envelope.classical_required_for_acceptance or not envelope.pq_required_for_acceptance:
            blockers.append("Hybrid policy requires both signature classes for acceptance.")
    elif requirement is MigrationRequirement.PQ_REQUIRED:
        if not envelope.pq_signature_present or not envelope.pq_required_for_acceptance:
            blockers.append("PQ-required policy requires a PQ signature for acceptance.")
        if envelope.classical_required_for_acceptance:
            blockers.append("PQ-required policy rejects continued classical acceptance dependency.")

    high_concentration = envelope.authority_layer in {
        AuthorityLayer.BRIDGE_CUSTODY,
        AuthorityLayer.GOVERNANCE_ADMIN,
    }
    if (policy.require_recovery_evidence or high_concentration) and not envelope.recovery_evidence_present:
        blockers.append("Recovery evidence is required for this authority surface.")

    accepted = not blockers
    if accepted and requirement is MigrationRequirement.PQ_REQUIRED:
        verdict = "PQ_AUTHORITY_MIGRATION_ACCEPTED"
    elif accepted and requirement is MigrationRequirement.HYBRID_REQUIRED:
        verdict = "HYBRID_AUTHORITY_MIGRATION_ACCEPTED"
    elif accepted:
        verdict = "CLASSICAL_COMPATIBILITY_ACCEPTED"
    elif "Migration-policy downgrade rejected." in blockers:
        verdict = "DOWNGRADE_REJECTED"
    elif any("Algorithm confusion" in item for item in blockers):
        verdict = "ALGORITHM_CONFUSION_REJECTED"
    elif any("rollback rejected" in item.lower() for item in blockers):
        verdict = "VERSION_OR_EPOCH_ROLLBACK_REJECTED"
    elif any("Recovery evidence" in item for item in blockers):
        verdict = "RECOVERY_EVIDENCE_REQUIRED"
    else:
        verdict = "AUTHORITY_MIGRATION_BLOCKED"

    if accepted and envelope.classical_signature_present:
        warnings.append(
            "Classical signature material remains present; this result does not establish "
            "end-to-end PQ-only security."
        )

    return AuthorityDecision(
        verdict=verdict,
        accepted=accepted,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        authority_layer=envelope.authority_layer.value,
        declared_requirement=envelope.declared_requirement.name,
        minimum_requirement=policy.minimum_requirement.name,
        classical_algorithm_id=envelope.classical_algorithm_id,
        pq_algorithm_id=envelope.pq_algorithm_id,
    )


def assess_system_readiness(
    layers: dict[CriticalLayer, ReadinessLevel],
) -> SystemReadinessDecision:
    """Return weakest-layer migration readiness; never assert whole-chain PQ security."""

    expected = set(CriticalLayer)
    present = set(layers)
    missing = expected - present
    if missing:
        names = tuple(sorted(layer.value for layer in missing))
        normalized = {layer.value: level.name for layer, level in layers.items()}
        return SystemReadinessDecision(
            verdict="BLOCKED_INCOMPLETE_LAYER_EVIDENCE",
            weakest_level="UNKNOWN",
            weakest_rank=-1,
            blocking_layers=names,
            layer_levels=normalized,
            migration_target_reached=False,
        )

    weakest_rank = min(int(level) for level in layers.values())
    weakest = ReadinessLevel(weakest_rank)
    blocking = tuple(sorted(layer.value for layer, level in layers.items() if int(level) == weakest_rank))
    normalized = {layer.value: level.name for layer, level in layers.items()}

    if weakest is ReadinessLevel.CLASSICAL:
        verdict = "BLOCKED_BY_CLASSICAL_LAYER"
        reached = False
    elif weakest is ReadinessLevel.HYBRID:
        verdict = "HYBRID_MIGRATION_READY"
        reached = False
    else:
        verdict = "PQ_MIGRATION_READY"
        reached = True

    return SystemReadinessDecision(
        verdict=verdict,
        weakest_level=weakest.name,
        weakest_rank=weakest_rank,
        blocking_layers=blocking,
        layer_levels=normalized,
        migration_target_reached=reached,
    )
