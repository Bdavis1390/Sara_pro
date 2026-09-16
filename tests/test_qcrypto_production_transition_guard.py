from security.qcrypto.production_transition_guard import (
    ProductionTransitionEvidence,
    assess_production_transition,
)


def mature_nonproduction_evidence(**overrides):
    data = dict(
        bitcoin_environment="SIGNET",
        ethereum_environment="HOLESKY_OR_EQUIVALENT_TESTNET",
        bitcoin_adapter_tested=True,
        ethereum_validator_change_tested=True,
        external_signer_or_hsm_configured=True,
        independent_review_complete=True,
        recovery_drill_passed=True,
        rollback_drill_passed=True,
        monitoring_ready=True,
        production_change_control_approved=True,
    )
    data.update(overrides)
    return ProductionTransitionEvidence(**data)


def test_mature_nonproduction_evidence_can_only_reach_external_change_control():
    result = assess_production_transition(mature_nonproduction_evidence())

    assert result.state == "READY_FOR_EXTERNAL_HUMAN_CHANGE_CONTROL"
    assert result.ready_for_external_human_change_control is True
    assert result.bitcoin_state == "BITCOIN_NONPRODUCTION_INTEGRATION_READY"
    assert result.ethereum_state == "ETHEREUM_NONPRODUCTION_VALIDATOR_CHANGE_READY"
    assert result.pq_claim_state == "END_TO_END_PQ_SECURITY_NOT_ESTABLISHED"

    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.private_key_operations_permitted is False
    assert result.production_deployment_permitted is False


def test_private_key_export_requirement_fails_closed():
    result = assess_production_transition(
        mature_nonproduction_evidence(private_key_export_required=True)
    )

    assert result.state == "PRODUCTION_TRANSITION_BLOCKED"
    assert result.key_custody_state == "KEY_CUSTODY_BOUNDARY_INCOMPLETE"
    assert any("Private-key export" in blocker for blocker in result.blockers)
    assert result.private_key_operations_permitted is False


def test_qcrypto_secret_retention_fails_closed():
    result = assess_production_transition(
        mature_nonproduction_evidence(secret_material_retained_by_qcrypto=True)
    )

    assert result.state == "PRODUCTION_TRANSITION_BLOCKED"
    assert any("must not retain" in blocker for blocker in result.blockers)


def test_live_bitcoin_request_never_grants_execution_authority():
    result = assess_production_transition(
        mature_nonproduction_evidence(
            live_bitcoin_transaction_requested=True,
            explicit_human_live_value_authorization=True,
        )
    )

    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.production_deployment_permitted is False
    assert any("Live Bitcoin transaction execution" in blocker for blocker in result.blockers)
    assert any("does not grant execution authority" in warning for warning in result.warnings)


def test_validator_mutation_request_never_grants_execution_authority():
    result = assess_production_transition(
        mature_nonproduction_evidence(ethereum_validator_mutation_requested=True)
    )

    assert result.execution_authority is False
    assert result.private_key_operations_permitted is False
    assert any("validator mutation" in blocker for blocker in result.blockers)


def test_production_deployment_request_is_handoff_only():
    result = assess_production_transition(
        mature_nonproduction_evidence(production_deployment_requested=True)
    )

    assert result.ready_for_external_human_change_control is True
    assert result.production_deployment_permitted is False
    assert any("outside QCRYPTO authority" in blocker for blocker in result.blockers)


def test_partial_pq_evidence_cannot_claim_end_to_end_security():
    result = assess_production_transition(
        mature_nonproduction_evidence(
            bitcoin_native_pq_spend_path_deployed=True,
            bitcoin_consensus_change_deployed=False,
            end_to_end_bitcoin_pq_security_independently_established=False,
            ethereum_pq_validator_signatures_deployed=True,
            ethereum_pq_execution_auth_deployed=True,
            ethereum_pq_data_commitments_deployed=False,
            end_to_end_ethereum_pq_security_independently_established=False,
        )
    )

    assert result.pq_claim_state == "END_TO_END_PQ_SECURITY_NOT_ESTABLISHED"
    assert result.bitcoin_state == "BITCOIN_NONPRODUCTION_INTEGRATION_READY"
    assert result.ethereum_state == "ETHEREUM_NONPRODUCTION_VALIDATOR_CHANGE_READY"


def test_external_pq_attestations_still_do_not_create_execution_authority():
    result = assess_production_transition(
        mature_nonproduction_evidence(
            bitcoin_native_pq_spend_path_deployed=True,
            bitcoin_consensus_change_deployed=True,
            end_to_end_bitcoin_pq_security_independently_established=True,
            ethereum_pq_validator_signatures_deployed=True,
            ethereum_pq_execution_auth_deployed=True,
            ethereum_pq_data_commitments_deployed=True,
            end_to_end_ethereum_pq_security_independently_established=True,
            explicit_human_live_value_authorization=True,
        )
    )

    assert result.pq_claim_state == "EXTERNAL_END_TO_END_PQ_ATTESTATIONS_PRESENT"
    assert result.bitcoin_state == "BITCOIN_PQ_SECURITY_EXTERNALLY_ATTESTED"
    assert result.ethereum_state == "ETHEREUM_PQ_SECURITY_EXTERNALLY_ATTESTED"
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.private_key_operations_permitted is False
    assert result.production_deployment_permitted is False
