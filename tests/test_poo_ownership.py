from dataclasses import replace

from security.poo.ownership_guard import (
    OwnershipEvidence,
    evaluate_ownership,
    ownership_digest,
)


def valid_evidence():
    return OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:ref:001",
        control_key_fingerprint="key:abc123",
        work_reference="work:challenge:001",
        concept_reference="concept:demo:001",
        coc_reference="coc:digest:001",
        stake_reference="stake:bond:001",
        issued_at="2026-09-15T22:00:00Z",
        expires_at="2026-09-16T22:00:00Z",
        previous_poo_digest=None,
        asset_fingerprint_bound=True,
        claimant_identity_bound=True,
        title_or_provenance_bound=True,
        pow_verified=True,
        poc_concept_verified=True,
        coc_verified=True,
        pos_bond_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def test_all_required_predicates_issue_technical_attestation_only():
    d = evaluate_ownership(valid_evidence())
    assert d.poo_valid is True
    assert d.technical_ownership_attested is True
    assert d.legal_ownership_established is False
    assert d.status == "TECHNICAL_OWNERSHIP_ATTESTATION"
    assert d.missing_predicates == []


def test_each_independent_leg_is_fail_closed():
    base = valid_evidence()
    for field in (
        "asset_fingerprint_bound",
        "claimant_identity_bound",
        "title_or_provenance_bound",
        "pow_verified",
        "poc_concept_verified",
        "coc_verified",
        "pos_bond_verified",
        "freshness_verified",
        "not_revoked",
    ):
        d = evaluate_ownership(replace(base, **{field: False}))
        assert d.poo_valid is False, field
        assert d.technical_ownership_attested is False, field
        assert d.missing_predicates, field


def test_empty_coc_reference_blocks_ownership_even_when_boolean_is_true():
    d = evaluate_ownership(replace(valid_evidence(), coc_reference=""))
    assert d.poo_valid is False
    assert "coc_reference must be non-empty" in d.missing_predicates


def test_external_title_reference_does_not_create_legal_ownership_claim():
    d = evaluate_ownership(replace(valid_evidence(), external_title_reference_verified=True))
    assert d.poo_valid is True
    assert d.status == "TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE"
    assert d.legal_ownership_established is False
    assert d.claims_boundary["legal_title_adjudicated"] is False


def test_proof_of_concept_does_not_substitute_for_coc():
    e = replace(valid_evidence(), coc_verified=False)
    d = evaluate_ownership(e)
    assert d.poo_valid is False
    assert e.poc_concept_verified is True
    assert "COC not verified" in d.missing_predicates


def test_coc_does_not_substitute_for_proof_of_concept():
    e = replace(valid_evidence(), poc_concept_verified=False)
    d = evaluate_ownership(e)
    assert d.poo_valid is False
    assert e.coc_verified is True
    assert "PoC concept not verified" in d.missing_predicates


def test_stake_or_work_cannot_compensate_for_missing_coc():
    e = replace(valid_evidence(), coc_verified=False)
    d = evaluate_ownership(e)
    assert d.poo_valid is False
    assert "COC not verified" in d.missing_predicates


def test_revocation_is_terminal_for_current_attestation():
    d = evaluate_ownership(replace(valid_evidence(), not_revoked=False))
    assert d.poo_valid is False
    assert "claim revoked" in d.missing_predicates


def test_digest_is_deterministic_and_transfer_chain_sensitive():
    e = valid_evidence()
    assert ownership_digest(e) == ownership_digest(e)
    chained = replace(e, previous_poo_digest="deadbeef")
    assert ownership_digest(chained) != ownership_digest(e)


def test_concept_and_coc_references_are_semantically_committed():
    e = valid_evidence()
    changed_concept = replace(e, concept_reference="concept:demo:002")
    changed_coc = replace(e, coc_reference="coc:digest:002")
    assert ownership_digest(changed_concept) != ownership_digest(e)
    assert ownership_digest(changed_coc) != ownership_digest(e)


def test_evidence_flags_do_not_change_semantic_digest():
    e = valid_evidence()
    altered = replace(e, pos_bond_verified=False)
    assert ownership_digest(altered) == ownership_digest(e)
