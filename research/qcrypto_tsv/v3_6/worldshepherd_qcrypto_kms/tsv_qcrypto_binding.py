"""Bind TSV authorization evidence to an exact QCRYPTO source/candidate lineage.

This module supplies integrity/provenance binding only. It does not make a legal
compliance determination and does not turn post-quantum execution evidence into
an SEC requirement.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from .source_integrity import build_source_manifest, verify_source_manifest
from .tsv.runtime import AuthorizationBundle


class TsvQcryptoBindingError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class TsvQcryptoBinding:
    tsv_decision_sha256: str
    tsv_evidence_head: str
    qcrypto_source_manifest_sha256: str
    parent_qcrypto_zip_sha256: str
    parent_tsv_zip_sha256: str
    external_pq_receipt_sha256: Optional[str]
    external_tsv_execution_bundle_sha256: Optional[str]
    external_tsv_adversarial_bundle_sha256: Optional[str]
    tsv_control_core_sha256: Optional[str]
    external_tsv_resilience_bundle_sha256: Optional[str]
    tsv_resilience_core_sha256: Optional[str]
    binding_sha256: str
    claims_label: str = "INTEGRITY_BINDING_ONLY_NOT_REGULATORY_APPROVAL"

    def to_dict(self) -> dict:
        return asdict(self)


def bind_tsv_authorization(
    authorization: AuthorizationBundle,
    *,
    package_root: str | Path,
    source_manifest: Mapping[str, Any],
    parent_qcrypto_zip_sha256: str,
    parent_tsv_zip_sha256: str,
    external_pq_receipt_sha256: Optional[str] = None,
    external_tsv_execution_bundle_sha256: Optional[str] = None,
    external_tsv_adversarial_bundle_sha256: Optional[str] = None,
    tsv_control_core_sha256: Optional[str] = None,
    external_tsv_resilience_bundle_sha256: Optional[str] = None,
    tsv_resilience_core_sha256: Optional[str] = None,
) -> TsvQcryptoBinding:
    report = verify_source_manifest(package_root, source_manifest)
    if not report["satisfied"]:
        raise TsvQcryptoBindingError("QCRYPTO source integrity verification failed")
    for name, value in {
        "tsv_decision_sha256": authorization.decision_sha256,
        "tsv_evidence_head": authorization.evidence_head,
        "parent_qcrypto_zip_sha256": parent_qcrypto_zip_sha256,
        "parent_tsv_zip_sha256": parent_tsv_zip_sha256,
    }.items():
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise TsvQcryptoBindingError(f"{name} must be lowercase SHA-256 hex")
    if external_pq_receipt_sha256 is not None and (len(external_pq_receipt_sha256) != 64 or any(c not in "0123456789abcdef" for c in external_pq_receipt_sha256)):
        raise TsvQcryptoBindingError("external_pq_receipt_sha256 must be lowercase SHA-256 hex")
    if external_tsv_execution_bundle_sha256 is not None and (len(external_tsv_execution_bundle_sha256) != 64 or any(c not in "0123456789abcdef" for c in external_tsv_execution_bundle_sha256)):
        raise TsvQcryptoBindingError("external_tsv_execution_bundle_sha256 must be lowercase SHA-256 hex")
    if external_tsv_adversarial_bundle_sha256 is not None and (len(external_tsv_adversarial_bundle_sha256) != 64 or any(c not in "0123456789abcdef" for c in external_tsv_adversarial_bundle_sha256)):
        raise TsvQcryptoBindingError("external_tsv_adversarial_bundle_sha256 must be lowercase SHA-256 hex")
    if tsv_control_core_sha256 is not None and (len(tsv_control_core_sha256) != 64 or any(c not in "0123456789abcdef" for c in tsv_control_core_sha256)):
        raise TsvQcryptoBindingError("tsv_control_core_sha256 must be lowercase SHA-256 hex")
    if external_tsv_resilience_bundle_sha256 is not None and (len(external_tsv_resilience_bundle_sha256) != 64 or any(c not in "0123456789abcdef" for c in external_tsv_resilience_bundle_sha256)):
        raise TsvQcryptoBindingError("external_tsv_resilience_bundle_sha256 must be lowercase SHA-256 hex")
    if tsv_resilience_core_sha256 is not None and (len(tsv_resilience_core_sha256) != 64 or any(c not in "0123456789abcdef" for c in tsv_resilience_core_sha256)):
        raise TsvQcryptoBindingError("tsv_resilience_core_sha256 must be lowercase SHA-256 hex")
    material = {
        "schema": "WS-QCRYPTO-TSV-BINDING-V1",
        "tsv_decision_sha256": authorization.decision_sha256,
        "tsv_evidence_head": authorization.evidence_head,
        "qcrypto_source_manifest_sha256": report["current_manifest_sha256"],
        "parent_qcrypto_zip_sha256": parent_qcrypto_zip_sha256,
        "parent_tsv_zip_sha256": parent_tsv_zip_sha256,
        "external_pq_receipt_sha256": external_pq_receipt_sha256,
        "external_tsv_execution_bundle_sha256": external_tsv_execution_bundle_sha256,
        "external_tsv_adversarial_bundle_sha256": external_tsv_adversarial_bundle_sha256,
        "tsv_control_core_sha256": tsv_control_core_sha256,
        "external_tsv_resilience_bundle_sha256": external_tsv_resilience_bundle_sha256,
        "tsv_resilience_core_sha256": tsv_resilience_core_sha256,
    }
    digest = hashlib.sha256(b"WS-QCRYPTO-TSV-BINDING-V1\x00" + _canon(material)).hexdigest()
    return TsvQcryptoBinding(
        tsv_decision_sha256=authorization.decision_sha256,
        tsv_evidence_head=authorization.evidence_head,
        qcrypto_source_manifest_sha256=report["current_manifest_sha256"],
        parent_qcrypto_zip_sha256=parent_qcrypto_zip_sha256,
        parent_tsv_zip_sha256=parent_tsv_zip_sha256,
        external_pq_receipt_sha256=external_pq_receipt_sha256,
        external_tsv_execution_bundle_sha256=external_tsv_execution_bundle_sha256,
        external_tsv_adversarial_bundle_sha256=external_tsv_adversarial_bundle_sha256,
        tsv_control_core_sha256=tsv_control_core_sha256,
        external_tsv_resilience_bundle_sha256=external_tsv_resilience_bundle_sha256,
        tsv_resilience_core_sha256=tsv_resilience_core_sha256,
        binding_sha256=digest,
    )
