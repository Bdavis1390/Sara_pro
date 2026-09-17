"""Defensive readiness gate for an institution-grade post-quantum pilot.

The pilot is intentionally staged: dry-run -> testnet -> bounded canary.
This module does not create keys, sign transactions, move assets, access wallets,
or authorize live-value deployment. Mainnet value remains human-gated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HighValuePilotEvidence:
    name: str
    source: str
    stable_authority_identifier: bool = False
    replaceable_authenticator: bool = False
    signature_agnostic_quorum: bool = False
    hardware_backed_ml_dsa_available: bool = False
    hardware_backed_slh_dsa_available: bool = False
    provider_diversity_available: bool = False
    chain_adapter_testnet_validated: bool = False
    precommitted_recovery: bool = False
    recovery_drill_passed: bool = False
    fail_closed_classical_bypass: bool = False
    immutable_evidence_logging: bool = False
    human_approval_required: bool = True
    independent_review_complete: bool = False
    bounded_value_policy_defined: bool = False
    live_value_canary_authorized: bool = False
    chain_native_pq_consensus: bool = False


@dataclass(frozen=True)
class HighValuePilotAssessment:
    pilot_state: str
    signer_state: str
    authorization_state: str
    recovery_state: str
    deployment_action: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_high_value_pilot(evidence: HighValuePilotEvidence) -> HighValuePilotAssessment:
    """Return the highest defensible pilot stage without authorizing live value."""

    blockers: list[str] = []

    dual_family = evidence.hardware_backed_ml_dsa_available and evidence.hardware_backed_slh_dsa_available
    if dual_family and evidence.provider_diversity_available:
        signer_state = "DUAL_FAMILY_DUAL_PROVIDER_PQ_SIGNING_AVAILABLE"
    elif dual_family:
        signer_state = "DUAL_FAMILY_PQ_SIGNING_AVAILABLE"
        blockers.append("Independent provider diversity is not established.")
    else:
        signer_state = "PQ_SIGNER_SET_INCOMPLETE"
        blockers.append("Both hardware-backed ML-DSA and SLH-DSA signing capability are required for this pilot profile.")

    auth_ready = all(
        (
            evidence.stable_authority_identifier,
            evidence.replaceable_authenticator,
            evidence.signature_agnostic_quorum,
            evidence.fail_closed_classical_bypass,
        )
    )
    authorization_state = "VIRTUALIZED_FAIL_CLOSED_AUTHORIZATION" if auth_ready else "AUTHORIZATION_GATES_INCOMPLETE"
    if not auth_ready:
        blockers.append("Stable authority identity, replaceable authenticators, quorum separation, and fail-closed classical bypass are not all validated.")

    if evidence.precommitted_recovery and evidence.recovery_drill_passed:
        recovery_state = "RECOVERY_PREPOSITIONED_AND_DRILLED"
    elif evidence.precommitted_recovery:
        recovery_state = "RECOVERY_PREPOSITIONED_NOT_DRILLED"
        blockers.append("Recovery exists but has not passed a controlled recovery drill.")
    else:
        recovery_state = "RECOVERY_NOT_PREPOSITIONED"
        blockers.append("A post-quantum recovery path must exist before pilot activation.")

    dry_run_ready = dual_family and evidence.human_approval_required and evidence.immutable_evidence_logging
    testnet_ready = dry_run_ready and auth_ready and evidence.chain_adapter_testnet_validated and evidence.precommitted_recovery
    canary_controls = (
        testnet_ready
        and evidence.recovery_drill_passed
        and evidence.independent_review_complete
        and evidence.bounded_value_policy_defined
    )

    if canary_controls and evidence.live_value_canary_authorized:
        pilot_state = "HVP_BOUNDED_CANARY_READY"
        action = "EXECUTE_ONLY_WITH_EXPLICIT_HUMAN_AUTHORIZATION_AND_CONFIGURED_VALUE_CAP"
    elif canary_controls:
        pilot_state = "HVP_BOUNDED_CANARY_READY_PENDING_HUMAN_AUTHORIZATION"
        action = "HOLD_LIVE_VALUE; COMPLETE_APPROVAL_AND_CHANGE_CONTROL"
    elif testnet_ready:
        pilot_state = "HVP_TESTNET_READY"
        action = "RUN_TESTNET_FAILURE_RECOVERY_AND_INTEROPERABILITY_CAMPAIGN"
    elif dry_run_ready:
        pilot_state = "HVP_DRY_RUN_READY"
        action = "RUN_NOTIONAL_HIGH_VALUE_DRY_RUN_WITH_ZERO_LIVE_ASSET_EXPOSURE"
    else:
        pilot_state = "HVP_DESIGN_OR_INTEGRATION"
        action = "COMPLETE_SIGNER_AUTHORIZATION_RECOVERY_AND_EVIDENCE_GATES"

    if not evidence.independent_review_complete:
        blockers.append("Independent review of the complete pilot path is not complete.")
    if not evidence.chain_native_pq_consensus:
        blockers.append("The pilot protects an authorization domain; base-layer consensus remains a separate migration dependency.")
    if not evidence.live_value_canary_authorized:
        blockers.append("No live-value mainnet canary is authorized by this evidence record.")

    return HighValuePilotAssessment(
        pilot_state=pilot_state,
        signer_state=signer_state,
        authorization_state=authorization_state,
        recovery_state=recovery_state,
        deployment_action=action,
        blockers=tuple(blockers),
    )
