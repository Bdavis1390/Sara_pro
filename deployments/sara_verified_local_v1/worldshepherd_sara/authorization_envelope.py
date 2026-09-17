from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_AUTHORIZATION_LIFETIME = timedelta(minutes=15)


class AuthorizationDisposition(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENIED = "DENIED"


class AuthorizationEnvelope(BaseModel):
    """Purpose-bound authority issued outside the model's own reasoning context."""

    model_config = ConfigDict(extra="forbid")

    authorization_id: str = Field(min_length=1, max_length=128)
    principal: str = Field(min_length=1, max_length=256)
    workflow_id: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    resource: str = Field(min_length=1, max_length=1024)
    purpose: str = Field(min_length=1, max_length=1024)
    scopes: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime
    maximum_delegation_depth: int = Field(default=0, ge=0, le=32)
    delegation_depth: int = Field(default=0, ge=0, le=32)
    external_egress: bool = False
    credential_use: bool = False

    @model_validator(mode="after")
    def validate_window_and_delegation(self) -> "AuthorizationEnvelope":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_AUTHORIZATION_LIFETIME:
            raise ValueError("authorization lifetime exceeds 15 minutes")
        if self.delegation_depth > self.maximum_delegation_depth:
            raise ValueError("delegation depth exceeds authorization ceiling")
        return self


class AuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    resource: str = Field(min_length=1, max_length=1024)
    purpose: str = Field(min_length=1, max_length=1024)
    required_scopes: list[str] = Field(default_factory=list)
    destination: str | None = Field(default=None, max_length=2048)
    external_egress: bool = False
    credential_use: bool = False
    requested_delegation_depth: int = Field(default=0, ge=0, le=32)


def evaluate_authorization(
    envelope: AuthorizationEnvelope | None,
    request: AuthorizationRequest,
    *,
    now: datetime | None = None,
) -> tuple[AuthorizationDisposition, list[str]]:
    """Fail closed unless the issued authority exactly covers the requested effect."""

    if envelope is None:
        return AuthorizationDisposition.DENIED, ["no authorization envelope supplied"]

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= envelope.expires_at.astimezone(timezone.utc):
        return AuthorizationDisposition.DENIED, ["authorization envelope is expired"]
    if current < envelope.issued_at.astimezone(timezone.utc):
        return AuthorizationDisposition.DENIED, ["authorization envelope is not yet valid"]

    reasons: list[str] = []
    if request.workflow_id != envelope.workflow_id:
        reasons.append("workflow is outside authorization scope")
    if request.action != envelope.action:
        reasons.append("action is outside authorization scope")
    if request.resource != envelope.resource:
        reasons.append("resource is outside authorization scope")
    if request.purpose != envelope.purpose:
        reasons.append("purpose is outside authorization scope")

    missing_scopes = sorted(set(request.required_scopes) - set(envelope.scopes))
    if missing_scopes:
        reasons.append(f"required scopes are not authorized: {', '.join(missing_scopes)}")

    if request.destination is not None and request.destination not in envelope.destinations:
        reasons.append("destination is outside authorization scope")
    if request.external_egress and not envelope.external_egress:
        reasons.append("external egress is not authorized")
    if request.credential_use and not envelope.credential_use:
        reasons.append("credential use is not authorized")
    if request.requested_delegation_depth > envelope.maximum_delegation_depth:
        reasons.append("requested delegation depth exceeds authorization ceiling")

    if reasons:
        return AuthorizationDisposition.DENIED, reasons
    return AuthorizationDisposition.AUTHORIZED, ["purpose-bound authorization covers requested action"]
