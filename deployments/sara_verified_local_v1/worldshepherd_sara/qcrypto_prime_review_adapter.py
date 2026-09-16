from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from .qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA, qcrypto_outbox_events


PRIME_GOVERNED_REVIEW_SCHEMA = "WS-QCRYPTO-PRIME-GOVERNED-RELEASE-REVIEW-V1"
PRIME_GOVERNED_REVIEW_CLAIM_STATE = (
    "PRIME_AND_QCRYPTO_EVIDENCE_BOUND_FOR_HUMAN_REVIEW_ONLY"
)
PRIME_GOVERNED_REVIEW_SCOPE = "CROSS_BOUNDARY_REVIEW_PACKAGE_NO_EXECUTION_AUTHORITY"
PRIME_GOVERNED_REVIEW_VERDICT = "PRIME_GOVERNED_RELEASE_READY_FOR_HUMAN_REVIEW"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TRUE_FIELDS = (
    "execution_authority",
    "live_value_authorized",
    "live_transaction_signed",
    "production_protocol_integration",
    "end_to_end_pq_security_established",
)


class QCryptoPrimeReviewAdapterError(ValueError):
    pass


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QCryptoPrimeReviewAdapterError(f"{name} must be a JSON object")
    return value


def _require_hex64(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise QCryptoPrimeReviewAdapterError(
            f"{name} must be canonical lowercase 64-character SHA-256 text"
        )
    return value


def _require_false(mapping: dict[str, Any], field: str, *, source: str) -> None:
    if mapping.get(field) is not False:
        raise QCryptoPrimeReviewAdapterError(f"{source}.{field} must remain false")


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return sha256(encoded).hexdigest()


def _review_binding(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": PRIME_GOVERNED_REVIEW_SCHEMA,
        "prime_evidence_sha256": decision.get("prime_evidence_sha256"),
        "governed_evidence_sha256": decision.get("governed_evidence_sha256"),
        "prime_signing_algorithm": decision.get("prime_signing_algorithm"),
        "prime_signature_context": decision.get("prime_signature_context"),
        "prime_activation_disposition": decision.get("prime_activation_disposition"),
        "prime_authorization_registry_status": decision.get(
            "prime_authorization_registry_status"
        ),
        "governed_terminal_state": decision.get("governed_terminal_state"),
        "governed_selected_suite_id": decision.get("governed_selected_suite_id"),
        "governed_pq_algorithm_id": decision.get("governed_pq_algorithm_id"),
        "governed_negotiated_context_digest": decision.get(
            "governed_negotiated_context_digest"
        ),
        "governed_negotiation_transcript_digest": decision.get(
            "governed_negotiation_transcript_digest"
        ),
        "human_release_required": True,
        "execution_authority": False,
        "live_value_authorized": False,
    }


def prime_governed_review_projection(evidence: dict[str, Any]) -> dict[str, Any]:
    """Map one self-verifying PRIME/QCRYPTO warrant into the native audit schema.

    The projection is data-only. It does not grant approval or authority. The source
    evidence wrapper digest and the cross-boundary review-package digest are both
    independently reconstructed before qcrypto_audit_adapter is allowed to emit the
    four native SARA events.
    """

    record = _require_mapping(evidence, "review evidence")
    if record.get("schema") != PRIME_GOVERNED_REVIEW_SCHEMA:
        raise QCryptoPrimeReviewAdapterError("unsupported PRIME/QCRYPTO review schema")
    if record.get("status") != "PASS":
        raise QCryptoPrimeReviewAdapterError("PRIME/QCRYPTO review evidence did not PASS")
    if record.get("claim_state") != PRIME_GOVERNED_REVIEW_CLAIM_STATE:
        raise QCryptoPrimeReviewAdapterError("PRIME/QCRYPTO review claim state is not bounded")
    if record.get("proof_scope") != PRIME_GOVERNED_REVIEW_SCOPE:
        raise QCryptoPrimeReviewAdapterError("PRIME/QCRYPTO review proof scope is not bounded")

    supplied_evidence_digest = _require_hex64(
        record.get("evidence_sha256"), "evidence_sha256"
    )
    digest_source = dict(record)
    digest_source.pop("evidence_sha256", None)
    reconstructed_evidence_digest = _canonical_json_digest(digest_source)
    if reconstructed_evidence_digest != supplied_evidence_digest:
        raise QCryptoPrimeReviewAdapterError(
            "review evidence wrapper digest does not reconstruct"
        )

    decision = _require_mapping(record.get("decision"), "review decision")
    summary = _require_mapping(record.get("summary"), "review summary")
    source = _require_mapping(record.get("source_evidence"), "source evidence")

    if decision.get("verdict") != PRIME_GOVERNED_REVIEW_VERDICT:
        raise QCryptoPrimeReviewAdapterError("review decision did not reach the human-review verdict")
    if decision.get("ready_for_human_release_review") is not True:
        raise QCryptoPrimeReviewAdapterError("review decision is not ready for human release review")
    if decision.get("human_release_required") is not True:
        raise QCryptoPrimeReviewAdapterError("review decision must preserve mandatory human release review")
    if decision.get("human_release_recorded") is not False:
        raise QCryptoPrimeReviewAdapterError("review decision must not pre-record human release")

    for field in _FORBIDDEN_TRUE_FIELDS:
        _require_false(decision, field, source="decision")
        _require_false(summary, field, source="summary")

    if summary.get("ready_for_human_release_review") is not True:
        raise QCryptoPrimeReviewAdapterError("review summary is not ready for human release review")
    if summary.get("human_release_required") is not True:
        raise QCryptoPrimeReviewAdapterError("review summary must preserve human release requirement")
    if summary.get("human_release_recorded") is not False:
        raise QCryptoPrimeReviewAdapterError("review summary must not pre-record human release")
    if summary.get("prime_signing_algorithm") != "ML-DSA-65":
        raise QCryptoPrimeReviewAdapterError("review summary PRIME algorithm must be ML-DSA-65")
    if summary.get("prime_signature_context") != "WS-PRIME-SENTINEL-AUTHZ-V2":
        raise QCryptoPrimeReviewAdapterError("review summary PRIME signature context mismatch")
    if summary.get("prime_activation_disposition") != "ACTIVATION_ALLOWED":
        raise QCryptoPrimeReviewAdapterError("review summary PRIME activation evidence is incomplete")
    if summary.get("prime_authorization_registry_status") != "CONSUMED":
        raise QCryptoPrimeReviewAdapterError("review summary PRIME authorization was not consumed")
    if summary.get("governed_terminal_state") != "HUMAN_REVIEW_REQUIRED":
        raise QCryptoPrimeReviewAdapterError("governed terminal state must remain HUMAN_REVIEW_REQUIRED")
    if summary.get("governed_pq_algorithm_id") != "ML-DSA":
        raise QCryptoPrimeReviewAdapterError("governed PQ family must remain ML-DSA")

    consistency_fields = (
        "prime_signing_algorithm",
        "prime_signature_context",
        "prime_activation_disposition",
        "prime_authorization_registry_status",
        "governed_terminal_state",
        "governed_selected_suite_id",
        "governed_pq_algorithm_id",
    )
    for field in consistency_fields:
        if decision.get(field) != summary.get(field):
            raise QCryptoPrimeReviewAdapterError(
                f"decision and summary disagree on {field}"
            )

    review_digest = _require_hex64(
        summary.get("review_package_sha256"), "review_package_sha256"
    )
    if decision.get("review_package_sha256") != review_digest:
        raise QCryptoPrimeReviewAdapterError("decision and summary review-package digests disagree")

    prime_digest = _require_hex64(source.get("prime_evidence_sha256"), "prime_evidence_sha256")
    governed_digest = _require_hex64(
        source.get("governed_evidence_sha256"), "governed_evidence_sha256"
    )
    if decision.get("prime_evidence_sha256") != prime_digest:
        raise QCryptoPrimeReviewAdapterError("decision PRIME source-evidence digest mismatch")
    if decision.get("governed_evidence_sha256") != governed_digest:
        raise QCryptoPrimeReviewAdapterError("decision governed source-evidence digest mismatch")

    _require_hex64(
        decision.get("governed_negotiated_context_digest"),
        "governed_negotiated_context_digest",
    )
    _require_hex64(
        decision.get("governed_negotiation_transcript_digest"),
        "governed_negotiation_transcript_digest",
    )
    reconstructed_review_digest = _canonical_json_digest(_review_binding(decision))
    if reconstructed_review_digest != review_digest:
        raise QCryptoPrimeReviewAdapterError(
            "review-package digest does not reconstruct from the bounded decision"
        )

    asset_id = f"PRIME-QCRYPTO-REVIEW:{review_digest}"
    correlation_id = f"sha256:{review_digest}"
    return {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": asset_id,
        "echo_state": "CROSS_BOUNDARY_REVIEW_EVIDENCE_READY",
        "prime_state": "MLDSA65_AUTHORIZATION_EVIDENCE_CONSUMED",
        "sara_state": "HUMAN_RELEASE_REVIEW_REQUIRED",
        "overwatch_state": "REVIEW_PACKAGE_MONITOR_ONLY",
        "priority": "PRIME_GOVERNED_RELEASE_REVIEW",
        "human_approval_required": True,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": (
            "PRIME/QCRYPTO cross-boundary review warrant in native SARA audit custody only; "
            "human release review remains required and no migration execution, transaction "
            "authority, live-value authorization, Federal compliance, WS-CAE conformance, "
            "production protocol integration, or end-to-end PQ security is established."
        ),
        "correlation_id": correlation_id,
    }


def prime_governed_review_outbox_events(
    evidence: dict[str, Any],
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return the existing four native SARA QCRYPTO events for the review warrant."""

    projection = prime_governed_review_projection(evidence)
    return qcrypto_outbox_events(
        projection,
        actor=actor,
        audit_instance_id=audit_instance_id,
    )
