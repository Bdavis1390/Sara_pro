from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_RESULTS = {
    "INDEPENDENT_CUSTODY_REPRODUCTION_PASSED",
    "INDEPENDENT_CUSTODY_REPRODUCTION_PASSED_WITH_NOTES",
    "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED",
}

REQUIRED_ANCHOR_CHECKS = {
    "implementation_commit_and_tree_match",
    "publication_commit_and_tree_match",
    "preservation_commit_and_tree_match",
    "historical_white_page_blob_exists",
    "primary_frozen_ref_matches",
    "mirror_frozen_ref_matches",
    "portable_bundle_hash_matches",
}

REQUIRED_CLAIMS_CHECKS = {
    "internal_proof_not_promoted_to_external_certification",
    "workflow_signature_not_promoted_to_personal_signature",
    "rfc3161_request_not_promoted_to_external_timestamp",
    "technical_evidence_not_promoted_to_patent_priority",
    "limitations_clearly_stated",
}


def fail(message: str) -> None:
    raise SystemExit(f"independent review receipt: FAIL: {message}")


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate_review_receipt.py RECEIPT.json")

    path = Path(sys.argv[1])
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "WS-QCRYPTO-INDEPENDENT-REVIEW-RECEIPT-V1":
        fail("unsupported schema")

    result = receipt.get("result")
    if result not in ALLOWED_RESULTS:
        fail("receipt is incomplete or result is unsupported")

    for field in (
        "reviewer_identity",
        "reviewer_organization",
        "reviewer_contact_or_public_profile",
        "review_date_utc",
        "repository_revision_reviewed",
    ):
        if not nonempty(receipt.get(field)):
            fail(f"missing attributable reviewer field: {field}")

    environment = receipt.get("review_environment")
    if not isinstance(environment, dict):
        fail("review_environment must be an object")
    for field in ("operating_system", "git_version", "cosign_version", "openssl_version"):
        if not nonempty(environment.get(field)):
            fail(f"missing review environment field: {field}")

    custody = receipt.get("custody_object")
    if not isinstance(custody, dict):
        fail("custody_object must be an object")
    if custody.get("expected_sha256") != "844a88add18a081eea8722ac69de13575fbb7db1d26d52e47b6d8cf13590f201":
        fail("unexpected custody-object reference hash")
    if not nonempty(custody.get("observed_sha256")):
        fail("missing observed custody-object hash")
    if custody.get("hash_match") is not True and result != "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED":
        fail("successful result requires custody-object hash match")

    sigstore = receipt.get("sigstore_attestation")
    if not isinstance(sigstore, dict):
        fail("sigstore_attestation must be an object")
    for field in ("artifact_zip_observed_sha256", "bundle_observed_sha256"):
        if not nonempty(sigstore.get(field)):
            fail(f"missing Sigstore observation: {field}")
    if sigstore.get("cosign_verification_passed") is not True and result != "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED":
        fail("successful result requires Cosign verification")

    anchors = receipt.get("anchor_checks")
    if not isinstance(anchors, dict) or set(anchors) != REQUIRED_ANCHOR_CHECKS:
        fail("anchor check set is incomplete or unexpected")
    claims = receipt.get("claims_review")
    if not isinstance(claims, dict) or set(claims) != REQUIRED_CLAIMS_CHECKS:
        fail("claims-review set is incomplete or unexpected")

    if result != "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED":
        if not all(value is True for value in anchors.values()):
            fail("successful result requires every anchor check to pass")
        if not all(value is True for value in claims.values()):
            fail("successful result requires every claims-boundary check to pass")

    discrepancies = receipt.get("discrepancies")
    if not isinstance(discrepancies, list):
        fail("discrepancies must be a list")
    if result == "INDEPENDENT_CUSTODY_REPRODUCTION_PASSED" and discrepancies:
        fail("clean PASS cannot contain discrepancies")
    if result == "INDEPENDENT_CUSTODY_REPRODUCTION_PASSED_WITH_NOTES" and not discrepancies:
        fail("PASS_WITH_NOTES requires at least one recorded discrepancy/note")
    if result == "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED" and not discrepancies:
        fail("FAILED requires at least one recorded discrepancy")

    print(
        json.dumps(
            {
                "schema": "WS-QCRYPTO-INDEPENDENT-REVIEW-RECEIPT-VALIDATION-V1",
                "status": "PASS",
                "receipt_result": result,
                "reviewer_identity": receipt["reviewer_identity"],
                "repository_revision_reviewed": receipt["repository_revision_reviewed"],
                "scope": "CUSTODY_REPRODUCTION_ONLY",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
