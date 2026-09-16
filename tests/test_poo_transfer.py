from dataclasses import replace

import pytest

from security.poo.ownership_guard import evaluate_ownership, ownership_digest
from security.poo.transfer_guard import (
    TransferEvidence,
    derive_recipient_ownership_evidence,
    evaluate_transfer,
    transfer_digest,
)


def valid_transfer():
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="prior-poo-digest-001",
        current_owner_id="claimant:one",
        recipient_id="claimant:two",
        title_transition_reference="title:transition:002",
        recipient_control_key_fingerprint="key:def456",
        recipient_work_reference="work:challenge:002",
        recipient_concept_reference="concept:demo:002",
        recipient_stake_reference="stake:bond:002",
        initiated_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
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


def test_transfer_ready_is_nonexecuting_governed_supersession_only():
    d = evaluate_transfer(valid_transfer())
    assert d.transfer_ready is True
    assert d.supersession_ready is True
    assert d.status == "READY_FOR_GOVERNED_SUPERSESSION"
    assert d.transfer_executed is False
    assert d.live_value_authorized is False
    assert d.legal_title_transferred is False


def test_every_transfer_predicate_is_fail_closed():
    base = valid_transfer()
    for field in (
        "prior_poo_valid",
        "asset_continuity_verified",
        "current_owner_authorized",
        "recipient_identity_bound",
        "recipient_poc_concept_verified",
        "recipient_coc_verified",
        "recipient_pow_verified",
        "recipient_pos_bond_verified",
        "title_or_provenance_transition_bound",
        "freshness_verified",
        "no_active_dispute",
        "transfer_not_revoked",
        "human_approval_verified",
    ):
        d = evaluate_transfer(replace(base, **{field: False}))
        assert d.transfer_ready is False, field
        assert d.supersession_ready is False, field
        assert d.missing_predicates, field


def test_proof_of_concept_and_coc_are_distinct_transfer_requirements():
    base = valid_transfer()
    missing_concept = evaluate_transfer(replace(base, recipient_poc_concept_verified=False))
    missing_coc = evaluate_transfer(replace(base, recipient_coc_verified=False))
    assert "recipient PoC concept not verified" in missing_concept.missing_predicates
    assert "recipient COC not verified" in missing_coc.missing_predicates
    assert missing_concept.transfer_ready is False
    assert missing_coc.transfer_ready is False


def test_active_dispute_blocks_supersession_even_when_other_proofs_pass():
    d = evaluate_transfer(replace(valid_transfer(), no_active_dispute=False))
    assert d.status == "TRANSFER_DISPUTED_BLOCKED"
    assert d.transfer_ready is False
    assert d.transfer_executed is False


def test_human_approval_is_required_and_does_not_execute_transfer():
    d = evaluate_transfer(replace(valid_transfer(), human_approval_verified=False))
    assert d.transfer_ready is False
    assert "human approval not verified" in d.missing_predicates
    assert d.transfer_executed is False


def test_ready_transfer_derives_new_poo_candidate_linked_to_prior_digest():
    transfer = valid_transfer()
    candidate = derive_recipient_ownership_evidence(transfer)
    decision = evaluate_ownership(candidate)
    assert candidate.claimant_id == transfer.recipient_id
    assert candidate.previous_poo_digest == transfer.prior_poo_digest
    assert candidate.poc_concept_verified is True
    assert candidate.coc_verified is True
    assert decision.poo_valid is True
    assert decision.legal_ownership_established is False


def test_unready_transfer_cannot_derive_recipient_poo_candidate():
    transfer = replace(valid_transfer(), recipient_poc_concept_verified=False)
    with pytest.raises(ValueError):
        derive_recipient_ownership_evidence(transfer)


def test_transfer_digest_is_deterministic_and_lineage_sensitive():
    t = valid_transfer()
    assert transfer_digest(t) == transfer_digest(t)
    assert transfer_digest(replace(t, prior_poo_digest="different-prior")) != transfer_digest(t)


def test_derived_recipient_poo_digest_changes_from_prior_lineage_reference():
    t1 = valid_transfer()
    t2 = replace(t1, prior_poo_digest="another-prior")
    c1 = derive_recipient_ownership_evidence(t1)
    c2 = derive_recipient_ownership_evidence(t2)
    assert ownership_digest(c1) != ownership_digest(c2)


def test_external_title_transition_does_not_establish_legal_title():
    t = replace(valid_transfer(), external_title_transition_verified=True)
    candidate = derive_recipient_ownership_evidence(t)
    decision = evaluate_ownership(candidate)
    assert decision.status == "TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE"
    assert decision.legal_ownership_established is False
