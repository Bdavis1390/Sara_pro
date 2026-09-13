"""Universal cryptographic-continuity manifest for digital-asset systems.

Metadata only. No keys, signatures, transactions, wallets, custody actions, or broadcast.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

SUBJECT_TYPES = {"CHAIN", "ASSET", "WALLET", "CUSTODIAN", "EXCHANGE", "BRIDGE", "ROLLUP", "ISSUER", "PROTOCOL", "OTHER"}


@dataclass(frozen=True)
class EvidenceRef:
    label: str
    url: str
    claim: str


@dataclass(frozen=True)
class DependencyRef:
    role: str
    subject: str
    critical: bool
    readiness_state: str


@dataclass(frozen=True)
class ContinuityManifest:
    subject_id: str
    subject_type: str
    version: str
    as_of: str
    authority_model: str
    implementation_maturity: str
    protocol_commitment_state: str
    pq_authorization_state: str
    consensus_pq_state: str
    crypto_agility_state: str
    recovery_state: str
    dependencies: tuple[DependencyRef, ...]
    evidence: tuple[EvidenceRef, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def canonical_bytes(manifest: ContinuityManifest) -> bytes:
    return json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_id(manifest: ContinuityManifest) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def validate(manifest: ContinuityManifest) -> tuple[str, ...]:
    issues: list[str] = []
    if not manifest.subject_id.strip():
        issues.append("subject_id must be non-empty")
    if manifest.subject_type not in SUBJECT_TYPES:
        issues.append("subject_type is not recognized")
    if not manifest.version.strip():
        issues.append("version must be non-empty")
    if len(manifest.as_of) != 10 or manifest.as_of[4] != "-" or manifest.as_of[7] != "-":
        issues.append("as_of must use YYYY-MM-DD")
    if not manifest.evidence:
        issues.append("at least one evidence reference is required")
    for index, item in enumerate(manifest.evidence):
        if not (item.label.strip() and item.claim.strip() and item.url.startswith("https://")):
            issues.append(f"evidence[{index}] must include label, HTTPS URL, and claim")
    for index, dep in enumerate(manifest.dependencies):
        if not dep.role.strip() or not dep.subject.strip() or not dep.readiness_state.strip():
            issues.append(f"dependencies[{index}] is incomplete")
    return tuple(issues)


def envelope(manifest: ContinuityManifest) -> dict:
    issues = validate(manifest)
    return {
        "spec": "WS-CAE-CONTINUITY-MANIFEST-1",
        "content_id": content_id(manifest),
        "valid": not issues,
        "issues": list(issues),
        "manifest": manifest.to_dict(),
    }
