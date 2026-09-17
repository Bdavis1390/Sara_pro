from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PQ_AGILITY_POLICY_SCHEMA = "WS-PQ-CRYPTO-AGILITY-POLICY-V1"
PQ_SUITE_SCHEMA = "WS-PQ-SIGNATURE-SUITE-V1"
PQ_POLICY_ENV = "PRIME_SENTINEL_PQ_POLICY_JSON"
PQ_POLICY_REQUIRED_ENV = "POO_REQUIRE_PQ_AGILITY_POLICY"
DEFAULT_PQ_SUITE_ID = "WS-PQ-SUITE-MLDSA65-FIPS204-V1"
DEFAULT_PQ_ALGORITHM = "ML-DSA-65"
DEFAULT_PQ_STANDARD = "FIPS-204"
DEFAULT_PQ_CONTEXT = "WS-POO-PQ-COMMIT-V1"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})


class PqCryptoAgilityPolicyError(ValueError):
    pass


class PqSignatureSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[PQ_SUITE_SCHEMA] = PQ_SUITE_SCHEMA
    suite_id: str = Field(min_length=1, max_length=128)
    algorithm: str = Field(min_length=1, max_length=64)
    standard: str = Field(min_length=1, max_length=64)
    signature_context: str = Field(min_length=1, max_length=255)
    status: Literal["ACTIVE", "VERIFY_ONLY", "DISABLED"]


class PqCryptoAgilityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[PQ_AGILITY_POLICY_SCHEMA] = PQ_AGILITY_POLICY_SCHEMA
    policy_id: str = Field(min_length=1, max_length=128)
    epoch: int = Field(ge=1, le=2_147_483_647)
    active_suite_id: str = Field(min_length=1, max_length=128)
    accepted_suite_ids: list[str] = Field(min_length=1, max_length=16)
    suites: list[PqSignatureSuite] = Field(min_length=1, max_length=16)
    effective_at: datetime
    expires_at: datetime | None = None
    allow_algorithm_downgrade: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> "PqCryptoAgilityPolicy":
        if self.effective_at.tzinfo is None:
            raise ValueError("effective_at must be timezone-aware")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise ValueError("expires_at must be timezone-aware")
            if self.expires_at <= self.effective_at:
                raise ValueError("expires_at must be after effective_at")
        suite_ids = [suite.suite_id for suite in self.suites]
        if len(set(suite_ids)) != len(suite_ids):
            raise ValueError("suite IDs must be unique")
        if len(set(self.accepted_suite_ids)) != len(self.accepted_suite_ids):
            raise ValueError("accepted_suite_ids must be unique")
        if self.active_suite_id not in self.accepted_suite_ids:
            raise ValueError("active_suite_id must be accepted")
        by_id = {suite.suite_id: suite for suite in self.suites}
        unknown = sorted(set(self.accepted_suite_ids) - set(by_id))
        if unknown:
            raise ValueError("accepted suites missing definitions: " + ", ".join(unknown))
        active = by_id[self.active_suite_id]
        if active.status != "ACTIVE":
            raise ValueError("active suite must have ACTIVE status")
        for suite_id in self.accepted_suite_ids:
            if by_id[suite_id].status == "DISABLED":
                raise ValueError("disabled suite cannot remain accepted")
        return self

    def canonical_dict(self) -> dict:
        payload = self.model_dump(mode="json")
        payload["accepted_suite_ids"] = sorted(payload["accepted_suite_ids"])
        payload["suites"] = sorted(payload["suites"], key=lambda item: item["suite_id"])
        return payload

    @property
    def digest(self) -> str:
        raw = json.dumps(
            self.canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def suite(self, suite_id: str) -> PqSignatureSuite:
        for suite in self.suites:
            if suite.suite_id == suite_id:
                return suite
        raise PqCryptoAgilityPolicyError(f"unknown PQ suite: {suite_id}")

    def assert_issuance_allowed(self, suite_id: str, *, now: datetime | None = None) -> PqSignatureSuite:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        effective = self.effective_at.astimezone(timezone.utc)
        if current < effective:
            raise PqCryptoAgilityPolicyError("PQ policy epoch is not yet effective")
        if self.expires_at is not None and current >= self.expires_at.astimezone(timezone.utc):
            raise PqCryptoAgilityPolicyError("PQ policy epoch is expired")
        if suite_id != self.active_suite_id:
            raise PqCryptoAgilityPolicyError("PQ suite is not the active issuance suite")
        suite = self.suite(suite_id)
        if suite.status != "ACTIVE":
            raise PqCryptoAgilityPolicyError("PQ suite is not active for issuance")
        return suite

    def assert_verification_allowed(self, suite_id: str, *, now: datetime | None = None) -> PqSignatureSuite:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        effective = self.effective_at.astimezone(timezone.utc)
        if current < effective:
            raise PqCryptoAgilityPolicyError("PQ policy epoch is not yet effective")
        if self.expires_at is not None and current >= self.expires_at.astimezone(timezone.utc):
            raise PqCryptoAgilityPolicyError("PQ policy epoch is expired")
        if suite_id not in self.accepted_suite_ids:
            raise PqCryptoAgilityPolicyError("PQ suite is not accepted by this policy epoch")
        suite = self.suite(suite_id)
        if suite.status == "DISABLED":
            raise PqCryptoAgilityPolicyError("PQ suite is disabled")
        return suite


def pq_agility_policy_required() -> bool:
    raw = os.getenv(PQ_POLICY_REQUIRED_ENV, "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise RuntimeError(
        f"{PQ_POLICY_REQUIRED_ENV} must be one of: 0/1, false/true, no/yes, off/on"
    )


def load_pq_crypto_agility_policy_from_environment(*, required: bool | None = None) -> PqCryptoAgilityPolicy | None:
    must_exist = pq_agility_policy_required() if required is None else required
    raw = os.getenv(PQ_POLICY_ENV, "").strip()
    if not raw:
        if must_exist:
            raise RuntimeError(f"{PQ_POLICY_ENV} is required by policy")
        return None
    try:
        parsed = json.loads(raw)
        policy = PqCryptoAgilityPolicy.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{PQ_POLICY_ENV} is invalid: {exc}") from exc
    return policy


def default_mldsa65_policy(*, policy_id: str, epoch: int, effective_at: datetime) -> PqCryptoAgilityPolicy:
    return PqCryptoAgilityPolicy(
        policy_id=policy_id,
        epoch=epoch,
        active_suite_id=DEFAULT_PQ_SUITE_ID,
        accepted_suite_ids=[DEFAULT_PQ_SUITE_ID],
        suites=[
            PqSignatureSuite(
                suite_id=DEFAULT_PQ_SUITE_ID,
                algorithm=DEFAULT_PQ_ALGORITHM,
                standard=DEFAULT_PQ_STANDARD,
                signature_context=DEFAULT_PQ_CONTEXT,
                status="ACTIVE",
            )
        ],
        effective_at=effective_at,
        allow_algorithm_downgrade=False,
    )
