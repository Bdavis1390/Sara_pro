from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
)
from worldshepherd_sara.sda_release_authorization import (
    SdaReleaseCandidate,
    VerifiedSdaReleaseAuthorization,
)
from worldshepherd_sara.sda_release_fence import (
    SdaReleaseExecutionFence,
    SdaReleaseFenceConflict,
    SdaReleaseFenceState,
)


NOW = datetime(2026, 9, 18, 3, 0, tzinfo=timezone.utc)
TOKEN_A = "claim-token-a-0123456789"
TOKEN_B = "claim-token-b-0123456789"


def authorization(
    *,
    expires_at: datetime = NOW + timedelta(minutes=4),
) -> VerifiedSdaReleaseAuthorization:
    return VerifiedSdaReleaseAuthorization(
        authorization_id="SDA-RELEASE-FENCE-001",
        action="DISSEMINATE_ANALYTIC_EVIDENCE",
        hypothesis_set_digest="sha256:" + "a" * 64,
        payload_digest="sha256:" + "b" * 64,
        policy_revision_digest="sha256:" + "c" * 64,
        destination="INTERNAL:OVERWATCH",
        releasability_tags=["INTERNAL", "SYNTHETIC"],
        human_approval_id="HUMAN-FENCE-001",
        human_approver="identified-human-authority",
        key_id="FENCE-K1",
        key_fingerprint_sha256="d" * 64,
        issued_at=NOW - timedelta(seconds=10),
        expires_at=expires_at,
        nonce="release-fence-nonce-0001",
    )


def candidate(**overrides) -> SdaReleaseCandidate:
    values = {
        "hypothesis_set_digest": "sha256:" + "a" * 64,
        "payload_digest": "sha256:" + "b" * 64,
        "policy_revision_digest": "sha256:" + "c" * 64,
        "destination": "INTERNAL:OVERWATCH",
        "releasability_tags": ["INTERNAL", "SYNTHETIC"],
    }
    values.update(overrides)
    return SdaReleaseCandidate.model_validate(values)


def fence(tmp_path, *, lease_seconds: int = 30) -> SdaReleaseExecutionFence:
    return SdaReleaseExecutionFence(
        (tmp_path / "release-fence").resolve(),
        claim_lease=timedelta(seconds=lease_seconds),
    )


def test_happy_path_is_durable_verified_claimed_invoking_consumed(tmp_path):
    first = fence(tmp_path)
    registered = first.register_verified(authorization(), candidate(), now=NOW)
    assert registered.state == SdaReleaseFenceState.VERIFIED

    claimed = first.claim(
        registered.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )
    assert claimed.state == SdaReleaseFenceState.CLAIMED
    assert claimed.attempt_count == 1

    # A separate fence instance simulates a second process sharing the same DB.
    second_process = fence(tmp_path)
    invoking = second_process.mark_invoking(
        registered.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=2),
    )
    assert invoking.state == SdaReleaseFenceState.INVOKING
    assert invoking.claim_expires_at is None

    consumed = first.finalize_success(
        registered.authorization_id,
        owner="worker-a",
        claim_token=TOKEN_A,
        result_evidence_ref="echo://delivery/receipt-001",
        now=NOW + timedelta(seconds=3),
    )
    assert consumed.state == SdaReleaseFenceState.CONSUMED
    assert consumed.receipt is not None
    assert consumed.receipt.authorization_id == registered.authorization_id
    assert consumed.receipt.human_approval_id == "HUMAN-FENCE-001"
    assert consumed.result_evidence_ref == "echo://delivery/receipt-001"

    reopened = fence(tmp_path)
    retained = reopened.get(registered.authorization_id)
    assert retained is not None
    assert retained.state == SdaReleaseFenceState.CONSUMED
    assert [item["to_state"] for item in reopened.transitions(registered.authorization_id)] == [
        "VERIFIED",
        "CLAIMED",
        "INVOKING",
        "CONSUMED",
    ]


def test_active_claim_blocks_second_process_duplicate_claim(tmp_path):
    first = fence(tmp_path)
    auth = authorization()
    first.register_verified(auth, candidate(), now=NOW)
    first.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )

    second = fence(tmp_path)
    with pytest.raises(SdaReleaseFenceConflict, match="active claim"):
        second.claim(
            auth.authorization_id,
            candidate(),
            owner="worker-b",
            claim_token=TOKEN_B,
            now=NOW + timedelta(seconds=2),
        )

    retained = second.get(auth.authorization_id)
    assert retained is not None
    assert retained.attempt_count == 1
    assert retained.claim_owner == "worker-a"


