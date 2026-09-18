from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID
from pydantic import BaseModel, ConfigDict, Field

from .prime_sentinel_authorization import PrimeSentinelAuthorizationError
from .sda_identity import VerifiedSdaWorkloadIdentity


class SdaTransportIdentity(BaseModel):
    """Verified properties of the TLS peer certificate seen by the SDA endpoint.

    Trust-chain validation is performed by the TLS stack before this object is
    accepted. This layer binds that authenticated transport credential to the
    separately PRIME-signed workload assertion.
    """

    model_config = ConfigDict(extra="forbid")

    certificate_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    san_uris: list[str] = Field(min_length=1, max_length=32)
    not_valid_before: datetime
    not_valid_after: datetime
    client_auth_eku: bool
    basic_constraints_ca: bool


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def inspect_tls_peer_certificate(peer_certificate_der: bytes) -> SdaTransportIdentity:
    if not isinstance(peer_certificate_der, bytes) or not peer_certificate_der:
        raise PrimeSentinelAuthorizationError("SDA TLS peer certificate is missing")

    try:
        certificate = x509.load_der_x509_certificate(peer_certificate_der)
    except ValueError as exc:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate is not valid DER X.509"
        ) from exc

    try:
        san = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        san_uris = list(san.get_values_for_type(x509.UniformResourceIdentifier))
    except x509.ExtensionNotFound as exc:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate lacks a URI subjectAltName"
        ) from exc

    try:
        eku = certificate.extensions.get_extension_for_oid(
            ExtensionOID.EXTENDED_KEY_USAGE
        ).value
        client_auth = ExtendedKeyUsageOID.CLIENT_AUTH in eku
    except x509.ExtensionNotFound:
        client_auth = False

    try:
        basic_constraints = certificate.extensions.get_extension_for_oid(
            ExtensionOID.BASIC_CONSTRAINTS
        ).value
        is_ca = bool(basic_constraints.ca)
    except x509.ExtensionNotFound:
        is_ca = False

    if not san_uris:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate has no URI subjectAltName values"
        )

    return SdaTransportIdentity(
        certificate_sha256="sha256:" + hashlib.sha256(peer_certificate_der).hexdigest(),
        san_uris=san_uris,
        not_valid_before=_utc(certificate.not_valid_before_utc),
        not_valid_after=_utc(certificate.not_valid_after_utc),
        client_auth_eku=client_auth,
        basic_constraints_ca=is_ca,
    )


def assert_transport_identity_bound_to_workload(
    transport: SdaTransportIdentity,
    workload: VerifiedSdaWorkloadIdentity,
    *,
    now: datetime | None = None,
) -> None:
    current = _utc(now or datetime.now(timezone.utc))

    if current < _utc(transport.not_valid_before):
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate is not yet valid"
        )
    if current >= _utc(transport.not_valid_after):
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate is expired"
        )
    if not transport.client_auth_eku:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate lacks clientAuth EKU"
        )
    if transport.basic_constraints_ca:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate must be an end-entity certificate"
        )
    if transport.certificate_sha256 != workload.transport_cert_sha256:
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate fingerprint does not match signed workload identity"
        )
    if workload.workload_id not in set(transport.san_uris):
        raise PrimeSentinelAuthorizationError(
            "SDA TLS peer certificate URI SAN does not match signed workload identity"
        )


def verify_tls_peer_for_workload(
    peer_certificate_der: bytes,
    workload: VerifiedSdaWorkloadIdentity,
    *,
    now: datetime | None = None,
) -> SdaTransportIdentity:
    transport = inspect_tls_peer_certificate(peer_certificate_der)
    assert_transport_identity_bound_to_workload(transport, workload, now=now)
    return transport
