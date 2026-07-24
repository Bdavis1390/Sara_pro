from __future__ import annotations

import hmac
import os
from enum import StrEnum

from fastapi import Header, HTTPException, status


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
