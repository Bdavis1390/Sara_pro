from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from .qualification import canonical_digest


SDA_RELEASE_AUTH_SCHEMA = "WS-SDA-RELEASE-AUTHORIZATION-V1"
SDA_RELEASE_DOMAIN = b"WS-SDA-RELEASE-AUTHORIZATION-V1\x00"
SDA_RELEASE_ACTION = "DISSEMINATE_ANALYTIC_EVIDENCE"
SDA_RELEASE_CONSUMPTIONS_KEY = "SDA_RELEASE_AUTH_CONSUMPTIONS"
MAX_RELEASE_AUTH_LIFETIME = timedelta(minutes=5)
MAX_RELEASE_FUTURE_SKEW = timedelta(seconds=30)


class SdaReleaseAuthorizationAssertion(BaseModel):
    """PRIME-signed authorization for one bounded analytic evidence release.

    The signed assertion binds the exact payload and hypothesis-set digests, policy
    revision, destination, releasability tags, and identified human approval. It
    does not authorize actuation, targeting, weapon employment, or an operational
    track winner.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_RELEASE_AUTH_SCHEMA] = SDA_RELEASE_AUTH_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(pattern=r"^SDA-RELEASE-[A-Za-z0-9._:-]{1,128}$")
    action: Literal[SDA_RELEASE_ACTION] = SDA_RELEASE_ACTION
    hypothesis_set_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_revision_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    destination: str = Field(min_length=1, max_length=256)
    releasability_tags: list[str] = Field(min_length=1, max_length=64)
    human_approval_id: str = Field(min_length=1, max_length=128)
    human_approver: str = Field(min_length=1, max_length=128)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @field_validator("releasability_tags")
    @classmethod
    def tags_are_normalized_unique(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 128 for item in cleaned):
            raise ValueError("releasability tag must contain 1-128 characters")
        if cleaned != sorted(cleaned):
            raise ValueError("releasability_tags must be sorted")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("releasability_tags must be unique")
        return cleaned

    @model_validator(mode="after")
    def validate_lifetime(self):
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        issued = self.issued_at.astimezone(timezone.utc)
        expires = self.expires_at.astimezone(timezone.utc)
        if expires <= issued:
            raise ValueError("expires_at must be after issued_at")
        if expires - issued > MAX_RELEASE_AUTH_LIFETIME:
            raise ValueError("SDA release authorization lifetime exceeds 5 minutes")
        return self


class VerifiedSdaReleaseAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_id: str
    action: str
    hypothesis_set_digest: str
    payload_digest: str
    policy_revision_digest: str
    destination: str
    releasability_tags: list[str]
    human_approval_id: str
    human_approver: str
    key_id: str
    key_fingerprint_sha256: str
    issued_at: datetime
    expires_at: datetime
    nonce: str


class SdaReleaseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_set_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_revision_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    destination: str = Field(min_length=1, max_length=256)
    releasability_tags: list[str] = Field(min_length=1, max_length=64)

    @field_validator("releasability_tags")
    @classmethod
    def tags_are_sorted_unique(cls, value: list[str]) -> list[str]:
        if value != sorted(value) or len(value) != len(set(value)):
            raise ValueError("candidate releasability_tags must be sorted and unique")
        if any(not item for item in value):
            raise ValueError("candidate releasability tag cannot be empty")
        return value


class SdaReleaseReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal["WS-SDA-RELEASE-RECEIPT-V1"] = "WS-SDA-RELEASE-RECEIPT-V1"
    authorization_id: str
    payload_digest: str
    hypothesis_set_digest: str
    policy_revision_digest: str
    destination: str
    releasability_tags: list[str]
    human_approval_id: str
    human_approver: str
    signing_key_id: str
    signing_key_fingerprint_sha256: str
    consumed_at: datetime
    claims_boundary: str = (
        "Receipt proves software verification/consumption of one signed analytic "
        "evidence release authorization. It does not prove external delivery, "
        "recipient acceptance, operational track correctness, targeting, actuation, "
        "or government/customer authorization."
    )


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sda_release_message(
    assertion: SdaReleaseAuthorizationAssertion,
) -> bytes:
    document = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "action": assertion.action,
        "hypothesis_set_digest": assertion.hypothesis_set_digest,
        "payload_digest": assertion.payload_digest,
        "policy_revision_digest": assertion.policy_revision_digest,
        "destination": assertion.destination,
        "releasability_tags": list(assertion.releasability_tags),
        "human_approval_id": assertion.human_approval_id,
        "human_approver": assertion.human_approver,
        "issued_at": _utc_iso(assertion.issued_at),
        "expires_at": _utc_iso(assertion.expires_at),
        "nonce": assertion.nonce,
    }
    return SDA_RELEASE_DOMAIN + json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_sda_release_authorization(
    assertion: SdaReleaseAuthorizationAssertion,
    *,
    verifier: PrimeSentinelVerifier,
    now: datetime | None = None,
) -> VerifiedSdaReleaseAuthorization:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued = assertion.issued_at.astimezone(timezone.utc)
    expires = assertion.expires_at.astimezone(timezone.utc)

    if issued > current + MAX_RELEASE_FUTURE_SKEW:
        raise PrimeSentinelAuthorizationError(
            "SDA release authorization is issued too far in the future"
        )
    if current >= expires:
        raise PrimeSentinelAuthorizationError("SDA release authorization is expired")

    signature = verifier.verify_detached_signature(
        key_id=assertion.key_id,
        message=canonical_sda_release_message(assertion),
        signature_b64url=assertion.signature_b64url,
    )
    return VerifiedSdaReleaseAuthorization(
        authorization_id=assertion.authorization_id,
        action=assertion.action,
        hypothesis_set_digest=assertion.hypothesis_set_digest,
        payload_digest=assertion.payload_digest,
        policy_revision_digest=assertion.policy_revision_digest,
        destination=assertion.destination,
        releasability_tags=list(assertion.releasability_tags),
        human_approval_id=assertion.human_approval_id,
        human_approver=assertion.human_approver,
        key_id=assertion.key_id,
        key_fingerprint_sha256=signature.key_fingerprint_sha256,
        issued_at=issued,
        expires_at=expires,
        nonce=assertion.nonce,
    )


def assert_release_candidate_matches_authorization(
    authorization: VerifiedSdaReleaseAuthorization,
    candidate: SdaReleaseCandidate,
    *,
    now: datetime | None = None,
) -> None:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= authorization.expires_at.astimezone(timezone.utc):
        raise PrimeSentinelAuthorizationError(
            "verified SDA release authorization has expired before use"
        )
    if authorization.action != SDA_RELEASE_ACTION:
        raise PrimeSentinelAuthorizationError("SDA release action is not permitted")

    comparisons = {
        "hypothesis_set_digest": (
            authorization.hypothesis_set_digest,
            candidate.hypothesis_set_digest,
        ),
        "payload_digest": (authorization.payload_digest, candidate.payload_digest),
        "policy_revision_digest": (
            authorization.policy_revision_digest,
            candidate.policy_revision_digest,
        ),
        "destination": (authorization.destination, candidate.destination),
        "releasability_tags": (
            authorization.releasability_tags,
            candidate.releasability_tags,
        ),
    }
    mismatches = [
        field
        for field, (expected, observed) in comparisons.items()
        if expected != observed
    ]
    if mismatches:
        raise PrimeSentinelAuthorizationError(
            "SDA release candidate changed after authorization: "
            + ", ".join(sorted(mismatches))
        )


def _consumption_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(SDA_RELEASE_CONSUMPTIONS_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeSentinelAuthorizationError(
            "SDA release consumption registry is malformed"
        )
    return dict(raw)


def consume_sda_release_authorization(
    registry: dict[str, Any],
    authorization: VerifiedSdaReleaseAuthorization,
    candidate: SdaReleaseCandidate,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], SdaReleaseReceipt]:
    """Prepare a one-time consumption patch for an atomic SARA registry transaction.

    Exactly-once behavior is only as strong as the caller's transaction boundary.
    This function must be executed inside SARA's durable/serialized registry
    transaction; the pure dict call alone is not a cross-process lock.
    """

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    assert_release_candidate_matches_authorization(
        authorization,
        candidate,
        now=current,
    )

    consumptions = _consumption_map(registry)
    if authorization.authorization_id in consumptions:
        raise PrimeSentinelAuthorizationError(
            "SDA release authorization was already consumed"
        )

    receipt = SdaReleaseReceipt(
        authorization_id=authorization.authorization_id,
        payload_digest=candidate.payload_digest,
        hypothesis_set_digest=candidate.hypothesis_set_digest,
        policy_revision_digest=candidate.policy_revision_digest,
        destination=candidate.destination,
        releasability_tags=list(candidate.releasability_tags),
        human_approval_id=authorization.human_approval_id,
        human_approver=authorization.human_approver,
        signing_key_id=authorization.key_id,
        signing_key_fingerprint_sha256=authorization.key_fingerprint_sha256,
        consumed_at=current,
    )
    consumptions[authorization.authorization_id] = {
        "receipt": receipt.model_dump(mode="json"),
        "receipt_digest": canonical_digest(receipt),
        "nonce": authorization.nonce,
    }
    return {SDA_RELEASE_CONSUMPTIONS_KEY: consumptions}, receipt