def test_expired_claim_can_be_reclaimed_only_before_invoking(tmp_path):
    store = fence(tmp_path, lease_seconds=5)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)
    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )

    reclaimed = store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-b",
        claim_token=TOKEN_B,
        now=NOW + timedelta(seconds=7),
    )
    assert reclaimed.state == SdaReleaseFenceState.CLAIMED
    assert reclaimed.claim_owner == "worker-b"
    assert reclaimed.attempt_count == 2


def test_exact_candidate_is_rechecked_at_claim_and_invocation(tmp_path):
    store = fence(tmp_path)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)

    changed = candidate(destination="PARTNER:OTHER")
    with pytest.raises(SdaReleaseFenceConflict, match="changed"):
        store.claim(
            auth.authorization_id,
            changed,
            owner="worker-a",
            claim_token=TOKEN_A,
            now=NOW + timedelta(seconds=1),
        )

    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=2),
    )
    changed = candidate(payload_digest="sha256:" + "e" * 64)
    with pytest.raises(SdaReleaseFenceConflict, match="changed"):
        store.mark_invoking(
            auth.authorization_id,
            changed,
            owner="worker-a",
            claim_token=TOKEN_A,
            now=NOW + timedelta(seconds=3),
        )


def test_expired_authorization_cannot_cross_invocation_boundary(tmp_path):
    store = fence(tmp_path)
    auth = authorization(expires_at=NOW + timedelta(seconds=4))
    store.register_verified(auth, candidate(), now=NOW)
    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )

    with pytest.raises(PrimeSentinelAuthorizationError, match="expired before use"):
        store.mark_invoking(
            auth.authorization_id,
            candidate(),
            owner="worker-a",
            claim_token=TOKEN_A,
            now=NOW + timedelta(seconds=5),
        )


def test_invoking_state_survives_restart_and_forbids_automatic_retry(tmp_path):
    store = fence(tmp_path)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)
    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )
    store.mark_invoking(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=2),
    )

    reopened = fence(tmp_path)
    with pytest.raises(SdaReleaseFenceConflict, match="unsafe state INVOKING"):
        reopened.claim(
            auth.authorization_id,
            candidate(),
            owner="worker-b",
            claim_token=TOKEN_B,
            now=NOW + timedelta(minutes=1),
        )


def test_acknowledgement_loss_becomes_indeterminate_and_never_auto_retries(tmp_path):
    store = fence(tmp_path)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)
    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )
    store.mark_invoking(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=2),
    )

    uncertain = store.finalize_indeterminate(
        auth.authorization_id,
        owner="worker-a",
        claim_token=TOKEN_A,
        result_evidence_ref="echo://delivery/ack-lost-001",
        now=NOW + timedelta(seconds=3),
    )
    assert uncertain.state == SdaReleaseFenceState.INDETERMINATE
    assert uncertain.receipt is None
    assert store.health()["indeterminate_records"] == 1

    with pytest.raises(SdaReleaseFenceConflict, match="unsafe state INDETERMINATE"):
        store.claim(
            auth.authorization_id,
            candidate(),
            owner="worker-b",
            claim_token=TOKEN_B,
            now=NOW + timedelta(minutes=1),
        )

    with pytest.raises(SdaReleaseFenceConflict, match="only from INVOKING"):
        store.finalize_success(
            auth.authorization_id,
            owner="worker-a",
            claim_token=TOKEN_A,
            result_evidence_ref="late-ack",
            now=NOW + timedelta(minutes=1),
        )


def test_wrong_claim_owner_or_token_cannot_advance_or_finalize(tmp_path):
    store = fence(tmp_path)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)
    store.claim(
        auth.authorization_id,
        candidate(),
        owner="worker-a",
        claim_token=TOKEN_A,
        now=NOW + timedelta(seconds=1),
    )

    with pytest.raises(SdaReleaseFenceConflict, match="owner mismatch"):
        store.mark_invoking(
            auth.authorization_id,
            candidate(),
            owner="worker-b",
            claim_token=TOKEN_A,
            now=NOW + timedelta(seconds=2),
        )

    with pytest.raises(SdaReleaseFenceConflict, match="token mismatch"):
        store.mark_invoking(
            auth.authorization_id,
            candidate(),
            owner="worker-a",
            claim_token=TOKEN_B,
            now=NOW + timedelta(seconds=2),
        )


def test_health_detects_candidate_semantic_tampering(tmp_path):
    store = fence(tmp_path)
    auth = authorization()
    store.register_verified(auth, candidate(), now=NOW)

    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE releases SET candidate_digest=? WHERE authorization_id=?",
            ("sha256:" + "f" * 64, auth.authorization_id),
        )
        connection.commit()
    finally:
        connection.close()

    health = store.health()
    assert health["ok"] is False
    assert health["semantic_integrity_errors"] == 1
