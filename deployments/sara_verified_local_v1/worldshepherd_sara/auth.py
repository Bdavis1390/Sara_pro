from __future__ import annotations

import hmac
import os
from enum import StrEnum

from fastapi import Header, HTTPException, status


_PRIME_PRIVATE_ENV_NAMES = frozenset(
    {
        "PRIME_SENTINEL_PRIVATE_KEY",
        "PRIME_SENTINEL_PRIVATE_KEY_FILE",
        "PRIME_SENTINEL_SIGNING_KEY",
        "PRIME_SENTINEL_SIGNING_KEY_FILE",
        "PRIME_SENTINEL_ED25519_PRIVATE_KEY",
        "PRIME_SENTINEL_ED25519_PRIVATE_KEY_FILE",
        "PRIME_SENTINEL_SECRET_KEY",
        "PRIME_SENTINEL_SEED",
    }
)
_PRIME_PRIVATE_NAME_TOKENS = (
    "PRIVATE_KEY",
    "SIGNING_KEY",
    "SECRET_KEY",
)
_PRIVATE_KEY_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
)


def reject_prime_private_signing_material(
    environ: dict[str, str] | None = None,
) -> None:
    """Fail SARA startup if PRIME private signing material is presented.

    This is a runtime boundary, not a claim about external signer custody. SARA
    accepts PRIME public verification keys only.
    """
    values = os.environ if environ is None else environ
    for name, raw in values.items():
        if not isinstance(name, str) or not name.startswith("PRIME_SENTINEL_"):
            continue
        value = str(raw).strip()
        if not value:
            continue
        suspicious_name = (
            name in _PRIME_PRIVATE_ENV_NAMES
            or any(token in name for token in _PRIME_PRIVATE_NAME_TOKENS)
            or name.endswith("_SEED")
        )
        public_metadata_name = (
            name.endswith("_KEY_ID")
            or name.endswith("_KEY_IDS")
            or name.endswith("_KEY_FINGERPRINT")
            or name.endswith("_KEY_FINGERPRINT_SHA256")
            or name == "PRIME_SENTINEL_PUBLIC_KEYS_JSON"
            or name == "PRIME_SENTINEL_REVOKED_KEY_IDS"
        )
        if suspicious_name and not public_metadata_name:
            raise RuntimeError(
                "SARA must not receive PRIME SENTINEL private signing material"
            )
        if any(marker in value for marker in _PRIVATE_KEY_MARKERS):
            raise RuntimeError(
                "SARA detected PRIME SENTINEL private key material in runtime environment"
            )


class Role(StrEnum):
    RELAY = "relay"
    ADMIN = "admin"


def _required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    if len(value) < 24:
        raise RuntimeError(f"{name} must contain at least 24 characters")
    return value


def validate_runtime_secrets() -> None:
    reject_prime_private_signing_material()
    relay = _required_secret("SARA_RELAY_TOKEN")
    admin = _required_secret("SARA_ADMIN_TOKEN")
    if hmac.compare_digest(relay, admin):
        raise RuntimeError("Relay and admin tokens must be different")


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must use Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def resolve_role(authorization: str | None = Header(default=None)) -> Role:
    token = _extract_bearer(authorization)
    admin = _required_secret("SARA_ADMIN_TOKEN")
    relay = _required_secret("SARA_RELAY_TOKEN")
    if hmac.compare_digest(token, admin):
        return Role.ADMIN
    if hmac.compare_digest(token, relay):
        return Role.RELAY
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(role: Role) -> Role:
    if role is not Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return role
