from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .echo_event_store import EchoEventStore, EchoIngestResult
from .evidence_artifacts import ArtifactEvidence, ArtifactRole, artifact_from_bytes
from .limits import validate_json_resource
from .models import AuditRecord


BRIDGE_SCHEMA = "WS-ECHO-DOMAIN-EVIDENCE-BRIDGE-V1"
BRIDGE_ACTOR = "ECHO_SENTINEL_LINK"
BRIDGE_EVENT = "domain_evidence_captured"
CLAIMS_BOUNDARY = (
    "Evidence/provenance transport only; the bridge preserves the source claim boundary and "
    "does not validate domain capability, authorize execution, or elevate maturity."
)

_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_prefixed(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class DomainEvidenceEnvelope(BaseModel):
    """Bounded, domain-neutral evidence envelope for ECHO ingestion.

    This contract deliberately does not import feature-branch domain models. A domain adapter
    supplies a JSON payload and the immutable source identifier/hash from its own evidence object.
    The bridge preserves that material and refuses any execution-bearing envelope.
    """

    model_config = ConfigDict(frozen=True)

    domain: str = Field(min_length=1, max_length=64)
    source_kind: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=128)
    source_sha256: str
    claim_state: str = Field(min_length=1, max_length=64)
    claims_boundary: str = Field(min_length=1, max_length=2048)
    payload: dict[str, Any]
    parent_refs: tuple[str, ...] = ()
    human_signoff: bool = False
    execution_attempted: bool = False

    @field_validator("domain", "source_kind", "source_id")
    @classmethod
    def safe_tokens(cls, value: str) -> str:
        if not _TOKEN.fullmatch(value):
            raise ValueError("domain/source tokens must use only A-Z, a-z, 0-9, dot, underscore, colon, or dash")
        return value

    @field_validator("source_sha256")
    @classmethod
    def normalize_source_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("source_sha256 must be a 64-character lowercase SHA-256 digest")
        return value if value.startswith("sha256:") else f"sha256:{value}"

    @field_validator("payload")
    @classmethod
    def bounded_finite_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        bounded = validate_json_resource(value)
        try:
            _canonical_json(bounded)
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be strict finite JSON") from exc
        return bounded

    @field_validator("parent_refs")
    @classmethod
    def unique_parent_refs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("parent_refs must be unique")
        if any(not item or len(item) > 256 for item in value):
            raise ValueError("parent_refs must be 1-256 characters")
        return value

    @model_validator(mode="after")
    def evidence_only(self) -> "DomainEvidenceEnvelope":
        if self.execution_attempted:
            raise ValueError("ECHO domain-evidence bridge is evidence-only; execution_attempted must be false")
        return self

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "schema": BRIDGE_SCHEMA,
            "domain": self.domain,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "claim_state": self.claim_state,
            "claims_boundary": self.claims_boundary,
            "payload": self.payload,
            "parent_refs": list(self.parent_refs),
            "human_signoff": self.human_signoff,
            "execution_attempted": False,
            "bridge_claims_boundary": CLAIMS_BOUNDARY,
        }

    def bridge_payload_sha256(self) -> str:
        return _sha256_prefixed(self.semantic_payload())

    def stable_event_id(self) -> str:
        identity = {
            "domain": self.domain,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
        }
        digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()[:32]
        return f"SARA-EVENT-EVID-{self.domain[:32]}-{digest}"

    def to_audit_record(self) -> AuditRecord:
        payload = self.semantic_payload()
        payload.update(
            {
                "bridge_payload_sha256": self.bridge_payload_sha256(),
                "_outbox_event_id": self.stable_event_id(),
                "_delivery_semantics": "AT_LEAST_ONCE",
            }
        )
        return AuditRecord.create(event=BRIDGE_EVENT, actor=BRIDGE_ACTOR, payload=payload)

    def to_artifact_evidence(self, *, locator: str) -> ArtifactEvidence:
        data = (_canonical_json(self.semantic_payload()) + "\n").encode("utf-8")
        return artifact_from_bytes(
            artifact_id=f"ECHO-DOMAIN-{hashlib.sha256(self.source_id.encode('utf-8')).hexdigest()[:24]}",
            role=ArtifactRole.SOURCE,
            data=data,
            media_type="application/json",
            locator=locator,
        )


def ingest_domain_evidence(
    store: EchoEventStore,
    envelope: DomainEvidenceEnvelope,
) -> EchoIngestResult:
    """Persist one bounded evidence envelope using the existing ECHO event-store semantics."""

    return store.ingest(envelope.to_audit_record())
