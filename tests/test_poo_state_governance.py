from dataclasses import replace

from security.poo.coc_guard import COCEvidence
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.state_engine import TechnicalOwnershipState
from security.poo.state_governance_guard import (
    evaluate_governed_recovery_transition,
    evaluate_governed_transfer_transition,
)
from security.poo.transfer_guard import TransferEvidence


def state(
    *,
    claimant: str,
    poo: str,
    coc: str,
    generation: int,
    previous_poo: str | None,
    previous_coc: str | None,
    event: str,
    key: str,
) -> TechnicalOwnershipState:
    return TechnicalOwnershipState(
        schema="WS-POO-TECHNICAL-STATE-V1",
        asset_id="asset:alpha",
        claimant_id=claimant,
        active_poo_digest=poo,
        active_coc_digest=coc,
        control_key_fingerprint=key,
        title_reference=f"title:{generation}",
        generation=generation,
        source_event_type=event,
        previous_poo_digest=previous_poo,
        previous_coc_digest=previous_coc,
    )


def healthy_history():
    return [
        state(
            claimant="claimant:one",
            poo="poo:001",
            coc="coc:001",
            generation=0,
            previous_poo=None,
            previous_coc=None,
            event="CLAIM",
            key="key:001",
        ),
        state(
            claimant="claimant:two",
            poo="poo:002",
            coc="coc:002",
            generation=1,
            previous_poo="poo:001",
            previous_coc="coc:001",
            event="TRANSFER",
            key="key:002",
        ),
    ]


def valid_transfer():
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="poo:002",
        current_owner_id="claimant:two",
        recipient_id="claimant:three",
        title_transition_reference="title:3",
        recipient_control_key_fingerprint="key:003",
        recipient_work_reference="work:003",
        recipient_concept_reference="concept:003",
        recipient_stake_reference="stake:003",
        initiated_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        current_owner_authorized=True,
        recipient_identity_bound=True,
        recipient_poc_concept_verified=True,
        recipient_coc_verified=True,
        recipient_pow_verified=True,
        recipient_pos_bond_verified=True,
        title_or_provenance_transition_bound=True,
        freshness_verified=True,
        no_active_dispute=True,
        transfer_not_revoked=True,
        human_approval_verified=True,
    )


def valid_recovery():
    return RecoveryEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="poo:002",
        claimant_id="claimant:two",
        recovery_reason="COMPROMISED_CONTROL",
        title_reference="title:1",
        new_control_key_fingerprint="key:002r",
        recovery_work_reference="work:recovery:002",
        recovery_concept_reference="concept:recovery:002",
        recovery_stake_reference="stake:recovery:002",
        recovery_request_reference="recovery:req:002",
        issued_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        claimant_continuity_verified=True,
        claimant_identity_reverified=True,
        title_or_provenance_reverified=True,
        compromise_or_loss_evidence_bound=True,
        recovery_pow_verified=True,
        recovery_poc_concept_verified=True,
        alternate_coc_verified=True,
        recovery_pos_bond_verified=True,
        multisource_or_quorum_verified=True,
        freshness_verified=True,
        recovery_not_revoked=True,
        active_dispute=False,
        dispute_resolution_verified=False,
        human_approval_verified=True,
    )


def coc_for(*, claimant: str, key: str, previous: str, suffix: str):
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{suffix}",
        custody_point_reference=f"point:{suffix}",
        challenge_reference=f"challenge:{suffix}",
        observed_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
        previous_coc_digest=previous,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def recipient_coc():
    return coc_for(claimant="claimant:three", key="key:003", previous="coc:002", suffix="003")


def recovery_coc():
    return coc_for(claimant="claimant:two", key="key:002r", previous="coc:002", suffix="002r")


def assert_non_authoritative(decision):
    assert decision.technical_state_committed is False
    assert decision.conflict_winner_selected is False
    assert decision.lineage_auto_resolved is False
    assert decision.legal_title_changed is False
    assert decision.live_value_moved is False
    assert decision.external_transfer_executed is False


def test_clean_full_state_lineage_allows_transfer_candidate_only():
    decision = evaluate_governed_transfer_transition(
        healthy_history(), valid_transfer(), recipient_coc()
    )
    assert decision.ready is True
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.poo_lineage_valid is True
    assert decision.coc_lineage_valid is True
    assert decision.generation_valid is True
    assert decision.status == "STATE_TRANSFER_READY_WITH_LINEAGE_GUARD"
    assert decision.active_tip_poo_digest == "poo:002"
    assert decision.transition is not None
    assert decision.transition.ready is True
    assert decision.candidate_state_digest == decision.transition.candidate_state_digest
    assert_non_authoritative(decision)


