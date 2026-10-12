from dataclasses import replace

from security.poo.coc_guard import COCEvidence, coc_digest, evaluate_coc


def valid_coc():
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        control_key_fingerprint="key:abc123",
        custody_reference="custody:record:001",
        custody_point_reference="custody:point:001",
        challenge_reference="challenge:coc:001",
        observed_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def test_valid_coc_is_technical_attestation_only():
    d = evaluate_coc(valid_coc())
    assert d.coc_valid is True
    assert d.technical_control_custody_attested is True
    assert d.legal_custody_established is False
    assert d.status == "TECHNICAL_COC_ATTESTATION"


def test_each_coc_predicate_is_fail_closed():
    base = valid_coc()
    for field in (
        "asset_binding_verified",
        "claimant_binding_verified",
        "custody_or_control_verified",
        "challenge_response_verified",
        "custody_chain_verified",
        "freshness_verified",
        "not_revoked",
    ):
        d = evaluate_coc(replace(base, **{field: False}))
        assert d.coc_valid is False, field
        assert d.missing_predicates, field


def test_coc_digest_binds_point_of_custody_and_lineage():
    base = valid_coc()
    moved = replace(base, custody_point_reference="custody:point:002")
    chained = replace(base, previous_coc_digest="prior-coc-digest")
    assert coc_digest(base) != coc_digest(moved)
    assert coc_digest(base) != coc_digest(chained)


def test_verification_flags_do_not_change_semantic_coc_digest():
    base = valid_coc()
    altered = replace(base, freshness_verified=False)
    assert coc_digest(base) == coc_digest(altered)


def test_empty_semantic_binding_blocks_coc():
    d = evaluate_coc(replace(valid_coc(), custody_reference=""))
    assert d.coc_valid is False
    assert "COC custody_reference must be non-empty" in d.missing_predicates


def test_coc_never_implies_legal_title_or_transfer_authority():
    d = evaluate_coc(valid_coc())
    assert d.legal_custody_established is False
    assert d.claims_boundary["legal_title_adjudicated"] is False
    assert d.claims_boundary["transfer_execution_authority"] is False
    assert d.claims_boundary["live_value_authority"] is False
