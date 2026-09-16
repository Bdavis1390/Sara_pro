"""Fail-closed production transition assessment for QCRYPTO.

This module evaluates whether defensive evidence is mature enough to enter an
external human-operated production change process. It never signs or broadcasts
transactions, mutates validator state, handles private keys, authorizes live
value, or establishes end-to-end post-quantum security.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionTransitionEvidence:
    bitcoin_environment: str = "SIGNET_OR_TESTNET"
    ethereum_environment: str = "DEVNET_OR_TESTNET"

    bitcoin_adapter_tested: bool = False
    bitcoin_native_pq_spend_path_deployed: bool = False
    bitcoin_consensus_change_deployed: bool = False

    ethereum_validator_change_tested: bool = False
    ethereum_pq_validator_signatures_deployed: bool = False
    ethereum_pq_execution_auth_deployed: bool = False
    ethereum_pq_data_commitments_deployed: bool = False

    external_signer_or_hsm_configured: bool = False
    private_key_export_required: bool = False
    secret_material_retained_by_qcrypto: bool = False

    independent_review_complete: bool = False
    recovery_drill_passed: bool = False
    rollback_drill_passed: bool = False
    monitoring_ready: bool = False
    production_change_control_approved: bool = False
    explicit_human_live_value_authorization: bool = False

    live_bitcoin_transaction_requested: bool = False
    ethereum_validator_mutation_requested: bool = False
    production_deployment_requested: bool = False

    end_to_end_bitcoin_pq_security_independently_established: bool = False
    end_to_end_ethereum_pq_security_independently_established: bool = False


@dataclass(frozen=True)
class ProductionTransitionAssessment:
    state: str
    bitcoin_state: str
    ethereum_state: str
    key_custody_state: str
    pq_claim_state: str
    deployment_action: str
    ready_for_external_human_change_control: bool
    execution_authority: bool
    live_value_authorized: bool
    private_key_operations_permitted: bool
    production_deployment_permitted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_production_transition(
    evidence: ProductionTransitionEvidence,
) -> ProductionTransitionAssessment:
    """Assess production-transition evidence while preserving a hard no-execution boundary."""

    blockers: list[str] = []
    warnings: list[str] = []

    if evidence.private_key_export_required:
        blockers.append("Private-key export is incompatible with the QCRYPTO production boundary.")
    if evidence.secret_material_retained_by_qcrypto:
        blockers.append("QCRYPTO must not retain private or secret signing material.")

    key_custody_ready = (
        evidence.external_signer_or_hsm_configured
        and not evidence.private_key_export_required
        and not evidence.secret_material_retained_by_qcrypto
    )
    key_custody_state = (
        "EXTERNAL_SIGNER_BOUNDARY_READY"
        if key_custody_ready
        else "KEY_CUSTODY_BOUNDARY_INCOMPLETE"
    )

    bitcoin_test_ready = evidence.bitcoin_adapter_tested and key_custody_ready
    bitcoin_protocol_pq = (
        evidence.bitcoin_native_pq_spend_path_deployed
        and evidence.bitcoin_consensus_change_deployed
        and evidence.end_to_end_bitcoin_pq_security_independently_established
    )
    if bitcoin_protocol_pq:
        bitcoin_state = "BITCOIN_PQ_SECURITY_EXTERNALLY_ATTESTED"
    elif bitcoin_test_ready:
        bitcoin_state = "BITCOIN_NONPRODUCTION_INTEGRATION_READY"
        warnings.append(
            "Bitcoin integration readiness is not evidence that a native PQ spend path or consensus migration is deployed."
        )
    else:
        bitcoin_state = "BITCOIN_INTEGRATION_INCOMPLETE"

    ethereum_test_ready = evidence.ethereum_validator_change_tested and key_custody_ready
    ethereum_protocol_pq = all(
        (
            evidence.ethereum_pq_validator_signatures_deployed,
            evidence.ethereum_pq_execution_auth_deployed,
            evidence.ethereum_pq_data_commitments_deployed,
            evidence.end_to_end_ethereum_pq_security_independently_established,
        )
    )
    if ethereum_protocol_pq:
        ethereum_state = "ETHEREUM_PQ_SECURITY_EXTERNALLY_ATTESTED"
    elif ethereum_test_ready:
        ethereum_state = "ETHEREUM_NONPRODUCTION_VALIDATOR_CHANGE_READY"
        warnings.append(
            "Validator-change readiness is not evidence that Ethereum consensus, execution, and data layers are fully PQ-secure."
        )
    else:
        ethereum_state = "ETHEREUM_VALIDATOR_CHANGE_INCOMPLETE"

    if bitcoin_protocol_pq and ethereum_protocol_pq:
        pq_claim_state = "EXTERNAL_END_TO_END_PQ_ATTESTATIONS_PRESENT"
    else:
        pq_claim_state = "END_TO_END_PQ_SECURITY_NOT_ESTABLISHED"

    governance_ready = all(
        (
            evidence.independent_review_complete,
            evidence.recovery_drill_passed,
            evidence.rollback_drill_passed,
            evidence.monitoring_ready,
            evidence.production_change_control_approved,
        )
    )

    if not evidence.independent_review_complete:
        blockers.append("Independent review is incomplete.")
    if not evidence.recovery_drill_passed:
        blockers.append("Recovery drill has not passed.")
    if not evidence.rollback_drill_passed:
        blockers.append("Rollback drill has not passed.")
    if not evidence.monitoring_ready:
        blockers.append("Production monitoring is not ready.")
    if not evidence.production_change_control_approved:
        blockers.append("Production change control is not approved.")

    integration_ready = bitcoin_test_ready and ethereum_test_ready and governance_ready

    if evidence.live_bitcoin_transaction_requested:
        blockers.append(
            "Live Bitcoin transaction execution is outside QCRYPTO authority and must remain an external human-operated action."
        )
    if evidence.ethereum_validator_mutation_requested:
        blockers.append(
            "Ethereum validator mutation is outside QCRYPTO authority and must remain an external human-operated action."
        )
    if evidence.production_deployment_requested:
        blockers.append(
            "Production deployment execution is outside QCRYPTO authority; this assessment can only gate an external change process."
        )
    if evidence.explicit_human_live_value_authorization:
        warnings.append(
            "A human live-value authorization record does not grant execution authority to QCRYPTO."
        )

    if integration_ready:
        state = "READY_FOR_EXTERNAL_HUMAN_CHANGE_CONTROL"
        deployment_action = (
            "HAND_OFF_SIGNET_TESTNET_EVIDENCE_TO_EXTERNAL_HUMAN_OPERATED_PRODUCTION_CHANGE_PROCESS"
        )
    else:
        state = "PRODUCTION_TRANSITION_BLOCKED"
        deployment_action = "COMPLETE_NONPRODUCTION_EVIDENCE_AND_GOVERNANCE_GATES"

    return ProductionTransitionAssessment(
        state=state,
        bitcoin_state=bitcoin_state,
        ethereum_state=ethereum_state,
        key_custody_state=key_custody_state,
        pq_claim_state=pq_claim_state,
        deployment_action=deployment_action,
        ready_for_external_human_change_control=integration_ready,
        execution_authority=False,
        live_value_authorized=False,
        private_key_operations_permitted=False,
        production_deployment_permitted=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
