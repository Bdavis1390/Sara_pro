from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from worldshepherd_sara.sda_external_replication import (
    SdaExternalReplicationAssertion,
    SdaExternalReplicationError,
    canonical_external_replication_message,
    evaluator_public_key_fingerprint,
    verify_external_replication,
)


NOW = datetime(2026, 9, 18, 2, 30, tzinfo=timezone.utc)
SOURCE = "a" * 40
G8 = "sha256:" + "b" * 64
G9 = "sha256:" + "c" * 64


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def materials():
    private = Ed25519PrivateKey.generate()
    public = b64url(private.public_key().public_bytes_raw())
    return private, public


def signed_assertion(
    private: Ed25519PrivateKey,
    public: str,
    *,
    worldshepherd_controlled_execution: bool = False,
    result: str = "PASS",
    observed_g9_claim_eligible: bool = True,
    unresolved_discrepancies=None,
):
    unsigned = SdaExternalReplicationAssertion(
        assertion_id="G10-REPLICATION-FIXTURE-001",
        evaluator_name="Independent Evaluator Fixture",
        evaluator_organization="External Lab Fixture",
        evaluator_identity_ref="fixture://external-lab-identity",
        evaluator_key_id="EXT-EVAL-K1",
        evaluator_public_key_fingerprint_sha256=evaluator_public_key_fingerprint(public),
        source_commit=SOURCE,
        g8_corpus_sha256=G8,
        g9_protocol_sha256=G9,
        baseline_bundle_sha256="sha256:" + "d" * 64,
        candidate_bundle_sha256="sha256:" + "e" * 64,
        g9_report_sha256="sha256:" + "f" * 64,
        raw_evidence_sha256="sha256:" + "1" * 64,
        environment_evidence_sha256="sha256:" + "2" * 64,
        evaluator_controlled_challenge_ref="fixture://challenge-seed-001",
        environment_id="EXTERNAL-LAB-FIXTURE-ENV",
        worldshepherd_controlled_execution=worldshepherd_controlled_execution,
        execution_started_at=NOW,
        execution_completed_at=NOW + timedelta(minutes=5),
        result=result,
        observed_g9_claim_eligible=observed_g9_claim_eligible,
        unresolved_discrepancies=list(unresolved_discrepancies or []),
        notes="synthetic validator fixture only",
        signature_b64url="placeholder",
    )
    return unsigned.model_copy(
        update={
            "signature_b64url": b64url(
                private.sign(canonical_external_replication_message(unsigned))
            )
        }
    )


def verify(assertion, public, *, identity=True, source=SOURCE, g8=G8, g9=G9):
    return verify_external_replication(
        assertion,
        evaluator_public_key_b64url=public,
        expected_source_commit=source,
        expected_g8_corpus_sha256=g8,
        expected_g9_protocol_sha256=g9,
        evaluator_identity_verified=identity,
    )


def test_signed_external_pass_requires_exact_artifacts_independent_execution_and_verified_identity():
    private, public = materials()
    assertion = signed_assertion(private, public)
    report = verify(assertion, public)

    assert report.cryptographic_signature_valid is True
    assert report.evaluator_key_fingerprint_matches is True
    assert report.exact_source_commit is True
    assert report.exact_g8_corpus is True
    assert report.exact_g9_protocol is True
    assert report.non_worldshepherd_execution is True
    assert report.evaluator_identity_verified is True
    assert report.result_passed is True
    assert report.g9_claim_reproduced is True
    assert report.unresolved_discrepancy_count == 0
    assert report.g10_independent_replication_gate_passed is True


def test_cryptographic_signature_does_not_substitute_for_evaluator_identity_verification():
    private, public = materials()
    report = verify(signed_assertion(private, public), public, identity=False)

    assert report.cryptographic_signature_valid is True
    assert report.evaluator_identity_verified is False
    assert report.g10_independent_replication_gate_passed is False


def test_worldshepherd_controlled_execution_cannot_satisfy_independent_gate():
    private, public = materials()
    assertion = signed_assertion(
        private,
        public,
        worldshepherd_controlled_execution=True,
    )
    report = verify(assertion, public)

    assert report.non_worldshepherd_execution is False
    assert report.g10_independent_replication_gate_passed is False


def test_wrong_source_or_frozen_artifact_digest_blocks_gate_without_rewriting_assertion():
    private, public = materials()
    assertion = signed_assertion(private, public)

    wrong_source = verify(assertion, public, source="9" * 40)
    assert wrong_source.exact_source_commit is False
    assert wrong_source.g10_independent_replication_gate_passed is False

    wrong_g8 = verify(assertion, public, g8="sha256:" + "9" * 64)
    assert wrong_g8.exact_g8_corpus is False
    assert wrong_g8.g10_independent_replication_gate_passed is False

    wrong_g9 = verify(assertion, public, g9="sha256:" + "8" * 64)
    assert wrong_g9.exact_g9_protocol is False
    assert wrong_g9.g10_independent_replication_gate_passed is False


def test_signed_field_mutation_fails_signature_verification():
    private, public = materials()
    assertion = signed_assertion(private, public)
    tampered = assertion.model_copy(update={"environment_id": "TAMPERED"})

    with pytest.raises(SdaExternalReplicationError, match="signature verification failed"):
        verify(tampered, public)


def test_public_key_fingerprint_mismatch_fails_before_acceptance():
    private, public = materials()
    other_private, other_public = materials()
    assert other_private is not None
    assertion = signed_assertion(private, public)

    with pytest.raises(SdaExternalReplicationError, match="fingerprint"):
        verify(assertion, other_public)


def test_pass_cannot_hide_unresolved_discrepancy_and_nonpass_cannot_claim_g9_eligibility():
    private, public = materials()

    with pytest.raises(ValidationError, match="PASS cannot carry unresolved discrepancies"):
        signed_assertion(
            private,
            public,
            result="PASS",
            observed_g9_claim_eligible=True,
            unresolved_discrepancies=["fixture discrepancy"],
        )

    with pytest.raises(ValidationError, match="non-PASS replication cannot claim"):
        signed_assertion(
            private,
            public,
            result="FAIL",
            observed_g9_claim_eligible=True,
        )


def test_external_fail_is_cryptographically_reportable_but_never_gate_pass():
    private, public = materials()
    assertion = signed_assertion(
        private,
        public,
        result="FAIL",
        observed_g9_claim_eligible=False,
        unresolved_discrepancies=["candidate did not reproduce G9 threshold"],
    )
    report = verify(assertion, public)

    assert report.cryptographic_signature_valid is True
    assert report.result_passed is False
    assert report.g9_claim_reproduced is False
    assert report.unresolved_discrepancy_count == 1
    assert report.g10_independent_replication_gate_passed is False
