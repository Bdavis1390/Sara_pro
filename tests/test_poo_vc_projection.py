from dataclasses import replace

from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.interop.vc_projection import MAPPING_SCHEMA, VC20_CONTEXT, project_vc20_mapping
from security.poo.ownership_guard import OwnershipEvidence


def valid_coc():
    return COCEvidence(
        asset_id="asset:vc:001",
        claimant_id="did:example:alice",
        control_key_fingerprint="key:vc:alice",
        custody_reference="custody:vc:001",
        custody_point_reference="point:vc:001",
        challenge_reference="challenge:vc:001",
        observed_at="2026-09-16T18:00:00Z",
        expires_at="2026-09-17T18:00:00Z",
        previous_coc_digest=None,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def valid_ownership(coc):
    return OwnershipEvidence(
        asset_id=coc.asset_id,
        claimant_id=coc.claimant_id,
        title_reference="provenance:vc:001",
        control_key_fingerprint=coc.control_key_fingerprint,
        work_reference="work:vc:001",
        concept_reference="concept:vc:001",
        coc_reference=coc_digest(coc),
        stake_reference="stake:vc:001",
        issued_at="2026-09-16T18:00:00Z",
        expires_at="2026-09-17T18:00:00Z",
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


def test_valid_mapping_is_review_ready_but_not_conformant_or_issued():
    coc = valid_coc()
    ownership = valid_ownership(coc)
    decision = project_vc20_mapping(
        ownership,
        coc,
        issuer_id="did:example:worldshepherd-review-issuer",
        credential_id="urn:uuid:poo-vc-review-001",
    )
    assert decision.schema == MAPPING_SCHEMA
    assert decision.status == "READY_FOR_STANDARDS_REVIEW"
    assert decision.mapping_ready_for_external_review is True
    assert decision.vc20_core_projection["@context"] == [VC20_CONTEXT]
    assert decision.vc20_core_projection["type"] == ["VerifiableCredential"]
    assert decision.vc20_core_projection["credentialSubject"] == {"id": ownership.claimant_id}
    assert decision.extension_candidates["cocDigest"] == coc_digest(coc)
    assert decision.extension_candidates["technicalOwnershipOnly"] is True
    assert decision.extension_candidates["legalOwnershipEstablished"] is False
    assert decision.vc20_conformance_established is False
    assert decision.did_conformance_established is False
    assert decision.openid4vp_conformance_established is False
    assert decision.credential_issued is False
    assert decision.credential_signed is False
    assert decision.issuer_authority_established is False
    assert decision.legal_ownership_established is False


def test_core_projection_does_not_fabricate_proof_status_or_custom_vocabulary():
    coc = valid_coc()
    decision = project_vc20_mapping(valid_ownership(coc), coc, issuer_id="did:example:issuer")
    core = decision.vc20_core_projection
    assert "proof" not in core
    assert "credentialStatus" not in core
    assert "evidence" not in core
    assert "cocDigest" not in core
    assert "pooDigest" not in core
    assert decision.claims_boundary["proof_generated"] is False
    assert decision.claims_boundary["credential_status_generated"] is False
    assert decision.claims_boundary["custom_vocabulary_standardized"] is False


def test_mismatched_coc_digest_fails_closed():
    coc = valid_coc()
    ownership = replace(valid_ownership(coc), coc_reference="0" * 64)
    decision = project_vc20_mapping(ownership, coc, issuer_id="did:example:issuer")
    assert decision.mapping_ready_for_external_review is False
    assert decision.status == "BLOCKED_MAPPING_INPUT"
    assert "PoO COC reference does not match supplied COC digest" in decision.unresolved_mapping_questions


def test_asset_claimant_and_control_key_mismatch_each_block_mapping():
    coc = valid_coc()
    ownership = valid_ownership(coc)
    cases = (
        replace(coc, asset_id="asset:other"),
        replace(coc, claimant_id="did:example:other"),
        replace(coc, control_key_fingerprint="key:other"),
    )
    expected = (
        "PoO/COC asset mismatch",
        "PoO/COC claimant mismatch",
        "PoO/COC control-key mismatch",
    )
    for altered, reason in zip(cases, expected):
        decision = project_vc20_mapping(ownership, altered, issuer_id="did:example:issuer")
        assert decision.mapping_ready_for_external_review is False
        assert reason in decision.unresolved_mapping_questions


def test_missing_issuer_blocks_mapping_and_never_self_authorizes_issuer():
    coc = valid_coc()
    decision = project_vc20_mapping(valid_ownership(coc), coc, issuer_id="")
    assert decision.mapping_ready_for_external_review is False
    assert "issuer_id must be non-empty" in decision.unresolved_mapping_questions
    assert decision.issuer_authority_established is False


def test_mapping_digest_changes_with_issuer_or_credential_id():
    coc = valid_coc()
    ownership = valid_ownership(coc)
    a = project_vc20_mapping(ownership, coc, issuer_id="did:example:a", credential_id="urn:uuid:a")
    b = project_vc20_mapping(ownership, coc, issuer_id="did:example:b", credential_id="urn:uuid:a")
    c = project_vc20_mapping(ownership, coc, issuer_id="did:example:a", credential_id="urn:uuid:c")
    assert a.mapping_digest != b.mapping_digest
    assert a.mapping_digest != c.mapping_digest


def test_unresolved_questions_keep_standards_and_privacy_work_explicit():
    coc = valid_coc()
    decision = project_vc20_mapping(valid_ownership(coc), coc, issuer_id="did:example:issuer")
    joined = " ".join(decision.unresolved_mapping_questions).lower()
    assert "vocabulary" in joined
    assert "credential status" in joined
    assert "did/controller" in joined
    assert "openid4vp" in joined
    assert "privacy" in joined
    assert decision.claims_boundary["w3c_conformance_claimed"] is False
    assert decision.claims_boundary["openid_conformance_claimed"] is False
    assert decision.claims_boundary["external_validation_established"] is False
