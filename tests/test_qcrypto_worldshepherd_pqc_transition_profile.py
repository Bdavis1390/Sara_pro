from datetime import date

from security.qcrypto.pqc_algorithm_policy import Environment
from security.qcrypto.worldshepherd_pqc_transition_profile import (
    COMPONENTS,
    InventoryState,
    TransitionPhase,
    assess_all,
    assess_component,
    assert_no_self_promotion,
)


def test_profile_covers_core_worldshepherd_crypto_surfaces():
    assert {
        "ECHO_CHECKPOINT_SIGNATURE",
        "SARA_ECHO_TRANSPORT_KEY_ESTABLISHMENT",
        "PRIME_ATTESTATION_SIGNATURE",
        "NODE_IDENTITY_SIGNATURE",
        "POS_VALIDATOR_AUTH_REFERENCE",
    }.issubset(COMPONENTS)
    assert_no_self_promotion()


def test_echo_checkpoint_inventory_is_code_verified_ed25519():
    component = COMPONENTS["ECHO_CHECKPOINT_SIGNATURE"]
    assert component.current_algorithm == "ED25519"
    assert component.inventory_state is InventoryState.CODE_VERIFIED
    assert component.target_algorithm == "ML-DSA"

    result = assess_component(component, environment=Environment.LAB)
    assert result.target_standardization_state == "FINAL_FIPS"
    assert result.target_standard_reference == "FIPS 204"
    assert result.transition_phase == TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED.value
    assert result.target_policy_verdict == "BLOCKED_DEPLOYMENT_EVIDENCE"
    assert result.production_pq_ready is False
    assert result.end_to_end_pq_security_established is False
    assert any("runtime/deployment evidence is insufficient" in item for item in result.blockers)


def test_echo_checkpoint_cannot_be_called_production_ready_even_when_target_is_final_fips():
    result = assess_component(
        COMPONENTS["ECHO_CHECKPOINT_SIGNATURE"],
        environment=Environment.PRODUCTION,
    )
    assert result.target_standardization_state == "FINAL_FIPS"
    assert result.transition_phase == TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED.value
    assert result.production_pq_ready is False
    assert result.execution_authority is False


def test_unresolved_transport_inventory_blocks_ml_kem_migration_phase():
    component = COMPONENTS["SARA_ECHO_TRANSPORT_KEY_ESTABLISHMENT"]
    assert component.current_algorithm == "UNRESOLVED_INVENTORY"
    assert component.inventory_state is InventoryState.UNRESOLVED
    assert component.target_algorithm == "ML-KEM"

    result = assess_component(component, environment=Environment.LAB)
    assert result.target_standardization_state == "FINAL_FIPS"
    assert result.target_standard_reference == "FIPS 203"
    assert result.transition_phase == TransitionPhase.INVENTORY_REQUIRED.value
    assert any("inventory evidence is required" in item for item in result.blockers)


def test_prime_and_node_identity_are_not_guessed():
    for component_id in ("PRIME_ATTESTATION_SIGNATURE", "NODE_IDENTITY_SIGNATURE"):
        component = COMPONENTS[component_id]
        assert component.current_algorithm == "UNRESOLVED_INVENTORY"
        assert component.inventory_state is InventoryState.UNRESOLVED
        result = assess_component(component, environment=Environment.LAB)
        assert result.transition_phase == TransitionPhase.INVENTORY_REQUIRED.value
        assert result.execution_authority is False
        assert result.live_value_authorized is False


def test_validator_reference_can_be_lab_or_testnet_candidate_but_never_self_promotes():
    component = COMPONENTS["POS_VALIDATOR_AUTH_REFERENCE"]

    lab = assess_component(component, environment=Environment.LAB)
    assert lab.transition_phase == TransitionPhase.CONTROLLED_LAB_CANDIDATE.value
    assert lab.production_pq_ready is False

    testnet = assess_component(component, environment=Environment.TESTNET)
    assert testnet.transition_phase == TransitionPhase.PUBLIC_TESTNET_CANDIDATE.value
    assert testnet.production_pq_ready is False
    assert testnet.end_to_end_pq_security_established is False

    production = assess_component(component, environment=Environment.PRODUCTION)
    assert production.transition_phase == TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED.value
    assert production.target_policy_verdict == "BLOCKED_DEPLOYMENT_EVIDENCE"


def test_stale_policy_evidence_blocks_transition_even_for_final_standard():
    result = assess_component(
        COMPONENTS["ECHO_CHECKPOINT_SIGNATURE"],
        environment=Environment.LAB,
        evidence_checked_on=date(2027, 2, 1),
    )
    assert result.transition_phase == TransitionPhase.TARGET_SELECTED_IMPLEMENTATION_BLOCKED.value
    assert any("stale" in item.lower() for item in result.blockers)


def test_all_component_environments_preserve_human_and_rollback_gates():
    for environment in Environment:
        for result in assess_all(environment=environment).values():
            assert result.human_approval_required is True
            assert result.rollback_evidence_required is True
            assert result.execution_authority is False
            assert result.live_value_authorized is False
            assert result.production_pq_ready is False
            assert result.end_to_end_pq_security_established is False


def test_claim_boundary_never_self_certifies():
    result = assess_component(
        COMPONENTS["ECHO_CHECKPOINT_SIGNATURE"],
        environment=Environment.LAB,
    )
    lower = result.claim_boundary.lower()
    assert "no key rotation" in lower
    assert "fips module validation" in lower
    assert "federal compliance" in lower
    assert "end-to-end post-quantum security" in lower
