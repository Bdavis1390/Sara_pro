from __future__ import annotations

import pytest

from security.qcrypto.qpos_preservation import (
    AuthMode,
    ValidatorState,
    accepted_authentication,
    activate_pq_primary,
    assert_preserved,
    disable_classical_auth,
    economic_projection,
    enter_emergency_pq,
    migrate_full_path,
    pq_ready_stake_fraction,
    register_pq_credential,
    require_hybrid_auth,
    run_bounded_preservation_proof,
    set_aggregator_eligibility,
    supermajority_threshold,
    total_effective_balance,
    validate_registry,
    vote_weight_once,
)


def base_validator(name: str = "v1", stake: int = 32, effective: int = 32) -> ValidatorState:
    return ValidatorState(
        validator_id=name,
        stake=stake,
        effective_balance=effective,
        withdrawal_owner=f"withdraw-{name}",
        slashed=False,
        slashing_history=("genesis",),
        classical_credential=f"classical-{name}",
    )


def test_full_migration_preserves_economic_projection() -> None:
    base = base_validator()
    path = migrate_full_path(base, pq_credential="pq-v1", pq_scheme="TEST_PQ")
    assert path[-1].auth_mode is AuthMode.CLASSICAL_DISABLED
    for stage in path:
        assert economic_projection(stage) == economic_projection(base)
        assert_preserved(base, stage)


def test_slashing_and_withdrawal_history_survive_every_stage() -> None:
    base = ValidatorState(
        validator_id="slash-history",
        stake=64,
        effective_balance=32,
        withdrawal_owner="cold-withdrawal-owner",
        slashed=True,
        slashing_history=("double-vote:epoch-10", "exit:epoch-11"),
        classical_credential="legacy-key",
    )
    path = migrate_full_path(base, pq_credential="pq-key", pq_scheme="TEST_PQ")
    emergency = enter_emergency_pq(path[0])
    for stage in (*path, emergency):
        assert stage.withdrawal_owner == base.withdrawal_owner
        assert stage.slashed is True
        assert stage.slashing_history == base.slashing_history
        assert stage.stake == base.stake
        assert stage.effective_balance == base.effective_balance


def test_hybrid_credentials_never_double_count_stake() -> None:
    validators = (
        migrate_full_path(base_validator("a", 32, 32), pq_credential="pq-a", pq_scheme="TEST_PQ")[-1],
        migrate_full_path(base_validator("b", 64, 48), pq_credential="pq-b", pq_scheme="TEST_PQ")[-1],
    )
    expected = total_effective_balance(validators)
    duplicated_id_evidence = ["a", "a", "b", "b", "a"]
    assert vote_weight_once(validators, duplicated_id_evidence) == expected


def test_supermajority_threshold_is_credential_scheme_invariant() -> None:
    before = (
        base_validator("a", 32, 32),
        base_validator("b", 64, 48),
        base_validator("c", 16, 16),
    )
    after = tuple(
        migrate_full_path(v, pq_credential=f"pq-{v.validator_id}", pq_scheme="TEST_PQ")[-1]
        for v in before
    )
    assert total_effective_balance(before) == total_effective_balance(after)
    assert supermajority_threshold(before) == supermajority_threshold(after)


def test_authentication_policy_moves_from_classical_to_pq_without_weight_change() -> None:
    base = base_validator()
    registered = register_pq_credential(base, credential="pq-v1", scheme="TEST_PQ")
    hybrid = require_hybrid_auth(registered)
    primary = activate_pq_primary(hybrid)
    sunset = disable_classical_auth(primary)

    assert accepted_authentication(base, ["classical"])
    assert accepted_authentication(registered, ["classical"])
    assert not accepted_authentication(hybrid, ["classical"])
    assert not accepted_authentication(hybrid, ["pq"])
    assert accepted_authentication(hybrid, ["classical", "pq"])
    assert accepted_authentication(primary, ["pq"])
    assert not accepted_authentication(primary, ["classical"])
    assert accepted_authentication(sunset, ["pq"])
    assert not accepted_authentication(sunset, ["classical"])

    for state in (registered, hybrid, primary, sunset):
        assert state.effective_balance == base.effective_balance


def test_emergency_pq_requires_pre_registered_pq_credential() -> None:
    with pytest.raises(ValueError):
        enter_emergency_pq(base_validator())

    registered = register_pq_credential(base_validator(), credential="pq-v1", scheme="TEST_PQ")
    emergency = enter_emergency_pq(registered)
    assert emergency.auth_mode is AuthMode.EMERGENCY_PQ
    assert economic_projection(emergency) == economic_projection(base_validator())


def test_aggregator_role_cannot_change_stake_weight() -> None:
    state = migrate_full_path(base_validator(), pq_credential="pq-v1", pq_scheme="TEST_PQ")[-1]
    enabled = set_aggregator_eligibility(state, True)
    disabled = set_aggregator_eligibility(enabled, False)
    assert enabled.aggregator_eligible is True
    assert disabled.aggregator_eligible is False
    assert economic_projection(enabled) == economic_projection(state)
    assert economic_projection(disabled) == economic_projection(state)


def test_duplicate_validator_or_pq_identity_fails_closed() -> None:
    a = migrate_full_path(base_validator("a"), pq_credential="pq-shared", pq_scheme="TEST_PQ")[-1]
    b = migrate_full_path(base_validator("b"), pq_credential="pq-b", pq_scheme="TEST_PQ")[-1]
    validate_registry((a, b))

    with pytest.raises(ValueError):
        validate_registry((a, a))

    b_shared = migrate_full_path(base_validator("b"), pq_credential="pq-shared", pq_scheme="TEST_PQ")[-1]
    with pytest.raises(ValueError):
        validate_registry((a, b_shared))


def test_pq_readiness_is_stake_weighted_not_validator_count() -> None:
    small_a = migrate_full_path(base_validator("small-a", 1, 1), pq_credential="pq-a", pq_scheme="TEST_PQ")[-1]
    small_b = migrate_full_path(base_validator("small-b", 1, 1), pq_credential="pq-b", pq_scheme="TEST_PQ")[-1]
    large = base_validator("large", 98, 98)
    validators = (small_a, small_b, large)

    assert 2 / 3 > 0.5  # validator-count majority is migrated
    assert pq_ready_stake_fraction(validators) == pytest.approx(0.02)


def test_invalid_transition_order_fails_closed() -> None:
    base = base_validator()
    with pytest.raises(ValueError):
        disable_classical_auth(base)
    with pytest.raises(ValueError):
        activate_pq_primary(base)

    registered = register_pq_credential(base, credential="pq-v1", scheme="TEST_PQ")
    with pytest.raises(ValueError):
        activate_pq_primary(registered)


def test_bounded_preservation_proof_passes_and_keeps_claims_bounded() -> None:
    report = run_bounded_preservation_proof()
    assert report.proof_status == "PASS"
    assert report.claim_state == "BOUNDED_MODEL_PROOF_OF_POS_MIGRATION_PRESERVATION"
    assert report.validator_transition_cases > 0
    assert report.validator_set_cases > 0
    assert report.hybrid_double_count_cases == report.validator_set_cases
    assert report.invalid_transition_cases > 0
    assert any("quantum-resistant" in assumption for assumption in report.assumptions)
    assert any("No proof of ML-DSA" in claim for claim in report.excluded_claims)
