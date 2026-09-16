from __future__ import annotations

from collections import Counter

import pytest

from security.qcrypto.pos_family_preservation import PROFILES
from security.qcrypto.pos_pq_benchmarks import BENCHMARKS
from security.qcrypto.pq_signature_interop import (
    SCHEMES,
    ValidatorAuthorizationEnvelope,
    benchmark_envelope,
    family_envelope,
    run_all_interop_probes,
    run_benchmark_interop_probes,
    run_family_interop_probes,
    run_interop_probe,
)


def sample_envelope() -> ValidatorAuthorizationEnvelope:
    return ValidatorAuthorizationEnvelope(
        validator_id="validator-test-1",
        chain_family="TEST_POS",
        migration_epoch=7,
        purpose="PQ_INTEROP_TEST_ONLY",
        economic_state_digest="a" * 64,
        previous_credential_fingerprint="b" * 64,
    )


def test_supported_schemes_are_standards_backed_profiles() -> None:
    assert set(SCHEMES) == {"ML-DSA-65", "ML-DSA-87", "SLH-DSA-SHA2-128s"}


@pytest.mark.parametrize("scheme", tuple(SCHEMES))
def test_real_pq_signature_round_trip_and_negative_cases(scheme: str) -> None:
    result = run_interop_probe(scheme, sample_envelope())
    assert result.valid_signature_verified is True
    assert result.tampered_message_rejected is True
    assert result.wrong_key_rejected is True
    assert result.secret_material_retained is False
    assert result.public_key_bytes > 0
    assert result.signature_bytes > 0
    assert len(result.message_sha256) == 64
    assert len(result.public_key_fingerprint) == 64
    assert result.chain_family == "TEST_POS"


def test_canonical_envelope_is_deterministic() -> None:
    left = sample_envelope().canonical_bytes()
    right = sample_envelope().canonical_bytes()
    assert left == right
    assert b"validator-test-1" in left


def test_generic_baseline_probes_pass() -> None:
    results = run_all_interop_probes()
    assert len(results) == 3
    assert all(r.chain_family == "GENERIC_POS" for r in results)
    assert {r.scheme for r in results} == set(SCHEMES)
    assert all(r.valid_signature_verified for r in results)
    assert all(r.tampered_message_rejected for r in results)
    assert all(r.wrong_key_rejected for r in results)


def test_every_pos_profile_has_family_bound_envelope() -> None:
    for profile_id in PROFILES:
        envelope = family_envelope(profile_id)
        assert envelope.chain_family == profile_id
        assert envelope.validator_id.startswith(profile_id.lower())
        assert len(envelope.economic_state_digest) == 64
        assert len(envelope.previous_credential_fingerprint) == 64


def test_all_family_bound_pq_probes_pass() -> None:
    results = run_family_interop_probes()
    assert len(results) == len(PROFILES) * len(SCHEMES) == 57
    counts = Counter(result.chain_family for result in results)
    assert set(counts) == set(PROFILES)
    assert set(counts.values()) == {3}
    for profile_id in PROFILES:
        assert {r.scheme for r in results if r.chain_family == profile_id} == set(SCHEMES)
    assert all(r.valid_signature_verified for r in results)
    assert all(r.tampered_message_rejected for r in results)
    assert all(r.wrong_key_rejected for r in results)
    assert all(not r.secret_material_retained for r in results)


def test_external_qrl_benchmark_is_testnet_and_ml_dsa_87() -> None:
    assert set(BENCHMARKS) == {"QRL2_TESTNET"}
    benchmark = BENCHMARKS["QRL2_TESTNET"]
    assert benchmark.environment == "PUBLIC_TESTNET_V2"
    assert benchmark.production_mainnet_pq_consensus is False
    envelope = benchmark_envelope("QRL2_TESTNET")
    assert envelope.chain_family == "QRL2_TESTNET"

    results = run_benchmark_interop_probes()
    assert len(results) == 1
    result = results[0]
    assert result.chain_family == "QRL2_TESTNET"
    assert result.scheme == "ML-DSA-87"
    assert result.valid_signature_verified is True
    assert result.tampered_message_rejected is True
    assert result.wrong_key_rejected is True
    assert result.secret_material_retained is False


def test_unknown_family_benchmark_and_scheme_fail_closed() -> None:
    with pytest.raises(ValueError):
        family_envelope("NOT-A-POS-FAMILY")
    with pytest.raises(ValueError):
        benchmark_envelope("NOT-A-BENCHMARK")
    with pytest.raises(ValueError):
        run_interop_probe("NOT-A-SCHEME", sample_envelope())
