from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.sda_release_authorization import (
    SDA_RELEASE_CONSUMPTIONS_KEY,
    SdaReleaseAuthorizationAssertion,
    SdaReleaseCandidate,
    canonical_sda_release_message,
    consume_sda_release_authorization,
    verify_sda_release_authorization,
)


NOW = datetime(2026, 9, 18, 1, 30, tzinfo=timezone.utc)
KEY_ID = "SDA-RELEASE-K1"
HYP_DIGEST = "sha256:" + "a" * 64
PAYLOAD_DIGEST = "sha256:" + "b" * 64
POLICY_DIGEST = "sha256:" + "c" * 64


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def materials():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            KEY_ID: b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def assertion(private: Ed25519PrivateKey, **overrides):
    values = {
        "key_id": KEY_ID,
        "authorization_id": "SDA-RELEASE-AUTH-001",
        "hypothesis_set_digest": HYP_DIGEST,
        "payload_digest": PAYLOAD_DIGEST,
        "policy_revision_digest": POLICY_DIGEST,
        "destination": "INTERNAL:OVERWATCH",
        "releasability_tags": ["INTERNAL", "SYNTHETIC"],
        "human_approval_id": "HUMAN-APPROVAL-001",
        "human_approver": "identified-human-authority",
        "issued_at": NOW - timedelta(seconds=5),
        "expires_at": NOW + timedelta(minutes=2),
        "nonce": "release-nonce-0000001",
        "signature_b64url": "placeholder",
    }
    values.update(overrides)
    unsigned = SdaReleaseAuthorizationAssertion.model_validate(values)
    return unsigned.model_copy(
        update={
            "signature_b64url": b64url(
                private.sign(canonical_sda_release_message(unsigned))
            )
        }
    )


def candidate(**overrides):
    values = {
        "hypothesis_set_digest": HYP_DIGEST,
        "payload_digest": PAYLOAD_DIGEST,
        "policy_revision_digest": POLICY_DIGEST,
        "destination": "INTERNAL:OVERWATCH",
        "releasability_tags": ["INTERNAL", "SYNTHETIC"],
    }
    values.update(overrides)
    return SdaReleaseCandidate.model_validate(values)


def test_public_key_only_verification_binds_human_policy_destination_and_digests():
    private, verifier = materials()
    verified = verify_sda_release_authorization(
        assertion(private),
        verifier=verifier,
        now=NOW,
    )

    assert verified.human_approval_id == "HUMAN-APPROVAL-001"
    assert verified.human_approver == "identified-human-authority"
    assert verified.hypothesis_set_digest == HYP_DIGEST
    assert verified.payload_digest == PAYLOAD_DIGEST
    assert verified.policy_revision_digest == POLICY_DIGEST
    assert verified.destination == "INTERNAL:OVERWATCH"
    assert verified.releasability_tags == ["INTERNAL", "SYNTHETIC"]
    assert len(verified.key_fingerprint_sha256) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hypothesis_set_digest", "sha256:" + "d" * 64),
        ("payload_digest", "sha256:" + "d" * 64),
        ("policy_revision_digest", "sha256:" + "d" * 64),
        ("destination", "PARTNER:OTHER"),
        ("releasability_tags", ["INTERNAL"]),
        ("human_approval_id", "OTHER-APPROVAL"),
        ("human_approver", "other-human"),
    ],
)
def test_signature_tamper_of_every_authority_semantic_field_fails(field, value):
    private, verifier = materials()
    signed = assertion(private)
    tampered = signed.model_copy(update={field: value})

    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        verify_sda_release_authorization(tampered, verifier=verifier, now=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hypothesis_set_digest", "sha256:" + "d" * 64),
        ("payload_digest", "sha256:" + "d" * 64),
        ("policy_revision_digest", "sha256:" + "d" * 64),
        ("destination", "PARTNER:OTHER"),
        ("releasability_tags", ["INTERNAL"]),
    ],
)
def test_toctou_candidate_mutation_after_signature_verification_fails(field, value):
    private, verifier = materials()
    verified = verify_sda_release_authorization(
        assertion(private),
        verifier=verifier,
        now=NOW,
    )
    changed = candidate(**{field: value})

    with pytest.raises(
        PrimeSentinelAuthorizationError,
        match="changed after authorization",
    ):
        consume_sda_release_authorization({}, verified, changed, now=NOW)


