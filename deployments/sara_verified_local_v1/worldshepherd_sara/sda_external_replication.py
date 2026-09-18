from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


G10_ASSERTION_SCHEMA = "WS-SDA-G10-EXTERNAL-REPLICATION-ASSERTION-V1"
G10_REPORT_SCHEMA = "WS-SDA-G10-EXTERNAL-REPLICATION-REPORT-V1"
G10_SIGNATURE_DOMAIN = b"WS-SDA-G10-EXTERNAL-REPLICATION-ASSERTION-V1\x00"


class SdaExternalReplicationError(ValueError):
    pass


class SdaExternalReplicationAssertion(BaseModel):
    """Signed evaluator assertion for one exact WS-SDA replication attempt.

    Cryptographic verification proves possession of the stated evaluator key. It
    does not by itself prove the evaluator's legal identity, independence, or
    institutional authority; those require separate identity evidence.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[G10_ASSERTION_SCHEMA] = G10_ASSERTION_SCHEMA
    assertion_id: str = Field(min_length=1, max_length=160)
    evaluator_name: str = Field(min_length=1, max_length=256)
    evaluator_organization: str = Field(min_length=1, max_length=256)
    evaluator_identity_ref: str = Field(min_length=1, max_length=512)
    evaluator_key_id: str = Field(min_length=1, max_length=160)
    evaluator_public_key_fingerprint_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    g8_corpus_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    g9_protocol_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_bundle_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    candidate_bundle_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    g9_report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_evidence_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    environment_evidence_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    evaluator_controlled_challenge_ref: str = Field(min_length=1, max_length=512)
    environment_id: str = Field(min_length=1, max_length=256)
    worldshepherd_controlled_execution: bool

    execution_started_at: datetime
    execution_completed_at: datetime
    result: Literal["PASS", "FAIL", "DISCREPANCY"]
    observed_g9_claim_eligible: bool
    unresolved_discrepancies: list[str] = Field(default_factory=list, max_length=128)
    notes: str | None = Field(default=None, max_length=4096)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @field_validator("execution_started_at", "execution_completed_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("replication timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def time_and_result_are_consistent(self):
        if self.execution_completed_at <= self.execution_started_at:
            raise ValueError("replication completion must follow start")
        if self.result == "PASS" and self.unresolved_discrepancies:
            raise ValueError("PASS cannot carry unresolved discrepancies")
        if self.result != "PASS" and self.observed_g9_claim_eligible:
            raise ValueError("non-PASS replication cannot claim G9 eligibility")
        return self


class SdaExternalReplicationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[G10_REPORT_SCHEMA] = G10_REPORT_SCHEMA
    assertion_id: str
    cryptographic_signature_valid: bool
    evaluator_key_fingerprint_matches: bool
    exact_source_commit: bool
    exact_g8_corpus: bool
    exact_g9_protocol: bool
    non_worldshepherd_execution: bool
    evaluator_identity_verified: bool
    result_passed: bool
    g9_claim_reproduced: bool
    unresolved_discrepancy_count: int = Field(ge=0)
    g10_independent_replication_gate_passed: bool
    claims_boundary: str = (
        "A G10 gate pass means the signed assertion matched the exact source and "
        "frozen G8/G9 artifacts, ran outside a Worldshepherd-controlled execution "
        "environment, reproduced the bounded G9 result, had no unresolved "
        "discrepancies, and the evaluator identity was separately verified. It does "
        "not imply government accreditation, universal security, operational SDA "
        "performance, certification, or authorization for consequential action."
    )


def _decode_b64url(value: str) -> bytes:
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, binascii.Error, UnicodeEncodeError) as exc:
        raise SdaExternalReplicationError("invalid base64url value") from exc


def evaluator_public_key_fingerprint(public_key_b64url: str) -> str:
    raw = _decode_b64url(public_key_b64url)
    if len(raw) != 32:
        raise SdaExternalReplicationError("Ed25519 public key must be 32 bytes")
    return hashlib.sha256(raw).hexdigest()


def canonical_external_replication_message(
    assertion: SdaExternalReplicationAssertion,
) -> bytes:
    payload = assertion.model_dump(mode="json", exclude={"signature_b64url"})
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return G10_SIGNATURE_DOMAIN + encoded


def verify_external_replication(
    assertion: SdaExternalReplicationAssertion,
    *,
    evaluator_public_key_b64url: str,
    expected_source_commit: str,
    expected_g8_corpus_sha256: str,
    expected_g9_protocol_sha256: str,
    evaluator_identity_verified: bool,
) -> SdaExternalReplicationReport:
    raw_public_key = _decode_b64url(evaluator_public_key_b64url)
    if len(raw_public_key) != 32:
        raise SdaExternalReplicationError("Ed25519 public key must be 32 bytes")

    observed_fingerprint = hashlib.sha256(raw_public_key).hexdigest()
    fingerprint_matches = (
        observed_fingerprint == assertion.evaluator_public_key_fingerprint_sha256
    )
    if not fingerprint_matches:
        raise SdaExternalReplicationError(
            "evaluator public-key fingerprint does not match signed assertion"
        )

    try:
        Ed25519PublicKey.from_public_bytes(raw_public_key).verify(
            _decode_b64url(assertion.signature_b64url),
            canonical_external_replication_message(assertion),
        )
    except (ValueError, InvalidSignature) as exc:
        raise SdaExternalReplicationError(
            "external replication signature verification failed"
        ) from exc

    exact_source = assertion.source_commit == expected_source_commit
    exact_g8 = assertion.g8_corpus_sha256 == expected_g8_corpus_sha256
    exact_g9 = assertion.g9_protocol_sha256 == expected_g9_protocol_sha256
    non_ws = not assertion.worldshepherd_controlled_execution
    result_passed = assertion.result == "PASS"
    reproduced = result_passed and assertion.observed_g9_claim_eligible
    no_discrepancies = not assertion.unresolved_discrepancies

    gate = all(
        (
            exact_source,
            exact_g8,
            exact_g9,
            non_ws,
            evaluator_identity_verified,
            reproduced,
            no_discrepancies,
        )
    )

    return SdaExternalReplicationReport(
        assertion_id=assertion.assertion_id,
        cryptographic_signature_valid=True,
        evaluator_key_fingerprint_matches=True,
        exact_source_commit=exact_source,
        exact_g8_corpus=exact_g8,
        exact_g9_protocol=exact_g9,
        non_worldshepherd_execution=non_ws,
        evaluator_identity_verified=evaluator_identity_verified,
        result_passed=result_passed,
        g9_claim_reproduced=reproduced,
        unresolved_discrepancy_count=len(assertion.unresolved_discrepancies),
        g10_independent_replication_gate_passed=gate,
    )
