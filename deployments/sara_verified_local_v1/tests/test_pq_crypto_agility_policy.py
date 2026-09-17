from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.pq_crypto_agility_policy import (
    DEFAULT_PQ_SUITE_ID,
    PqCryptoAgilityPolicy,
    PqCryptoAgilityPolicyError,
    PqSignatureSuite,
    default_mldsa65_policy,
    load_pq_crypto_agility_policy_from_environment,
)


NOW = datetime(2026, 9, 17, 19, 0, tzinfo=timezone.utc)


def _policy(**updates):
    raw = default_mldsa65_policy(
        policy_id="WS-PQ-POLICY-POO-001",
        epoch=7,
        effective_at=NOW - timedelta(minutes=5),
    ).model_dump(mode="json")
    raw.update(updates)
    return PqCryptoAgilityPolicy.model_validate(raw)


def test_policy_digest_is_deterministic_and_epoch_sensitive():
    a = _policy()
    b = _policy()
    assert a.digest == b.digest
    c = _policy(epoch=8)
    assert c.digest != a.digest


def test_active_suite_must_be_accepted_and_active():
    with pytest.raises(ValidationError, match="active_suite_id must be accepted"):
        _policy(accepted_suite_ids=["other-suite"])
    suite = PqSignatureSuite(
        suite_id=DEFAULT_PQ_SUITE_ID,
        algorithm="ML-DSA-65",
        standard="FIPS-204",
        signature_context="WS-POO-PQ-COMMIT-V1",
        status="VERIFY_ONLY",
    )
    with pytest.raises(ValidationError, match="active suite must have ACTIVE status"):
        _policy(suites=[suite.model_dump(mode="json")])


def test_disabled_suite_cannot_remain_accepted():
    disabled = PqSignatureSuite(
        suite_id="WS-PQ-SUITE-OLD-V1",
        algorithm="OLD-PQ",
        standard="OLD-STANDARD",
        signature_context="OLD-CONTEXT",
        status="DISABLED",
    )
    active = PqSignatureSuite(
        suite_id=DEFAULT_PQ_SUITE_ID,
        algorithm="ML-DSA-65",
        standard="FIPS-204",
        signature_context="WS-POO-PQ-COMMIT-V1",
        status="ACTIVE",
    )
    with pytest.raises(ValidationError, match="disabled suite cannot remain accepted"):
        _policy(
            accepted_suite_ids=[DEFAULT_PQ_SUITE_ID, disabled.suite_id],
            suites=[active.model_dump(mode="json"), disabled.model_dump(mode="json")],
        )


def test_verify_only_suite_supports_bounded_transition_but_not_new_issuance():
    old = PqSignatureSuite(
        suite_id="WS-PQ-SUITE-OLD-V1",
        algorithm="OLD-PQ",
        standard="OLD-STANDARD",
        signature_context="OLD-CONTEXT",
        status="VERIFY_ONLY",
    )
    active = PqSignatureSuite(
        suite_id=DEFAULT_PQ_SUITE_ID,
        algorithm="ML-DSA-65",
        standard="FIPS-204",
        signature_context="WS-POO-PQ-COMMIT-V1",
        status="ACTIVE",
    )
    policy = _policy(
        accepted_suite_ids=[DEFAULT_PQ_SUITE_ID, old.suite_id],
        suites=[active.model_dump(mode="json"), old.model_dump(mode="json")],
    )
    assert policy.assert_verification_allowed(old.suite_id, now=NOW).status == "VERIFY_ONLY"
    with pytest.raises(PqCryptoAgilityPolicyError, match="not the active issuance suite"):
        policy.assert_issuance_allowed(old.suite_id, now=NOW)


def test_policy_effective_and_expiry_windows_fail_closed():
    future = _policy(effective_at=(NOW + timedelta(minutes=1)).isoformat())
    with pytest.raises(PqCryptoAgilityPolicyError, match="not yet effective"):
        future.assert_verification_allowed(DEFAULT_PQ_SUITE_ID, now=NOW)
    expired = _policy(
        effective_at=(NOW - timedelta(hours=2)).isoformat(),
        expires_at=(NOW - timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(PqCryptoAgilityPolicyError, match="expired"):
        expired.assert_verification_allowed(DEFAULT_PQ_SUITE_ID, now=NOW)


def test_required_environment_policy_missing_or_malformed_fails_closed(monkeypatch):
    monkeypatch.setenv("POO_REQUIRE_PQ_AGILITY_POLICY", "1")
    monkeypatch.delenv("PRIME_SENTINEL_PQ_POLICY_JSON", raising=False)
    with pytest.raises(RuntimeError, match="required by policy"):
        load_pq_crypto_agility_policy_from_environment()
    monkeypatch.setenv("PRIME_SENTINEL_PQ_POLICY_JSON", "{not-json")
    with pytest.raises(RuntimeError, match="is invalid"):
        load_pq_crypto_agility_policy_from_environment()


def test_policy_forbids_downgrade_flag():
    with pytest.raises(ValidationError):
        _policy(allow_algorithm_downgrade=True)