def test_one_time_consumption_receipt_rejects_replay():
    private, verifier = materials()
    verified = verify_sda_release_authorization(
        assertion(private),
        verifier=verifier,
        now=NOW,
    )
    patch, receipt = consume_sda_release_authorization(
        {},
        verified,
        candidate(),
        now=NOW,
    )

    assert receipt.authorization_id == verified.authorization_id
    assert "targeting" in receipt.claims_boundary.lower()
    assert verified.authorization_id in patch[SDA_RELEASE_CONSUMPTIONS_KEY]

    registry = dict(patch)
    with pytest.raises(PrimeSentinelAuthorizationError, match="already consumed"):
        consume_sda_release_authorization(
            registry,
            verified,
            candidate(),
            now=NOW,
        )


def test_expiry_future_issue_and_revoked_key_fail_closed():
    private, verifier = materials()

    expired = assertion(
        private,
        issued_at=NOW - timedelta(minutes=3),
        expires_at=NOW - timedelta(seconds=1),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="expired"):
        verify_sda_release_authorization(expired, verifier=verifier, now=NOW)

    future = assertion(
        private,
        issued_at=NOW + timedelta(seconds=31),
        expires_at=NOW + timedelta(minutes=2),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="future"):
        verify_sda_release_authorization(future, verifier=verifier, now=NOW)

    revoked = PrimeSentinelVerifier(
        public_keys_b64url={
            KEY_ID: b64url(private.public_key().public_bytes_raw())
        },
        revoked_key_ids={KEY_ID},
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="revoked"):
        verify_sda_release_authorization(
            assertion(private),
            verifier=revoked,
            now=NOW,
        )


def test_use_time_expiry_closes_verification_execution_gap():
    private, verifier = materials()
    signed = assertion(
        private,
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(seconds=5),
    )
    verified = verify_sda_release_authorization(
        signed,
        verifier=verifier,
        now=NOW,
    )

    with pytest.raises(
        PrimeSentinelAuthorizationError,
        match="expired before use",
    ):
        consume_sda_release_authorization(
            {},
            verified,
            candidate(),
            now=NOW + timedelta(seconds=6),
        )


def test_assertion_requires_short_lifetime_identified_human_and_sorted_tags():
    private, _verifier = materials()
    with pytest.raises(ValidationError, match="5 minutes"):
        assertion(
            private,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=6),
        )

    with pytest.raises(ValidationError):
        SdaReleaseAuthorizationAssertion(
            key_id=KEY_ID,
            authorization_id="SDA-RELEASE-AUTH-002",
            hypothesis_set_digest=HYP_DIGEST,
            payload_digest=PAYLOAD_DIGEST,
            policy_revision_digest=POLICY_DIGEST,
            destination="INTERNAL:OVERWATCH",
            releasability_tags=["SYNTHETIC", "INTERNAL"],
            human_approval_id="",
            human_approver="",
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=1),
            nonce="release-nonce-0000002",
            signature_b64url="x",
        )


def test_pure_dict_consumption_documentation_does_not_claim_cross_process_atomicity():
    private, verifier = materials()
    verified = verify_sda_release_authorization(
        assertion(private),
        verifier=verifier,
        now=NOW,
    )
    _patch, receipt = consume_sda_release_authorization(
        {},
        verified,
        candidate(),
        now=NOW,
    )
    assert "software verification/consumption" in receipt.claims_boundary
