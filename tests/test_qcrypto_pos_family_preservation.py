from __future__ import annotations

import pytest

from security.qcrypto.pos_family_preservation import (
    PROFILES,
    MigrationStage,
    activate_pq,
    migrate,
    protected_projection,
    run_family_preservation_proof,
    sunset_classical,
    vote_weight_once,
    _sample_state,
)


EXPECTED_PROFILES = {
    "ETHEREUM",
    "SOLANA",
    "CARDANO",
    "POLKADOT",
    "COMETBFT",
    "AVALANCHE",
    "ALGORAND",
    "NEAR",
    "TEZOS",
    "APTOS",
    "SUI",
    "POLYGON_POS",
    "BNB_CHAIN",
    "TRON",
    "CELESTIA",
    "FLOW",
    "HEDERA",
    "TON",
    "MULTIVERSX",
}


def test_major_pos_family_coverage_is_explicit() -> None:
    assert set(PROFILES) == EXPECTED_PROFILES
    assert all(profile.source_urls for profile in PROFILES.values())
    assert all("consensus_weight" in profile.protected_fields for profile in PROFILES.values())
    assert all(profile.reviewed_pq_status for profile in PROFILES.values())


@pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILES))
def test_each_profile_preserves_declared_state(profile_id: str) -> None:
    profile = PROFILES[profile_id]
    base = _sample_state(profile, 0)
    before = protected_projection(base)
    path = migrate(base, f"ML-DSA-65:{profile_id}:test")
    assert path[-1].stage is MigrationStage.CLASSICAL_DISABLED
    assert all(protected_projection(stage) == before for stage in path)


@pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILES))
def test_each_profile_rejects_invalid_order(profile_id: str) -> None:
    base = _sample_state(PROFILES[profile_id], 0)
    with pytest.raises(ValueError):
        sunset_classical(base)
    registered = migrate(base, f"ML-DSA-65:{profile_id}:test")[0]
    with pytest.raises(ValueError):
        activate_pq(registered)


@pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILES))
def test_hybrid_evidence_cannot_double_count_weight(profile_id: str) -> None:
    profile = PROFILES[profile_id]
    states = [
        migrate(_sample_state(profile, 0), f"ML-DSA-65:{profile_id}:0")[-1],
        migrate(_sample_state(profile, 1), f"ML-DSA-65:{profile_id}:1")[-1],
    ]
    ids = [state.stable_identity for state in states]
    expected = sum(int(state.protected_map()["consensus_weight"]) for state in states)
    assert vote_weight_once(states, ids + ids + ids) == expected


def test_family_proof_passes_with_claims_boundary() -> None:
    report = run_family_preservation_proof()
    assert report.status == "PASS"
    assert report.claim_state == "BOUNDED_MULTI_POS_MIGRATION_PRESERVATION_PROVEN_IN_SOFTWARE"
    assert report.profiles_checked == len(EXPECTED_PROFILES)
    assert report.transition_cases == len(EXPECTED_PROFILES) * 2 * 4
    assert report.invalid_order_cases == len(EXPECTED_PROFILES) * 2
    assert report.duplicate_weight_cases == len(EXPECTED_PROFILES)
    assert any("literally enumerates every" in claim for claim in report.excluded_claims)
