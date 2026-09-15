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


class FrozenDict(dict):
    """JSON-compatible immutable dictionary used to seal evidence after validation."""

    @staticmethod
    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise TypeError("sealed evidence mapping is immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked
    __ior__ = _blocked


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


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return FrozenDict({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _detached_strict_json(value: Any) -> Any:
    """Validate, canonicalize and detach caller-owned JSON before sealing it."""

    bounded = validate_json_resource(value)
    try:
        encoded = _canonical_json(bounded)
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be strict finite JSON") from exc
    return json.loads(encoded)


class SealedAuditRecord(AuditRecord):
    """AuditRecord subtype whose payload and model fields cannot be mutated after emission."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    payload: FrozenDict

    @field_validator("payload", mode="before")
    @classmethod
    def seal_payload(cls, value: Any) -> FrozenDict:
        detached = _detached_strict_json(value)
        frozen = _deep_freeze(detached)
        if not isinstance(frozen, FrozenDict):
            raise ValueError("audit payload must be a JSON object")
        return frozen


class DomainEvidenceEnvelope(BaseModel):
    """Bounded, domain-neutral evidence envelope for ECHO ingestion.

    This contract deliberately does not import feature-branch domain models. A domain adapter
    supplies a JSON payload and the immutable source identifier/hash from its own evidence object.
    The bridge preserves that material and refuses any execution-bearing envelope.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    domain: str = Field(min_length=1, max_length=64)
    source_kind: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=128)
    source_sha256: str
    claim_state: str = Field(min_length=1, max_length=64)
    claims_boundary: str = Field(min_length=1, max_length=2048)
    payload: FrozenDict
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

    @field_validator("payload", mode="before")
    @classmethod
    def bounded_finite_payload(cls, value: Any) -> FrozenDict:
        detached = _detached_strict_json(value)
        frozen = _deep_freeze(detached)
        if not isinstance(frozen, FrozenDict):
            raise ValueError("payload must be a JSON object")
        return frozen

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
        self._assert_evidence_only()
        return self

    def _assert_evidence_only(self) -> None:
        # model_copy(update=...) does not run Pydantic validators. Re-check at every
        # emission/ingestion boundary instead of rewriting a potentially true value.
        if self.execution_attempted is not False:
            raise ValueError("ECHO domain-evidence bridge is evidence-only; execution_attempted must be false")

    def identity_document(self) -> dict[str, str]:
        return {
            "domain": self.domain,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
        }

    def semantic_payload(self) -> dict[str, Any]:
        self._assert_evidence_only()
        # Convert the sealed structure through strict canonical JSON to produce a new
        # detached object for every emission. No caller-owned nested reference is reused.
        detached_payload = json.loads(_canonical_json(self.payload))
        return {
            "schema": BRIDGE_SCHEMA,
            "domain": self.domain,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "claim_state": self.claim_state,
            "claims_boundary": self.claims_boundary,
            "payload": detached_payload,
            "parent_refs": list(self.parent_refs),
            "human_signoff": self.human_signoff,
            "execution_attempted": self.execution_attempted,
            "bridge_claims_boundary": CLAIMS_BOUNDARY,
        }

    def bridge_payload_sha256(self) -> str:
        return _sha256_prefixed(self.semantic_payload())

    def stable_event_id(self) -> str:
        digest = hashlib.sha256(_canonical_json(self.identity_document()).encode("utf-8")).hexdigest()[:32]
        return f"SARA-EVENT-EVID-{self.domain[:32]}-{digest}"

    def artifact_id(self) -> str:
        digest = hashlib.sha256(_canonical_json(self.identity_document()).encode("utf-8")).hexdigest()[:24]
        return f"ECHO-DOMAIN-{digest}"

    def to_audit_record(self) -> SealedAuditRecord:
        self._assert_evidence_only()
        payload = self.semantic_payload()
        payload["bridge_payload_sha256"] = _sha256_prefixed(payload)
        payload["_outbox_event_id"] = self.stable_event_id()
        payload["_delivery_semantics"] = "AT_LEAST_ONCE"
        return SealedAuditRecord.create(event=BRIDGE_EVENT, actor=BRIDGE_ACTOR, payload=payload)

    def to_artifact_evidence(self, *, locator: str) -> ArtifactEvidence:
        self._assert_evidence_only()
        data = (_canonical_json(self.semantic_payload()) + "\n").encode("utf-8")
        return artifact_from_bytes(
            artifact_id=self.artifact_id(),
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

    envelope._assert_evidence_only()
    record = envelope.to_audit_record()
    # Recompute the bridge digest immediately before handing the sealed record to
    # ECHO. This is redundant with object sealing by design and makes custody local.
    semantic = dict(record.payload)
    declared = semantic.pop("bridge_payload_sha256")
    semantic.pop("_outbox_event_id")
    semantic.pop("_delivery_semantics")
    if declared != _sha256_prefixed(semantic):
        raise ValueError("ECHO bridge payload digest mismatch before ingestion")
    return store.ingest(record)
