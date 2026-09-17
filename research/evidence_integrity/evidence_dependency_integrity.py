from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Iterable

class VersionCoverage(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MULTI_CADENCE = "MULTI_CADENCE"
    PROVISIONAL = "PROVISIONAL"
    JUDGMENT_DEPENDENT = "JUDGMENT_DEPENDENT"
    MUTABLE_METADATA = "MUTABLE_METADATA"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class SemanticSnapshot:
    resource_id: str
    native_version: str | None = None
    content: str | None = None
    annotation_release: str | None = None
    schema_version: str | None = None
    source_timestamp: str | None = None
    publication_state: str | None = None
    coverage: VersionCoverage = VersionCoverage.UNKNOWN
    extra_layers: tuple[tuple[str, str], ...] = ()

    @property
    def content_hash(self) -> str | None:
        if self.content is None:
            return None
        return sha256(self.content.encode("utf-8")).hexdigest()

    def semantic_fingerprint(self) -> str:
        payload = [
            self.resource_id,
            self.native_version or "",
            self.content_hash or "",
            self.annotation_release or "",
            self.schema_version or "",
            self.source_timestamp or "",
            self.publication_state or "",
            self.coverage.value,
        ]
        payload.extend(f"{k}={v}" for k, v in sorted(self.extra_layers))
        return sha256("\n".join(payload).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class DerivedClaim:
    claim_id: str
    depends_on_fingerprint: str
    claim_text: str
    domain: str

@dataclass(frozen=True)
class RevalidationResult:
    stale: bool
    reason: str
    current_fingerprint: str
    prior_fingerprint: str

def needs_semantic_snapshot(snapshot: SemanticSnapshot) -> bool:
    return snapshot.coverage in {
        VersionCoverage.PARTIAL,
        VersionCoverage.MULTI_CADENCE,
        VersionCoverage.PROVISIONAL,
        VersionCoverage.JUDGMENT_DEPENDENT,
        VersionCoverage.MUTABLE_METADATA,
        VersionCoverage.UNKNOWN,
    }

def validate_claim(snapshot: SemanticSnapshot, claim: DerivedClaim) -> RevalidationResult:
    current = snapshot.semantic_fingerprint()
    if current != claim.depends_on_fingerprint:
        return RevalidationResult(
            stale=True,
            reason="SEMANTIC_DEPENDENCY_CHANGED",
            current_fingerprint=current,
            prior_fingerprint=claim.depends_on_fingerprint,
        )
    if needs_semantic_snapshot(snapshot) and not any([
        snapshot.content_hash,
        snapshot.annotation_release,
        snapshot.schema_version,
        snapshot.source_timestamp,
        snapshot.publication_state,
        snapshot.extra_layers,
    ]):
        return RevalidationResult(
            stale=True,
            reason="NATIVE_VERSION_INSUFFICIENT_FOR_SEMANTIC_REPRODUCIBILITY",
            current_fingerprint=current,
            prior_fingerprint=claim.depends_on_fingerprint,
        )
    return RevalidationResult(
        stale=False,
        reason="DEPENDENCY_CURRENT",
        current_fingerprint=current,
        prior_fingerprint=claim.depends_on_fingerprint,
    )

def medical_dataset_skew(web_updated: str, file_updated: str) -> str:
    if web_updated > file_updated:
        return "BULK_FILE_MAY_LAG_WEB_SURFACE"
    if web_updated < file_updated:
        return "WEB_SURFACE_MAY_LAG_BULK_FILE"
    return "CADENCE_ALIGNED_AT_RECORDED_TIMESTAMPS"

def legal_publication_state(state: str) -> str:
    normalized = state.strip().lower()
    if "slip" in normalized or "provisional" in normalized:
        return "REVISION_SENSITIVE"
    if "bound" in normalized or "official report" in normalized:
        return "FINAL_PUBLICATION_STATE"
    return "PUBLICATION_STATE_UNKNOWN"

def intelligence_revalidation(
    source_changed: bool,
    assumption_changed: bool,
    indicator_triggered: bool,
) -> str:
    if source_changed or assumption_changed or indicator_triggered:
        return "JUDGMENT_REQUIRES_REASSESSMENT"
    return "NO_REASSESSMENT_TRIGGER_DETECTED"

def software_doc_state(
    documented_version: str | None,
    runtime_version: str | None,
) -> str:
    if not documented_version or not runtime_version:
        return "VERSION_BINDING_REQUIRED"
    if documented_version != runtime_version:
        return "DOC_RUNTIME_VERSION_MISMATCH"
    return "DOC_RUNTIME_VERSION_ALIGNED"