def test_forked_poo_history_blocks_perfect_transfer_evidence():
    history = healthy_history()
    history.append(
        state(
            claimant="claimant:fork",
            poo="poo:002b",
            coc="coc:002b",
            generation=1,
            previous_poo="poo:001",
            previous_coc="coc:001",
            event="TRANSFER",
            key="key:fork",
        )
    )
    decision = evaluate_governed_transfer_transition(history, valid_transfer(), recipient_coc())
    assert decision.base_evidence_ready is True
    assert decision.ready is False
    assert decision.state_lineage_valid is False
    assert decision.fork_detected is True
    assert decision.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert decision.transition is None
    assert decision.active_tip_poo_digest is None
    assert_non_authoritative(decision)


def test_broken_coc_predecessor_blocks_perfect_transfer_evidence():
    history = healthy_history()
    history[1] = replace(history[1], previous_coc_digest="coc:wrong")
    decision = evaluate_governed_transfer_transition(history, valid_transfer(), recipient_coc())
    assert decision.base_evidence_ready is True
    assert decision.ready is False
    assert decision.state_lineage_valid is False
    assert decision.poo_lineage_valid is True
    assert decision.coc_lineage_valid is False
    assert decision.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert any("COC:" in reason for reason in decision.reasons)
    assert_non_authoritative(decision)


def test_generation_gap_blocks_perfect_transfer_evidence():
    history = healthy_history()
    history[1] = replace(history[1], generation=2)
    decision = evaluate_governed_transfer_transition(history, valid_transfer(), recipient_coc())
    assert decision.base_evidence_ready is True
    assert decision.ready is False
    assert decision.generation_valid is False
    assert decision.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert any("generation" in reason for reason in decision.reasons)
    assert_non_authoritative(decision)


def test_stale_poo_predecessor_is_blocked_after_clean_lineage_check():
    transfer = replace(valid_transfer(), prior_poo_digest="poo:001")
    decision = evaluate_governed_transfer_transition(healthy_history(), transfer, recipient_coc())
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.ready is False
    assert decision.status == "STATE_TRANSFER_GOVERNANCE_BLOCKED"
    assert any("predecessor does not match active PoO" in reason for reason in decision.reasons)
    assert_non_authoritative(decision)


def test_wrong_current_claimant_is_blocked_after_clean_lineage_check():
    transfer = replace(valid_transfer(), current_owner_id="claimant:one")
    decision = evaluate_governed_transfer_transition(healthy_history(), transfer, recipient_coc())
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.ready is False
    assert any("current owner does not match active technical claimant" in r for r in decision.reasons)
    assert_non_authoritative(decision)


def test_recipient_coc_must_continue_active_coc_lineage():
    coc = replace(recipient_coc(), previous_coc_digest="coc:001")
    decision = evaluate_governed_transfer_transition(healthy_history(), valid_transfer(), coc)
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.ready is False
    assert any("COC predecessor does not match active COC lineage" in r for r in decision.reasons)
    assert_non_authoritative(decision)


def test_clean_full_state_lineage_allows_same_owner_recovery_candidate_only():
    decision = evaluate_governed_recovery_transition(
        healthy_history(), valid_recovery(), recovery_coc()
    )
    assert decision.ready is True
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.status == "STATE_RECOVERY_READY_WITH_LINEAGE_GUARD"
    assert decision.transition is not None
    assert decision.transition.ready is True
    assert_non_authoritative(decision)


def test_recovery_claimant_must_be_active_state_claimant():
    recovery = replace(valid_recovery(), claimant_id="claimant:one")
    decision = evaluate_governed_recovery_transition(
        healthy_history(), recovery, recovery_coc()
    )
    assert decision.base_evidence_ready is True
    assert decision.state_lineage_valid is True
    assert decision.ready is False
    assert any("recovery claimant must match active technical claimant" in r for r in decision.reasons)
    assert_non_authoritative(decision)


def test_invalid_lineage_blocks_recovery_even_when_base_evidence_is_ready():
    history = healthy_history()
    history[1] = replace(history[1], previous_coc_digest="coc:wrong")
    decision = evaluate_governed_recovery_transition(history, valid_recovery(), recovery_coc())
    assert decision.base_evidence_ready is True
    assert decision.ready is False
    assert decision.state_lineage_valid is False
    assert decision.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert_non_authoritative(decision)
