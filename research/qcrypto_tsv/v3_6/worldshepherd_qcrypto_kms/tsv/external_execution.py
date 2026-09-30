"""Validation of externally executed TSV control receipts.

This module validates provenance and expected fail-closed behavior from a hosted
software reproducer. It does not convert external execution into an SEC, legal,
market-data, cybersecurity, or operational-compliance determination.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

HEX64 = re.compile(r"^[0-9a-f]{64}$")
DOMAIN = b"WS-QCRYPTO-TSV-EXTERNAL-EXECUTION-BUNDLE-V1\x00"
EXPECTED_PASS_CHECKS = {
    "RELEASE_BINDING",
    "SOURCE_MANIFEST_BINDING",
    "EXEMPTION_WINDOW",
    "INITIAL_PUBLIC_NOTICE_30_CALENDAR_DAYS",
    "OPERATIONS_START_WINDOW",
    "SEC_INITIAL_NOTICE_1_BUSINESS_DAY",
    "ISSUER_WAIT_30_CALENDAR_DAYS",
    "AFFILIATE_VOLUME_THRESHOLD",
    "TRANSPARENCY_FEED_POSTURE",
    "TRANSACTION_REQUIRED_FIELDS",
    "TRANSACTION_PUBLICATION_10_MINUTES",
    "SIGNIFICANT_OPERATIONAL_EVENT_EVIDENCE",
}
EXPECTED_FAIL_CASES = {
    "EXEMPTION_EXPIRED": "EXEMPTION_WINDOW",
    "LATE_INITIAL_NOTICE": "INITIAL_PUBLIC_NOTICE_30_CALENDAR_DAYS",
    "OP_EVENT_SEC_NOTICE_MISSING": "SIGNIFICANT_OPERATIONAL_EVENT_EVIDENCE",
    "TRANSACTION_PUBLICATION_LATE": "TRANSACTION_PUBLICATION_10_MINUTES",
    "VOLUME_EXCEEDANCE": "AFFILIATE_VOLUME_THRESHOLD",
    "WRONG_RELEASE_BINDING": "RELEASE_BINDING",
}


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_ok(value: object) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


@dataclass(frozen=True)
class ExternalTsvExecutionValidation:
    decision: str
    errors: tuple[str, ...]
    bundle_sha256: str | None
    execution_target: str | None
    pass_receipt_sha256: str | None
    negative_case_count: int
    claims_label: str = "EXTERNAL_EXECUTION_PROVENANCE_VALIDATION_ONLY_NOT_SEC_OR_LEGAL_COMPLIANCE"

    def to_dict(self) -> dict:
        return asdict(self)


def validate_external_tsv_execution_bundle(
    bundle: Mapping[str, Any],
    *,
    expected_parent_release_sha256: str,
    expected_parent_source_manifest_sha256: str,
    require_verify_jwt: bool = True,
) -> ExternalTsvExecutionValidation:
    errors: list[str] = []
    if bundle.get("schema") != "WS-QCRYPTO-TSV-EXTERNAL-EXECUTION-BUNDLE-V1":
        errors.append("BAD_SCHEMA")

    claimed_bundle_hash = bundle.get("bundle_sha256")
    material = dict(bundle)
    material.pop("bundle_sha256", None)
    computed_bundle_hash = hashlib.sha256(DOMAIN + _canon(material)).hexdigest()
    if not _sha_ok(claimed_bundle_hash) or claimed_bundle_hash != computed_bundle_hash:
        errors.append("BUNDLE_HASH_MISMATCH")

    parent = bundle.get("parent_binding") or {}
    if parent.get("v3_3_release_sha256") != expected_parent_release_sha256:
        errors.append("PARENT_RELEASE_MISMATCH")
    if parent.get("v3_3_source_manifest_sha256") != expected_parent_source_manifest_sha256:
        errors.append("PARENT_SOURCE_MANIFEST_MISMATCH")

    target = bundle.get("execution_target") or {}
    if target.get("provider") != "Supabase Edge Functions":
        errors.append("UNEXPECTED_EXECUTION_PROVIDER")
    if not target.get("project_ref") or not target.get("function_slug"):
        errors.append("EXECUTION_TARGET_IDENTITY_INCOMPLETE")
    if int(target.get("function_version") or 0) < 1:
        errors.append("FUNCTION_VERSION_INVALID")
    if require_verify_jwt and target.get("verify_jwt") is not True:
        errors.append("JWT_VERIFICATION_NOT_ENABLED")
    if not _sha_ok(target.get("deployed_bundle_sha256")):
        errors.append("DEPLOYED_FUNCTION_HASH_INVALID")

    passed = bundle.get("pass_case") or {}
    if passed.get("http_status") != 200 or passed.get("decision") != "ALLOW":
        errors.append("PASS_CASE_NOT_ALLOW_200")
    if not _sha_ok(passed.get("receipt_sha256")):
        errors.append("PASS_RECEIPT_HASH_INVALID")
    checks = set(passed.get("passed_checks") or [])
    missing = sorted(EXPECTED_PASS_CHECKS - checks)
    if missing:
        errors.append("PASS_CASE_MISSING_CHECKS:" + ",".join(missing))

    fail_rows = bundle.get("fail_cases") or []
    if not isinstance(fail_rows, list):
        errors.append("FAIL_CASES_NOT_LIST")
        fail_rows = []
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in fail_rows:
        if not isinstance(row, Mapping):
            errors.append("FAIL_CASE_ROW_INVALID")
            continue
        name = str(row.get("name") or "")
        if not name or name in by_name:
            errors.append("FAIL_CASE_NAME_INVALID_OR_DUPLICATE")
            continue
        by_name[name] = row
        if row.get("http_status") != 200 or row.get("decision") != "DENY":
            errors.append(f"FAIL_CASE_NOT_DENY_200:{name}")
        if not _sha_ok(row.get("receipt_sha256")):
            errors.append(f"FAIL_CASE_RECEIPT_HASH_INVALID:{name}")
    for name, expected_check in EXPECTED_FAIL_CASES.items():
        row = by_name.get(name)
        if row is None:
            errors.append(f"MISSING_FAIL_CASE:{name}")
        elif row.get("expected_failed_check") != expected_check:
            errors.append(f"WRONG_FAILED_CHECK:{name}")

    if bundle.get("claims_label") != "EXTERNAL_SOFTWARE_EXECUTION_EVIDENCE_ONLY_NOT_SEC_OR_LEGAL_COMPLIANCE_DETERMINATION":
        errors.append("CLAIMS_LABEL_MISSING_OR_CHANGED")
    negatives = bundle.get("negative_claims") or {}
    required_false = (
        "licensed_market_feed_used",
        "live_trading_used",
        "real_value_moved",
        "sec_approval_established",
        "legal_compliance_established",
        "independent_third_party_certification",
    )
    for key in required_false:
        if negatives.get(key) is not False:
            errors.append(f"NEGATIVE_CLAIM_NOT_FALSE:{key}")

    execution_target = None
    if target.get("project_ref") and target.get("function_slug"):
        execution_target = f"Supabase:{target['project_ref']}:{target['function_slug']}:v{target.get('function_version')}"
    return ExternalTsvExecutionValidation(
        decision="ALLOW" if not errors else "DENY",
        errors=tuple(errors),
        bundle_sha256=claimed_bundle_hash if _sha_ok(claimed_bundle_hash) else None,
        execution_target=execution_target,
        pass_receipt_sha256=passed.get("receipt_sha256") if _sha_ok(passed.get("receipt_sha256")) else None,
        negative_case_count=len(fail_rows),
    )
