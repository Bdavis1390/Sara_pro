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
    "rfc3161_timestamp_not_promoted_beyond_time_custody",
    "technical_evidence_not_promoted_to_patent_priority",
    "limitations_clearly_stated",
}

EXPECTED_CUSTODY_SHA256 = "844a88add18a081eea8722ac69de13575fbb7db1d26d52e47b6d8cf13590f201"
EXPECTED_SIGSTORE_ARTIFACT_SHA256 = "a6addc6b513f09a41b627d48c2476317ab4a94c5269931056a93dad5350e9a8a"
EXPECTED_SIGSTORE_BUNDLE_SHA256 = "a8669a592f84bb3e67cc063b67be1bba811606291bf64febbf748d24669fd862"
EXPECTED_RFC3161_ARTIFACT_SHA256 = "e907ffb24eb21f04d4071e119bfa796ba4a1478235b58be707219383307d61bd"
EXPECTED_RFC3161_RESPONSE_SHA256 = "b6d2ecd32015932f7f472dd5f80f06123fc9f31aa005d509fa6c5c9e85be942a"
EXPECTED_FROZEN_BUNDLE_SHA256 = "3ac4b9d6a94c50dad951ed5c33446ccaaffc876b9d9ad398aefe2a6b7e472522"
EXPECTED_ROOT_FINGERPRINT = "552F7BDCF1A7AF9E6CE672017F4F12ABF77240C78E761AC203D1D9D20AC89988"


def fail(message: str) -> None:
    raise SystemExit(f"independent review receipt: FAIL: {message}")


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def successful(result: str) -> bool:
    return result != "INDEPENDENT_CUSTODY_REPRODUCTION_FAILED"


def require_observed_match(block: dict[str, object], expected_key: str, observed_key: str, label: str) -> None:
    expected = block.get(expected_key)
    observed = block.get(observed_key)
    if not nonempty(observed):
        fail(f"missing observed {label}")
    if observed != expected:
        fail(f"observed {label} does not match expected value")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate_review_receipt.py RECEIPT.json")

    path = Path(sys.argv[1])
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "WS-QCRYPTO-INDEPENDENT-REVIEW-RECEIPT-V2":
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
    if custody.get("expected_sha256") != EXPECTED_CUSTODY_SHA256:
        fail("unexpected custody-object reference hash")
    require_observed_match(custody, "expected_sha256", "observed_sha256", "custody-object hash")
    if custody.get("hash_match") is not True and successful(result):
        fail("successful result requires custody-object hash match")

    sigstore = receipt.get("sigstore_attestation")
    if not isinstance(sigstore, dict):
        fail("sigstore_attestation must be an object")
    if sigstore.get("artifact_zip_expected_sha256") != EXPECTED_SIGSTORE_ARTIFACT_SHA256:
        fail("unexpected Sigstore artifact reference hash")
    if sigstore.get("bundle_expected_sha256") != EXPECTED_SIGSTORE_BUNDLE_SHA256:
        fail("unexpected Sigstore bundle reference hash")
    require_observed_match(sigstore, "artifact_zip_expected_sha256", "artifact_zip_observed_sha256", "Sigstore artifact ZIP hash")
    require_observed_match(sigstore, "bundle_expected_sha256", "bundle_observed_sha256", "Sigstore bundle hash")
    if sigstore.get("cosign_verification_passed") is not True and successful(result):
        fail("successful result requires Cosign verification")

    timestamp = receipt.get("rfc3161_timestamp")
    if not isinstance(timestamp, dict):
        fail("rfc3161_timestamp must be an object")
    if timestamp.get("artifact_zip_expected_sha256") != EXPECTED_RFC3161_ARTIFACT_SHA256:
        fail("unexpected RFC3161 artifact reference hash")
    if timestamp.get("response_expected_sha256") != EXPECTED_RFC3161_RESPONSE_SHA256:
        fail("unexpected RFC3161 response reference hash")
    if timestamp.get("frozen_bundle_expected_sha256") != EXPECTED_FROZEN_BUNDLE_SHA256:
        fail("unexpected frozen-bundle reference hash")
    if timestamp.get("root_fingerprint_expected_sha256") != EXPECTED_ROOT_FINGERPRINT:
        fail("unexpected RFC3161 root fingerprint")
    require_observed_match(timestamp, "artifact_zip_expected_sha256", "artifact_zip_observed_sha256", "RFC3161 artifact ZIP hash")
    require_observed_match(timestamp, "response_expected_sha256", "response_observed_sha256", "RFC3161 response hash")
    for field in ("openssl_ts_verify_passed", "certificate_chain_verified", "root_fingerprint_verified"):
        if timestamp.get(field) is not True and successful(result):
            fail(f"successful result requires {field}=true")

    anchors = receipt.get("anchor_checks")
    if not isinstance(anchors, dict) or set(anchors) != REQUIRED_ANCHOR_CHECKS:
        fail("anchor check set is incomplete or unexpected")
    claims = receipt.get("claims_review")
    if not isinstance(claims, dict) or set(claims) != REQUIRED_CLAIMS_CHECKS:
        fail("claims-review set is incomplete or unexpected")

    if successful(result):
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
                "schema": "WS-QCRYPTO-INDEPENDENT-REVIEW-RECEIPT-VALIDATION-V2",
                "status": "PASS",
                "receipt_result": result,
                "reviewer_identity": receipt["reviewer_identity"],
                "repository_revision_reviewed": receipt["repository_revision_reviewed"],
                "scope": "CUSTODY_REPRODUCTION_ONLY",
                "rfc3161_verified": bool(timestamp.get("openssl_ts_verify_passed")),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
