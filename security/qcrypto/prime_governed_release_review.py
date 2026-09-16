"""Cross-boundary review binding for PRIME and governed QCRYPTO evidence.

This module deliberately does not authorize execution. It combines two independently
bounded evidence products:

* deployed PRIME SENTINEL ML-DSA-65 authorization/integration evidence; and
* QCRYPTO governed signing-readiness evidence that terminates at HUMAN_REVIEW_REQUIRED.

A successful result creates a deterministic review-package digest for a human
reviewer. It never converts PRIME's deployment-local ``ACTIVATION_ALLOWED`` state
into wallet authority, live-value authorization, transaction signing, or production
protocol approval.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any


BRIDGE_SCHEMA = "WS-QCRYPTO-PRIME-GOVERNED-RELEASE-REVIEW-V1"
PRIME_EVIDENCE_SCHEMA = "WS-PRIME-SENTINEL-TWO-CONTAINER-INTEGRATION-V3"
PRIME_ALGORITHM = "ML-DSA-65"
PRIME_SIGNATURE_CONTEXT = "WS-PRIME-SENTINEL-AUTHZ-V2"
GOVERNED_EVIDENCE_SCHEMA = "WS-QCRYPTO-GOVERNED-PQ-SIGNING-STATE-EVIDENCE-V1"
GOVERNED_TERMINAL_STATE = "HUMAN_REVIEW_REQUIRED"


@dataclass(frozen=True)
class PrimeGovernedReleaseReviewDecision:
    verdict: str
    ready_for_human_release_review: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    prime_evidence_sha256: str
    governed_evidence_sha256: str
    review_package_sha256: str | None
    prime_signing_algorithm: str | None
    prime_signature_context: str | None
    prime_activation_disposition: str | None
    prime_authorization_registry_status: str | None
    governed_terminal_state: str | None
    governed_selected_suite_id: str | None
    governed_pq_algorithm_id: str | None
    human_release_required: bool = True
    human_release_recorded: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False
    live_transaction_signed: bool = False
    production_protocol_integration: bool = False
    end_to_end_pq_security_established: bool = False
    claim_boundary: str = (
        "Cross-boundary evidence review package only. PRIME cryptographic activation and "
        "QCRYPTO readiness do not grant human approval, execution authority, wallet "
        "authority, live-value authorization, production protocol integration, FIPS 140 "
        "validation, PQ-secure transport, or end-to-end post-quantum security."
    )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["blockers"] = list(self.blockers)
        result["warnings"] = list(self.warnings)
        return result


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()


def _bool_is(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def _summary(governed_evidence: dict[str, Any]) -> dict[str, Any]:
    value = governed_evidence.get("summary")
    return value if isinstance(value, dict) else {}


def _complete_path(governed_evidence: dict[str, Any]) -> dict[str, Any]:
    value = governed_evidence.get("complete_path")
    return value if isinstance(value, dict) else {}


def assess_prime_governed_release_review(
    prime_evidence: dict[str, Any],
    governed_evidence: dict[str, Any],
) -> PrimeGovernedReleaseReviewDecision:
    """Create a deterministic human-review package only when both evidence lanes agree."""

    blockers: list[str] = []
    warnings: list[str] = []
    prime_digest = _canonical_json_digest(prime_evidence)
    governed_digest = _canonical_json_digest(governed_evidence)

    if prime_evidence.get("schema") != PRIME_EVIDENCE_SCHEMA:
        blockers.append("PRIME evidence schema is not the governed integration schema.")
    if prime_evidence.get("status") != "PASS":
        blockers.append("PRIME deployed integration evidence did not PASS.")
    if prime_evidence.get("signing_algorithm") != PRIME_ALGORITHM:
        blockers.append("PRIME signing algorithm is not ML-DSA-65.")
    if prime_evidence.get("signature_context") != PRIME_SIGNATURE_CONTEXT:
        blockers.append("PRIME ML-DSA-65 signature context does not match the governed context.")
    if not _bool_is(prime_evidence.get("post_quantum_signature_protection"), True):
        blockers.append("PRIME evidence does not establish its bounded ML-DSA-65 signature protection.")
    if not _bool_is(prime_evidence.get("same_request_retry_identical_before_restart"), True):
        blockers.append("PRIME same-request idempotence before restart was not established.")
    if not _bool_is(prime_evidence.get("same_request_retry_identical_after_restart"), True):
        blockers.append("PRIME same-request idempotence after restart was not established.")
    if prime_evidence.get("conflicting_request_rejected_http_status") != 409:
        blockers.append("PRIME conflicting-request rejection was not established.")
    if prime_evidence.get("assertion_replay_rejected_http_status") != 403:
        blockers.append("PRIME assertion replay rejection was not established.")
    if prime_evidence.get("activation_disposition") != "ACTIVATION_ALLOWED":
        blockers.append("PRIME bounded activation disposition is not ACTIVATION_ALLOWED.")
    if prime_evidence.get("authorization_registry_status") != "CONSUMED":
        blockers.append("PRIME authorization registry did not reach CONSUMED state.")
    if not _bool_is(prime_evidence.get("end_to_end_pq_security_established"), False):
        blockers.append("PRIME evidence improperly asserts end-to-end PQ security.")

    if governed_evidence.get("schema") != GOVERNED_EVIDENCE_SCHEMA:
        blockers.append("Governed QCRYPTO evidence schema is not recognized.")
    if governed_evidence.get("status") != "PASS":
        blockers.append("Governed QCRYPTO evidence did not PASS.")
    if governed_evidence.get("proof_scope") != "EPHEMERAL_ZERO_VALUE_PRE_APPROVAL_ONLY":
        blockers.append("Governed QCRYPTO evidence escaped its zero-value pre-approval scope.")

    summary = _summary(governed_evidence)
    complete = _complete_path(governed_evidence)
    if summary.get("terminal_state") != GOVERNED_TERMINAL_STATE:
        blockers.append("Governed QCRYPTO evidence did not terminate at HUMAN_REVIEW_REQUIRED.")
    if not _bool_is(summary.get("ready_for_human_review"), True):
        blockers.append("Governed QCRYPTO evidence is not ready for human review.")
    if not _bool_is(summary.get("human_approval_required"), True):
        blockers.append("Governed QCRYPTO evidence does not preserve mandatory human approval.")
    if not _bool_is(summary.get("human_approval_recorded"), False):
        blockers.append("Governed QCRYPTO evidence unexpectedly records human approval.")
    for field in (
        "execution_authority",
        "live_value_authorized",
        "live_transaction_signed",
        "production_protocol_integration",
        "end_to_end_pq_security_established",
    ):
        if not _bool_is(summary.get(field), False):
            blockers.append(f"Governed QCRYPTO evidence improperly asserts {field}.")

    selected_suite = complete.get("selected_suite_id")
    pq_algorithm = complete.get("pq_algorithm_id")
    if pq_algorithm != "ML-DSA":
        blockers.append("Governed QCRYPTO PQ algorithm family does not match PRIME ML-DSA-65.")
    if not isinstance(selected_suite, str) or "MLDSA" not in selected_suite:
        blockers.append("Governed selected suite does not bind an ML-DSA family suite.")
    if not isinstance(complete.get("negotiated_context_digest"), str):
        blockers.append("Governed evidence is missing its negotiated context digest.")
    if not isinstance(complete.get("negotiation_transcript_digest"), str):
        blockers.append("Governed evidence is missing its negotiation transcript digest.")
    if int(complete.get("verified_compatible_probe_count", 0) or 0) < 1:
        blockers.append("Governed evidence has no verified compatible PQ reference probe.")

    warnings.append(
        "PRIME ACTIVATION_ALLOWED is interpreted only as the bounded deployment-local "
        "activation result demonstrated by PRIME evidence; it is not live-value or "
        "transaction execution authority."
    )

    review_digest: str | None = None
    if not blockers:
        review_binding = {
            "schema": BRIDGE_SCHEMA,
            "prime_evidence_sha256": prime_digest,
            "governed_evidence_sha256": governed_digest,
            "prime_signing_algorithm": prime_evidence.get("signing_algorithm"),
            "prime_signature_context": prime_evidence.get("signature_context"),
            "prime_activation_disposition": prime_evidence.get("activation_disposition"),
            "prime_authorization_registry_status": prime_evidence.get("authorization_registry_status"),
            "governed_terminal_state": summary.get("terminal_state"),
            "governed_selected_suite_id": selected_suite,
            "governed_pq_algorithm_id": pq_algorithm,
            "governed_negotiated_context_digest": complete.get("negotiated_context_digest"),
            "governed_negotiation_transcript_digest": complete.get("negotiation_transcript_digest"),
            "human_release_required": True,
            "execution_authority": False,
            "live_value_authorized": False,
        }
        review_digest = _canonical_json_digest(review_binding)

    return PrimeGovernedReleaseReviewDecision(
        verdict=(
            "PRIME_GOVERNED_RELEASE_READY_FOR_HUMAN_REVIEW"
            if not blockers
            else "PRIME_GOVERNED_RELEASE_BLOCKED"
        ),
        ready_for_human_release_review=not blockers,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        prime_evidence_sha256=prime_digest,
        governed_evidence_sha256=governed_digest,
        review_package_sha256=review_digest,
        prime_signing_algorithm=prime_evidence.get("signing_algorithm"),
        prime_signature_context=prime_evidence.get("signature_context"),
        prime_activation_disposition=prime_evidence.get("activation_disposition"),
        prime_authorization_registry_status=prime_evidence.get("authorization_registry_status"),
        governed_terminal_state=summary.get("terminal_state"),
        governed_selected_suite_id=selected_suite if isinstance(selected_suite, str) else None,
        governed_pq_algorithm_id=pq_algorithm if isinstance(pq_algorithm, str) else None,
    )
