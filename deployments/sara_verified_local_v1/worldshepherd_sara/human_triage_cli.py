from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .qualification import canonical_digest

TRIAGE_LEDGER_SCHEMA = "WS-VULNERABILITY-HUMAN-TRIAGE-LEDGER-V1"
VULNERABILITY_EVIDENCE_SCHEMA = "WS-VULNERABILITY-ADVISORY-EVIDENCE-V1"
EVIDENCE_STATUS = "INTERNAL_REVIEW_LEDGER_UNSIGNED"
REVIEW_INPUT_NONE = "NO_HUMAN_REVIEW_INPUT_SUPPLIED"
REVIEW_INPUT_SUPPLIED = "HUMAN_REVIEW_INPUT_RECORDED_UNSIGNED"

DECISION_PENDING = "PENDING_HUMAN_REVIEW"
DECISION_ACCEPTED_RISK = "ACCEPTED_RISK"
DECISION_PATCH_REQUIRED = "PATCH_REQUIRED"
DECISION_NOT_APPLICABLE = "NOT_APPLICABLE"
DECISION_DEFERRED = "DEFERRED"
DECISION_NO_ADVISORY_RECORDS = "NO_ADVISORY_RECORDS"

ALLOWED_DECISIONS = {
    DECISION_ACCEPTED_RISK,
    DECISION_PATCH_REQUIRED,
    DECISION_NOT_APPLICABLE,
    DECISION_DEFERRED,
}

CLAIMS_BOUNDARY = (
    "Human-review advisory triage ledger records internal review decisions, rationale, and evidence references only. "
    "It does not establish absence of vulnerabilities, advisory-feed completeness, vulnerability scan pass, remediation "
    "completion, exploitability analysis, secure-by-design status, license legal review, SLSA compliance, CMMC/NIST/DFARS "
    "conformity, FedRAMP authorization, ISO certification, SOC 2 attestation, supplier approval, partner validation, "
    "external reproduction, field performance, hardware performance, classified access, or operational authority."
)

NOT_CLAIMED = [
    "absence_of_vulnerabilities",
    "advisory_feed_completeness",
    "vulnerability_scan_pass",
    "remediation_completion",
    "exploitability_analysis",
    "secure_by_design_status",
    "license_legal_review",
    "slsa_compliance",
    "cmmc_conformity",
    "nist_800_171_implementation",
    "dfars_satisfaction",
    "fedramp_authorization",
    "iso_certification",
    "soc2_attestation",
    "supplier_approval",
    "partner_validation",
    "external_reproduction",
    "field_or_hardware_performance",
]

FORBIDDEN_CLAIM_TOKENS = (
    "no_vulnerabilities",
    "vulnerability_free",
    "scan_passed",
    "remediation_complete",
    "cmmc_certified",
    "nist_800_171_conformant",
    "dfars_satisfied",
    "slsa_compliant",
    "fedramp_authorized",
    "iso_certified",
    "soc2_attested",
    "supplier_approved",
    "partner_validated",
    "field_validated",
    "hardware_validated",
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _set_summary_digest(summary: dict[str, Any]) -> None:
    digest_input = dict(summary)
    digest_input.pop("summary_digest", None)
    summary["summary_digest"] = canonical_digest(digest_input)


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file missing for digest: {path}")
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required JSON file missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _optional_file_digest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise ValueError(f"optional input was supplied but does not exist: {path}")
    return {"path": str(path), "sha256": _sha256_file(path), "size_bytes": path.stat().st_size}


def _resolve_cli_path(path: Path, *, base_dir: Path, must_exist: bool, allow_directory: bool) -> Path:
    base = base_dir.resolve()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"CLI path must resolve under working directory: {path}") from exc
    if must_exist:
        if allow_directory and not resolved.is_dir():
            raise ValueError(f"expected directory input: {path}")
        if not allow_directory and not resolved.is_file():
            raise ValueError(f"expected file input: {path}")
    return resolved


def _resolve_optional_cli_file(path: Path | None, *, base_dir: Path) -> Path | None:
    if path is None:
        return None
    return _resolve_cli_path(path, base_dir=base_dir, must_exist=True, allow_directory=False)


