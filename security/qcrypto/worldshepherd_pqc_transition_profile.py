"""Component-level post-quantum transition envelope for Worldshepherd.

This module converts algorithm-policy and runtime-inventory evidence into phased
migration plans. It is intentionally non-executing: it cannot rotate keys,
change transport configuration, sign artifacts, deploy code, or authorize live
value.

Known facts are kept separate from target selection. Unknown current primitives
remain INVENTORY_REQUIRED rather than being guessed from architecture names.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum

from security.qcrypto.pqc_algorithm_policy import (
    AlgorithmRequest,
    CryptoRole,
    Environment,
    SupportTier,
    TransitionMode,
    assess as assess_algorithm,
)


AS_OF = date(2026, 9, 15)
UNKNOWN = "UNRESOLVED_INVENTORY"


class InventoryState(StrEnum):
    CODE_VERIFIED = "CODE_VERIFIED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    UNRESOLVED = "UNRESOLVED"


class TransitionPhase(StrEnum):
    INVENTORY_REQUIRED = "INVENTORY_REQUIRED"
    TARGET_SELECTED_IMPLEMENTATION_BLOCKED = "TARGET_SELECTED_IMPLEMENTATION_BLOCKED"
    CONTROLLED_LAB_CANDIDATE = "CONTROLLED_LAB_CANDIDATE"
    PUBLIC_TESTNET_CANDIDATE = "PUBLIC_TESTNET_CANDIDATE"
    BOUNDED_PRODUCTION_INTEGRATION_REVIEW = "BOUNDED_PRODUCTION_INTEGRATION_REVIEW"


@dataclass(frozen=True)
class ComponentInventory:
    component_id: str
    crypto_role: CryptoRole
    current_algorithm: str
    inventory_state: InventoryState
    target_algorithm: str
    runtime_support_tier: SupportTier
    current_evidence: tuple[str, ...]
    required_evidence: tuple[str, ...]
    transition_mode: TransitionMode = TransitionMode.HYBRID_TRANSITION


@dataclass(frozen=True)
class ComponentTransitionPlan:
    component_id: str
    crypto_role: str
    current_algorithm: str
    inventory_state: str
    target_algorithm: str
    target_standardization_state: str
    target_standard_reference: str
    target_policy_verdict: str
    runtime_support_tier: str
    transition_phase: str
    current_evidence: tuple[str, ...]
    required_evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    human_approval_required: bool = True
    rollback_evidence_required: bool = True
    execution_authority: bool = False
    live_value_authorized: bool = False
    production_pq_ready: bool = False
    end_to_end_pq_security_established: bool = False
    claim_boundary: str = (
        "Component migration planning only; no key rotation, signing, transport mutation, "
        "production deployment, FIPS module validation, Federal compliance, live-value "
        "authorization, or end-to-end post-quantum security is established."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("current_evidence", "required_evidence", "blockers", "warnings"):
            data[key] = list(data[key])
        return data


COMPONENTS: dict[str, ComponentInventory] = {
    "ECHO_CHECKPOINT_SIGNATURE": ComponentInventory(
        component_id="ECHO_CHECKPOINT_SIGNATURE",
        crypto_role=CryptoRole.DIGITAL_SIGNATURE,
        current_algorithm="ED25519",
        inventory_state=InventoryState.CODE_VERIFIED,
        target_algorithm="ML-DSA",
        runtime_support_tier=SupportTier.NONE,
        current_evidence=(
            "ECHO checkpoint runtime and verifier encode Ed25519 as the current executable algorithm.",
            "Checkpoint agility guard recognizes ML-DSA/SLH-DSA but fails closed because no verified PQ signer adapter is installed.",
        ),
        required_evidence=(
            "Verified ML-DSA signer adapter using a standards-conformant cryptographic provider.",
            "ML-DSA verify-path support for checkpoint bundles.",
            "Key serialization/custody format evidence and rollback procedure.",
            "Controlled lab sign/verify interoperability evidence.",
            "Checkpoint-chain mixed-era compatibility evidence before any production review.",
        ),
    ),
    "SARA_ECHO_TRANSPORT_KEY_ESTABLISHMENT": ComponentInventory(
        component_id="SARA_ECHO_TRANSPORT_KEY_ESTABLISHMENT",
        crypto_role=CryptoRole.KEY_ESTABLISHMENT,
        current_algorithm=UNKNOWN,
        inventory_state=InventoryState.UNRESOLVED,
        target_algorithm="ML-KEM",
        runtime_support_tier=SupportTier.NONE,
        current_evidence=(
            "No component-specific key-establishment primitive is asserted by this profile without direct runtime/configuration evidence.",
        ),
        required_evidence=(
            "Inventory exact current TLS/KEX primitive and provider/version from deployed configuration.",
            "Protocol/library evidence for ML-KEM or approved hybrid key establishment.",
            "Lab handshake/interoperability evidence with downgrade detection.",
            "Rollback evidence and human-approved deployment plan.",
        ),
    ),
    "PRIME_ATTESTATION_SIGNATURE": ComponentInventory(
        component_id="PRIME_ATTESTATION_SIGNATURE",
        crypto_role=CryptoRole.DIGITAL_SIGNATURE,
        current_algorithm=UNKNOWN,
        inventory_state=InventoryState.UNRESOLVED,
        target_algorithm="ML-DSA",
        runtime_support_tier=SupportTier.NONE,
        current_evidence=(
            "No PRIME attestation signing primitive is asserted by this profile until runtime/code evidence is bound.",
        ),
        required_evidence=(
            "Inventory exact PRIME attestation/signature primitive and key custody path.",
            "Define canonical signed payload and algorithm identifier/versioning rules.",
            "Controlled ML-DSA sign/verify interoperability evidence.",
            "Mixed classical/PQ verification and rollback evidence.",
        ),
    ),
    "NODE_IDENTITY_SIGNATURE": ComponentInventory(
        component_id="NODE_IDENTITY_SIGNATURE",
        crypto_role=CryptoRole.NODE_IDENTITY,
        current_algorithm=UNKNOWN,
        inventory_state=InventoryState.UNRESOLVED,
        target_algorithm="ML-DSA",
        runtime_support_tier=SupportTier.NONE,
        current_evidence=(
            "Node-identity algorithm is target/runtime dependent and is not guessed by this profile.",
        ),
        required_evidence=(
            "Inventory node-identity primitive by target environment.",
            "Define certificate/identity container compatibility for the selected PQ algorithm.",
            "Lab authentication and rotation evidence.",
            "Failure/recovery evidence under mixed-version operation.",
        ),
    ),
    "POS_VALIDATOR_AUTH_REFERENCE": ComponentInventory(
        component_id="POS_VALIDATOR_AUTH_REFERENCE",
        crypto_role=CryptoRole.CONSENSUS_AUTH,
        current_algorithm=UNKNOWN,
        inventory_state=InventoryState.EVIDENCE_VERIFIED,
        target_algorithm="ML-DSA",
        runtime_support_tier=SupportTier.PUBLIC_TESTNET,
        current_evidence=(
            "Worldshepherd PoS readiness model contains a public-testnet validator-auth benchmark profile; it is not a production-mainnet claim.",
        ),
        required_evidence=(
            "Per-target consensus-rule acceptance evidence.",
            "Production client/protocol support for the exact validator-auth path.",
            "Validator key lifecycle, slashing/recovery, hardware custody, and HSM evidence.",
            "Independent production-network validation before any production-ready claim.",
        ),
    ),
}


def assess_component(
    component: ComponentInventory,
    *,
    environment: Environment = Environment.LAB,
    evidence_checked_on: date = AS_OF,
) -> ComponentTransitionPlan:
    blockers: list[str] = []
    warnings: list[str] = []

    request = AlgorithmRequest(
        algorithm_id=component.target_algorithm,
        role=component.crypto_role,
        environment=environment,
        support_tier=component.runtime_support_tier,
        transition_mode=component.transition_mode,
        evidence_checked_on=evidence_checked_on,
    )
    policy = assess_algorithm(request)
    warnings.extend(policy.warnings)

    if component.inventory_state is InventoryState.UNRESOLVED:
        blockers.append("Current cryptographic primitive is unresolved; inventory evidence is required before migration execution planning.")
        phase = TransitionPhase.INVENTORY_REQUIRED
    elif not policy.standards_eligible:
        blockers.append(f"Target algorithm is not standards-eligible for this role: {policy.verdict}.")
        phase = TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED
    elif not policy.deployment_eligible:
        blockers.append(f"Target runtime/deployment evidence is insufficient: {policy.verdict}.")
        phase = TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED
    elif environment is Environment.LAB:
        phase = TransitionPhase.CONTROLLED_LAB_CANDIDATE
    elif environment is Environment.TESTNET:
        phase = TransitionPhase.PUBLIC_TESTNET_CANDIDATE
    else:
        phase = TransitionPhase.BOUNDED_PRODUCTION_INTEGRATION_REVIEW

    if component.transition_mode is TransitionMode.HYBRID_TRANSITION:
        warnings.append(
            "Hybrid transition preserves a classical dependency until separately evidenced retirement criteria are satisfied."
        )

    return ComponentTransitionPlan(
        component_id=component.component_id,
        crypto_role=component.crypto_role.value,
        current_algorithm=component.current_algorithm,
        inventory_state=component.inventory_state.value,
        target_algorithm=component.target_algorithm,
        target_standardization_state=policy.standardization_state,
        target_standard_reference=policy.standard_reference,
        target_policy_verdict=policy.verdict,
        runtime_support_tier=component.runtime_support_tier.name,
        transition_phase=phase.value,
        current_evidence=component.current_evidence,
        required_evidence=component.required_evidence,
        blockers=tuple(blockers) + policy.blockers,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def assess_all(
    *,
    environment: Environment = Environment.LAB,
    evidence_checked_on: date = AS_OF,
) -> dict[str, ComponentTransitionPlan]:
    return {
        component_id: assess_component(
            component,
            environment=environment,
            evidence_checked_on=evidence_checked_on,
        )
        for component_id, component in COMPONENTS.items()
    }


def assert_no_self_promotion() -> None:
    for environment in Environment:
        for result in assess_all(environment=environment).values():
            if result.production_pq_ready:
                raise AssertionError(f"{result.component_id} self-promoted to production PQ ready")
            if result.end_to_end_pq_security_established:
                raise AssertionError(f"{result.component_id} self-promoted to end-to-end PQ security")
            if result.execution_authority or result.live_value_authorized:
                raise AssertionError(f"{result.component_id} self-promoted execution authority")
