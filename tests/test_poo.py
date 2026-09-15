from security.ownership.poo import (
    OwnershipEvidence,
    assess_ownership,
    ownership_claim_digest,
    verify_work,
)


def _mine(asset_id: str, claimant_id: str, key_fingerprint: str, provenance_ref: str, bits: int = 8) -> tuple[str, int]:
    digest = ownership_claim_digest(
        asset_id=asset_id,
        claimant_id=claimant_id,
        key_fingerprint=key_fingerprint,
        provenance_ref=provenance_ref,
    )
    for nonce in range(1_000_000):
        if verify_work(claim_digest=digest, nonce=nonce, difficulty_bits=bits):
            return digest, nonce
    raise AssertionError("test nonce not found")


def _base_evidence(*, stake_verified: bool = True, control_verified: bool = True, provenance_verified: bool = True):
    asset_id = "asset:test:001"
    claimant_id = "claimant:test:alice"
    key_fingerprint = "sha256:test-key-fingerprint"
    provenance_ref = "echo:provenance:test-001"
    _, nonce = _mine(asset_id, claimant_id, key_fingerprint, provenance_ref)
    return OwnershipEvidence(
        asset_id=asset_id,
        claimant_id=claimant_id,
        key_fingerprint=key_fingerprint,
        provenance_ref=provenance_ref,
        control_challenge_ref="challenge:test-001",
        control_verified=control_verified,
        work_nonce=nonce,
        work_difficulty_bits=8,
        stake_amount=100.0,
        stake_unit="TEST",
        stake_lock_ref="bond:test-001",
        stake_attestation_verified=stake_verified,
        provenance_verified=provenance_verified,
    )


def test_all_four_gates_support_bonded_cryptographic_claim_but_not_legal_title():
    result = assess_ownership(_base_evidence(), minimum_work_bits=8, minimum_stake=10.0, required_stake_unit="TEST")
    assert result.state == "BONDED_CRYPTOGRAPHIC_OWNERSHIP_CLAIM"
    assert result.control_pass is True
    assert result.provenance_pass is True
    assert result.work_pass is True
    assert result.stake_pass is True
    assert result.legal_title_established is False


def test_pow_does_not_substitute_for_control_or_provenance():
    result = assess_ownership(
        _base_evidence(control_verified=False, provenance_verified=False),
        minimum_work_bits=8,
        minimum_stake=10.0,
    )
    assert result.work_pass is True
    assert result.state == "INSUFFICIENT_OWNERSHIP_EVIDENCE"
    assert result.legal_title_established is False


def test_pos_bond_does_not_substitute_for_key_control():
    result = assess_ownership(
        _base_evidence(control_verified=False),
        minimum_work_bits=8,
        minimum_stake=10.0,
    )
    assert result.stake_pass is True
    assert result.state == "INSUFFICIENT_OWNERSHIP_EVIDENCE"


def test_unverified_stake_fails_even_when_amount_is_large():
    evidence = _base_evidence(stake_verified=False)
    result = assess_ownership(evidence, minimum_work_bits=8, minimum_stake=1.0)
    assert result.stake_pass is False
    assert result.state == "INSUFFICIENT_OWNERSHIP_EVIDENCE"


def test_registry_linkage_strengthens_claim_but_still_does_not_establish_legal_title():
    base = _base_evidence()
    evidence = OwnershipEvidence(
        **{
            **base.__dict__,
            "trusted_registry_ref": "registry:test-authority:record-77",
            "trusted_registry_verified": True,
        }
    )
    result = assess_ownership(evidence, minimum_work_bits=8, minimum_stake=10.0)
    assert result.state == "REGISTRY_LINKED_OWNERSHIP_CLAIM"
    assert result.registry_linked is True
    assert result.legal_title_established is False


def test_wrong_stake_unit_fails_policy():
    result = assess_ownership(
        _base_evidence(),
        minimum_work_bits=8,
        minimum_stake=10.0,
        required_stake_unit="OTHER",
    )
    assert result.stake_pass is False
    assert result.state == "INSUFFICIENT_OWNERSHIP_EVIDENCE"


def test_invalid_work_policy_is_rejected():
    evidence = _base_evidence()
    try:
        assess_ownership(evidence, minimum_work_bits=33)
    except ValueError as exc:
        assert "minimum_work_bits" in str(exc)
    else:
        raise AssertionError("expected ValueError")