def _assert_no_forbidden_claims(**values: dict[str, Any]) -> None:
    text = json.dumps(values, sort_keys=True).lower()
    for token in FORBIDDEN_CLAIM_TOKENS:
        if token in text:
            raise ValueError(f"prohibited security/compliance claim present: {token}")


def _validate_vulnerability_evidence(report: dict[str, Any], summary: dict[str, Any]) -> None:
    if report.get("schema") != VULNERABILITY_EVIDENCE_SCHEMA:
        raise ValueError("unexpected vulnerability advisory report schema")
    if summary.get("schema") != VULNERABILITY_EVIDENCE_SCHEMA:
        raise ValueError("unexpected vulnerability evidence summary schema")
    if report.get("commit_sha") and summary.get("commit_sha") and report["commit_sha"] != summary["commit_sha"]:
        raise ValueError("vulnerability report and summary commit_sha values do not match")
    if "does not establish" not in str(report.get("claims_boundary", "")):
        raise ValueError("vulnerability report missing claims boundary")
    if "does not establish" not in str(summary.get("claims_boundary", "")):
        raise ValueError("vulnerability summary missing claims boundary")


def _load_review_input(review_input: Path | None) -> list[dict[str, Any]]:
    if review_input is None:
        return []
    payload = _load_json(review_input)
    reviews = payload.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("review input must contain a reviews list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, review in enumerate(reviews, start=1):
        if not isinstance(review, dict):
            raise ValueError("review entries must be objects")
        advisory_id = str(review.get("advisory_id") or "").strip()
        if not advisory_id:
            raise ValueError(f"review {index} missing advisory_id")
        if advisory_id in seen:
            raise ValueError(f"duplicate review decision for advisory_id: {advisory_id}")
        seen.add(advisory_id)
        decision = str(review.get("decision") or "").strip().upper()
        if decision not in ALLOWED_DECISIONS:
            raise ValueError(f"review {advisory_id} decision must be one of {sorted(ALLOWED_DECISIONS)}")
        reviewer = str(review.get("reviewer") or "").strip()
        if not reviewer:
            raise ValueError(f"review {advisory_id} missing reviewer")
        rationale = str(review.get("rationale") or "").strip()
        if not rationale:
            raise ValueError(f"review {advisory_id} missing rationale")
        evidence_refs = review.get("evidence_refs", [])
        if evidence_refs is None:
            evidence_refs = []
        if not isinstance(evidence_refs, list) or not all(isinstance(item, str) and item.strip() for item in evidence_refs):
            raise ValueError(f"review {advisory_id} evidence_refs must be a list of non-empty strings")
        normalized.append(
            {
                "advisory_id": advisory_id,
                "decision": decision,
                "reviewer": reviewer,
                "rationale": rationale,
                "reviewed_utc": review.get("reviewed_utc"),
                "evidence_refs": [item.strip() for item in evidence_refs],
            }
        )
    return normalized


def _severity_sort_key(record: dict[str, Any]) -> tuple[int, str]:
    priority = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    return (priority.get(str(record.get("severity", "UNKNOWN")).upper(), 4), str(record.get("advisory_id", "")))


def build_human_triage_ledger(
    *,
    vulnerability_report: Path,
    vulnerability_summary: Path,
    review_input: Path | None,
    repository: str,
    commit_sha: str,
    operator: str,
    executed_utc: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build an unsigned internal human-review ledger from vulnerability advisory evidence."""
    if not commit_sha:
        raise ValueError("commit_sha is required")

    report = _load_json(vulnerability_report)
    summary_source = _load_json(vulnerability_summary)
    _validate_vulnerability_evidence(report, summary_source)

    source_commit = str(summary_source.get("commit_sha") or report.get("commit_sha") or "")
    if source_commit and source_commit != commit_sha:
        raise ValueError("triage ledger commit_sha must match vulnerability evidence commit_sha")

    advisory_triage = report.get("advisory_triage", {})
    source_records = advisory_triage.get("records", [])
    if not isinstance(source_records, list):
        raise ValueError("vulnerability advisory report records must be a list")

    source_ids_list: list[str] = []
    for source_record in source_records:
        if not isinstance(source_record, dict):
            raise ValueError("vulnerability advisory record entries must be objects")
        advisory_id = str(source_record.get("advisory_id") or "").strip()
        if not advisory_id:
            raise ValueError("vulnerability advisory record missing advisory_id")
        source_ids_list.append(advisory_id)
    duplicate_source_ids = sorted(
        {advisory_id for advisory_id in source_ids_list if source_ids_list.count(advisory_id) > 1}
    )
    if duplicate_source_ids:
        raise ValueError(f"duplicate advisory_id values in vulnerability evidence: {duplicate_source_ids}")

    reviews = _load_review_input(review_input)
    review_by_advisory = {review["advisory_id"]: review for review in reviews}
    source_ids = set(source_ids_list)
    unknown_review_ids = sorted(set(review_by_advisory) - source_ids)
    if unknown_review_ids:
        raise ValueError(f"review input references unknown advisory_id values: {unknown_review_ids}")

    generated_at = executed_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ledger_records: list[dict[str, Any]] = []
    for source_record in sorted(source_records, key=_severity_sort_key):
        advisory_id = str(source_record.get("advisory_id") or "").strip()
        matched = bool(source_record.get("matched_component_in_sbom"))
        source_status = str(source_record.get("triage_status") or "")
        review = review_by_advisory.get(advisory_id)
        if review:
            decision = review["decision"]
            reviewer = review["reviewer"]
            rationale = review["rationale"]
            reviewed_utc = review["reviewed_utc"]
            evidence_refs = review["evidence_refs"]
            decision_source = REVIEW_INPUT_SUPPLIED
        elif matched and source_status == "OPEN_TRIAGE_REQUIRED":
            decision = DECISION_PENDING
            reviewer = None
            rationale = "Matched advisory requires human review; no review input was supplied for this advisory."
            reviewed_utc = None
            evidence_refs = []
            decision_source = REVIEW_INPUT_NONE
        else:
            decision = DECISION_NOT_APPLICABLE
            reviewer = "system"
            rationale = "Advisory was not present in the current SBOM input or did not require review in source evidence."
            reviewed_utc = generated_at
            evidence_refs = []
            decision_source = "SYSTEM_DERIVED_FROM_VULNERABILITY_EVIDENCE"

        ledger_records.append(
            {
                "advisory_id": advisory_id,
                "component": source_record.get("component"),
                "severity": source_record.get("severity"),
                "source_triage_status": source_status,
                "matched_component_in_sbom": matched,
                "decision": decision,
                "decision_source": decision_source,
                "reviewer": reviewer,
                "rationale": rationale,
                "reviewed_utc": reviewed_utc,
                "evidence_refs": evidence_refs,
                "remediation_status": "NOT_RECORDED_BY_THIS_LEDGER",
            }
        )

    pending_count = sum(1 for record in ledger_records if record["decision"] == DECISION_PENDING)
    patch_required_count = sum(1 for record in ledger_records if record["decision"] == DECISION_PATCH_REQUIRED)
    accepted_risk_count = sum(1 for record in ledger_records if record["decision"] == DECISION_ACCEPTED_RISK)
    not_applicable_count = sum(1 for record in ledger_records if record["decision"] == DECISION_NOT_APPLICABLE)
    deferred_count = sum(1 for record in ledger_records if record["decision"] == DECISION_DEFERRED)
    human_review_required_count = sum(
        1
        for record in ledger_records
        if record["matched_component_in_sbom"] and record["source_triage_status"] == "OPEN_TRIAGE_REQUIRED"
    )

    if not ledger_records:
        overall_status = DECISION_NO_ADVISORY_RECORDS
    elif pending_count:
        overall_status = "HUMAN_REVIEW_PENDING"
    else:
        overall_status = "HUMAN_REVIEW_RECORDED_UNSIGNED"

    ledger: dict[str, Any] = {
        "schema": TRIAGE_LEDGER_SCHEMA,
        "generated_utc": generated_at,
        "repository": repository,
        "commit_sha": commit_sha,
        "operator": operator,
        "evidence_status": EVIDENCE_STATUS,
        "review_input_status": REVIEW_INPUT_SUPPLIED if review_input else REVIEW_INPUT_NONE,
        "source_vulnerability_evidence": {
            "vulnerability_report_path": str(vulnerability_report),
            "vulnerability_report_sha256": _sha256_file(vulnerability_report),
            "vulnerability_summary_path": str(vulnerability_summary),
            "vulnerability_summary_sha256": _sha256_file(vulnerability_summary),
            "source_advisory_record_count": len(source_records),
            "source_matched_advisory_count": summary_source.get("matched_advisory_count"),
            "source_advisory_input_status": summary_source.get("advisory_input_status"),
        },
        "review_summary": {
            "overall_status": overall_status,
            "ledger_record_count": len(ledger_records),
            "human_review_required_count": human_review_required_count,
            "pending_review_count": pending_count,
            "patch_required_count": patch_required_count,
            "accepted_risk_count": accepted_risk_count,
            "not_applicable_count": not_applicable_count,
            "deferred_count": deferred_count,
        },
        "records": ledger_records,
        "claims_boundary": CLAIMS_BOUNDARY,
        "not_claimed": NOT_CLAIMED,
    }

    summary: dict[str, Any] = {
        "schema": TRIAGE_LEDGER_SCHEMA,
        "generated_utc": generated_at,
        "repository": repository,
        "commit_sha": commit_sha,
        "operator": operator,
        "evidence_status": EVIDENCE_STATUS,
        "review_input_status": ledger["review_input_status"],
        "overall_status": overall_status,
        "ledger_record_count": len(ledger_records),
        "human_review_required_count": human_review_required_count,
        "pending_review_count": pending_count,
        "patch_required_count": patch_required_count,
        "accepted_risk_count": accepted_risk_count,
        "not_applicable_count": not_applicable_count,
        "deferred_count": deferred_count,
        "input_files": {
            "vulnerability_report": _optional_file_digest(vulnerability_report),
            "vulnerability_summary": _optional_file_digest(vulnerability_summary),
            "review_input": _optional_file_digest(review_input),
        },
        "claims_boundary": CLAIMS_BOUNDARY,
        "not_claimed": NOT_CLAIMED,
    }
    _set_summary_digest(summary)
    _assert_no_forbidden_claims(ledger=ledger, summary=summary)
    return ledger, summary


def write_human_triage_ledger(
    *,
    out_dir: Path,
    vulnerability_report: Path,
    vulnerability_summary: Path,
    review_input: Path | None,
    repository: str,
    commit_sha: str,
    operator: str,
    executed_utc: str | None = None,
) -> dict[str, Any]:
    ledger, summary = build_human_triage_ledger(
        vulnerability_report=vulnerability_report,
        vulnerability_summary=vulnerability_summary,
        review_input=review_input,
        repository=repository,
        commit_sha=commit_sha,
        operator=operator,
        executed_utc=executed_utc,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "human-triage-ledger.json"
    summary_path = out_dir / "human-triage-summary.json"
    _write_json(ledger_path, ledger)

    summary["human_triage_ledger_path"] = str(ledger_path)
    summary["human_triage_ledger_sha256"] = _sha256_file(ledger_path)
    _set_summary_digest(summary)
    _assert_no_forbidden_claims(summary=summary)
    _write_json(summary_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate unsigned internal SARA human-review advisory triage ledger evidence."
    )
    parser.add_argument("--vulnerability-report", type=Path, required=True)
    parser.add_argument("--vulnerability-summary", type=Path, required=True)
    parser.add_argument("--review-input", type=Path, default=None, help="Optional local human review input JSON.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for human triage ledger files.")
    parser.add_argument("--repository", default="", help="Repository full name.")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA for the CI run.")
    parser.add_argument("--operator", default="github-actions", help="Evidence operator.")
    parser.add_argument("--executed-utc", default=None, help="Optional fixed execution timestamp.")
    args = parser.parse_args(argv)

    working_dir = Path.cwd()
    vulnerability_report = _resolve_cli_path(
        args.vulnerability_report, base_dir=working_dir, must_exist=True, allow_directory=False
    )
    vulnerability_summary = _resolve_cli_path(
        args.vulnerability_summary, base_dir=working_dir, must_exist=True, allow_directory=False
    )
    review_input = _resolve_optional_cli_file(args.review_input, base_dir=working_dir)
    out_dir = _resolve_cli_path(args.out, base_dir=working_dir, must_exist=False, allow_directory=True)

    summary = write_human_triage_ledger(
        out_dir=out_dir,
        vulnerability_report=vulnerability_report,
        vulnerability_summary=vulnerability_summary,
        review_input=review_input,
        repository=args.repository,
        commit_sha=args.commit_sha,
        operator=args.operator,
        executed_utc=args.executed_utc,
    )
    print(_json_text(summary), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
