from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)


SDA_WORKLOAD_IDENTITY_SCHEMA = "WS-SDA-WORKLOAD-IDENTITY-V1"
SDA_WORKLOAD_IDENTITY_DOMAIN = b"WS-SDA-WORKLOAD-IDENTITY-V1\x00"
SDA_WORKLOAD_AUDIENCE = "ws-sda-ingest"
MAX_WORKLOAD_ASSERTION_LIFETIME = timedelta(minutes=5)
MAX_WORKLOAD_FUTURE_SKEW = timedelta(seconds=30)


class SdaWorkloadIdentityAssertion(BaseModel):
    """Short-lived signed workload identity for an SDA source adapter.

    This is a Worldshepherd software identity assertion. It is not a SPIFFE SVID,
    X.509 certificate, mTLS session, DoD credential, or external IAM attestation.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_WORKLOAD_IDENTITY_SCHEMA] = SDA_WORKLOAD_IDENTITY_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    workload_id: str = Field(pattern=r"^spiffe://worldshepherd\.internal/sda/[A-Za-z0-9._/-]{1,180}$")
    audience: Literal[SDA_WORKLOAD_AUDIENCE] = SDA_WORKLOAD_AUDIENCE
    source_id: str = Field(min_length=1, max_length=128)
    adapter_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "SdaWorkloadIdentityAssertion":
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        issued = self.issued_at.astimezone(timezone.utc)
        expires = self.expires_at.astimezone(timezone.utc)
        if expires <= issued:
            raise ValueError("expires_at must be after issued_at")
        if expires - issued > MAX_WORKLOAD_ASSERTION_LIFETIME:
            raise ValueError("SDA workload assertion lifetime exceeds 5 minutes")
        return self


class VerifiedSdaWorkloadIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workload_id: str
    source_id: str
    adapter_id: str
    adapter_version: str
    audience: str
    key_id: str
    key_fingerprint_sha256: str
    issued_at: datetime
    expires_at: datetime
    nonce: str


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sda_workload_identity_message(
    assertion: SdaWorkloadIdentityAssertion,
) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "workload_id": assertion.workload_id,
        "audience": assertion.audience,
        "source_id": assertion.source_id,
        "adapter_id": assertion.adapter_id,
        "adapter_version": assertion.adapter_version,
        "issued_at": _utc_iso(assertion.issued_at),
        "expires_at": _utc_iso(assertion.expires_at),
        "nonce": assertion.nonce,
    }
    return SDA_WORKLOAD_IDENTITY_DOMAIN + json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_sda_workload_identity(
    assertion: SdaWorkloadIdentityAssertion,
    *,
    verifier: PrimeSentinelVerifier,
    now: datetime | None = None,
) -> VerifiedSdaWorkloadIdentity:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued = assertion.issued_at.astimezone(timezone.utc)
    expires = assertion.expires_at.astimezone(timezone.utc)

    if issued > current + MAX_WORKLOAD_FUTURE_SKEW:
        raise PrimeSentinelAuthorizationError(
            "SDA workload assertion is issued too far in the future"
        )
    if current >= expires:
        raise PrimeSentinelAuthorizationError("SDA workload assertion is expired")

    signature = verifier.verify_detached_signature(
        key_id=assertion.key_id,
        message=canonical_sda_workload_identity_message(assertion),
        signature_b64url=assertion.signature_b64url,
    )

    return VerifiedSdaWorkloadIdentity(
        workload_id=assertion.workload_id,
        source_id=assertion.source_id,
        adapter_id=assertion.adapter_id,
        adapter_version=assertion.adapter_version,
        audience=assertion.audience,
        key_id=assertion.key_id,
        key_fingerprint_sha256=signature.key_fingerprint_sha256,
        issued_at=issued,
        expires_at=expires,
        nonce=assertion.nonce,
    )


def assert_workload_identity_bound_to_adapter(
    identity: VerifiedSdaWorkloadIdentity,
    *,
    source_id: str,
    adapter_id: str,
    adapter_version: str,
    now: datetime | None = None,
) -> None:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= identity.expires_at.astimezone(timezone.utc):
        raise PrimeSentinelAuthorizationError(
            "verified SDA workload identity has expired"
        )
    if identity.audience != SDA_WORKLOAD_AUDIENCE:
        raise PrimeSentinelAuthorizationError("SDA workload audience mismatch")
    if identity.source_id != source_id:
        raise PrimeSentinelAuthorizationError("SDA workload source identity mismatch")
    if identity.adapter_id != adapter_id:
        raise PrimeSentinelAuthorizationError("SDA workload adapter identity mismatch")
    if identity.adapter_version != adapter_version:
        raise PrimeSentinelAuthorizationError("SDA workload adapter version mismatch")
