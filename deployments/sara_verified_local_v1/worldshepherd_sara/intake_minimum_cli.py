from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .qualification import canonical_digest

INTAKE_MINIMUM_SCHEMA = "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1"
EVIDENCE_STATUS = "INTERNAL_INTAKE_STANDARD_UNSIGNED"

REQUIRED_FIELDS = (
    "intake_id",
    "intake_type",
    "source_system",
    "source_locator",
    "source_retrieved_utc",
    "source_sha256",
    "evidence_status",
    "maturity_label",
    "human_review_status",
    "routing_status",
    "claims_boundary",
)

ALLOWED_REVIEW_STATUSES = {
    "PENDING_HUMAN_REVIEW",
    "HUMAN_REVIEW_NOT_REQUIRED",
    "REVIEWED_ACCEPTED_RISK",
    "REVIEWED_ACTION_REQUIRED",
    "REVIEWED_NOT_APPLICABLE",
    "DEFERRED",
}

ALLOWED_ROUTING_STATUSES = {
    "PENDING_ROUTE",
    "ROUTED_TO_PRE",
    "ROUTED_TO_TRIAGE",
    "ROUTED_TO_PARTNER_SCREENING",
    "ROUTED_TO_RELEASE_INDEX",
    "ROUTED_TO_BACKLOG",
    "NOT_MATERIAL",
}

RECOGNIZED_EVIDENCE_STATUSES = {
    "RAW_INTAKE_UNSIGNED",
    "EXTERNAL_SOURCE_REFERENCE_ONLY",
    "INTERNAL_CI_GENERATED_UNSIGNED",
    "INTERNAL_REVIEW_LEDGER_UNSIGNED",
    "INTERNAL_INTAKE_STANDARD_UNSIGNED",
    "SCREENING_PACKAGE_UNSIGNED",
    "SIMULATION",
    "SIMULATED_ONLY",
}

RECOGNIZED_MATURITY_LABELS = {
    "NOT_CURRENTLY_CLAIMED",
    "RAW_INTAKE",
    "SUPPORTED_BY_SOURCE",
    "PROVEN_INTERNALLY",
    "IMPLEMENTED_IN_SOFTWARE",
    "SIMULATED_ONLY",
    "REQUIRES_LAB_VALIDATION",
    "REQUIRES_PARTNER_VALIDATION",
    "REQUIRES_LEGAL_REVIEW",
    "REQUIRES_EXTERNAL_VALIDATION",
}

NON_CLAIM_MARKERS = ("does not", "do not", "not", "no", "without", "unless", "never")

PROHIBITED_ASSERTIONS = {
    "BAE_VALIDATED",
    "BAE_CERTIFIED",
    "BAE_APPROVED",
    "BAE_ADOPTED",
    "PARTNER_VALIDATED",
    "PARTNER_APPROVED",
    "PARTNER_ADOPTED",
    "SUPPLIER_APPROVED",
    "CMMC_CERTIFIED",
    "NIST_800_171_CONFORMANT",
    "DFARS_SATISFIED",
    "FEDRAMP_AUTHORIZED",
    "ISO_CERTIFIED",
    "SOC2_ATTESTED",
    "CLASSIFIED_ACCESS_GRANTED",
    "DOE_VALIDATED",
    "FIELD_VALIDATED",
    "HARDWARE_VALIDATED",
    "VULNERABILITY_REMEDIATED",
    "SECURE_BY_DESIGN_VALIDATED",
    "OPERATIONAL_AUTHORITY_GRANTED",
}

CLAIMS_BOUNDARY = (
    "Intake minimum standard ledger records intake governance and custody only. It does not establish "
    "source truth, partner validation, supplier approval, certification, CMMC/NIST/DFARS conformity, "
    "classified access, DOE validation, external reproduction, field performance, hardware performance, "
    "export-control clearance, software supply-chain completeness, absence of vulnerabilities, advisory-feed "
    "completeness, vulnerability scan pass, vulnerability remediation, human-review completion, exploitability "
    "analysis, license legal review, SLSA compliance, opportunity eligibility, award probability, or operational authority."
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"required JSON file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file missing for digest: {path}")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_digest(value: str, *, field: str) -> str:
    if not value:
        raise ValueError(f"{field} is required")
    raw = str(value).strip()
    if raw.startswith("sha256:"):
        raw = raw[len("sha256:") :]
    if len(raw) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in raw):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return "sha256:" + raw.lower()


def _normalized_words(text: str) -> str:
    normalized = str(text).lower().replace("-", " ").replace("/", " ")
    return " " + " ".join(normalized.split()) + " "


def _has_non_claim_language(text: str) -> bool:
    normalized = _normalized_words(text)
    return any(f" {marker} " in normalized for marker in NON_CLAIM_MARKERS)


def _require_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"intake {record.get('intake_id', '<unknown>')}: {field} is required")
    return value.strip()


def _require_utc_timestamp(record: dict[str, Any], field: str) -> str:
    value = _require_string(record, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"intake {record.get('intake_id', '<unknown>')}: {field} must be an ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(
            f"intake {record.get('intake_id', '<unknown>')}: {field} must be an ISO-8601 UTC timestamp"
        )
    return value


def _require_claims_boundary(record: dict[str, Any]) -> str:
    boundary = _require_string(record, "claims_boundary")
    if not _has_non_claim_language(boundary):
        raise ValueError(f"intake {record.get('intake_id')}: claims_boundary must contain explicit non-claim language")
    normalized_boundary = boundary.upper()
    for assertion in PROHIBITED_ASSERTIONS:
        if assertion in normalized_boundary:
            raise ValueError(f"intake {record.get('intake_id')}: prohibited assertion found in claims_boundary: {assertion}")
    return boundary


def _require_downstream_route(record: dict[str, Any]) -> list[dict[str, Any]]:
    downstream = record.get("downstream_evidence")
    route = record.get("downstream_route")
    if downstream is None:
        downstream = []
    if not isinstance(downstream, list):
        raise ValueError(f"intake {record.get('intake_id')}: downstream_evidence must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(downstream):
        if not isinstance(item, dict):
            raise ValueError(f"intake {record.get('intake_id')}: downstream_evidence[{index}] must be an object")
        artifact_name = item.get("artifact_name")
        artifact_digest = item.get("artifact_digest")
        relation = item.get("relation")
        if not isinstance(artifact_name, str) or not artifact_name.strip():
            raise ValueError(f"intake {record.get('intake_id')}: downstream_evidence[{index}].artifact_name is required")
        if not isinstance(relation, str) or not relation.strip():
            raise ValueError(f"intake {record.get('intake_id')}: downstream_evidence[{index}].relation is required")
        normalized.append(
            {
                "artifact_name": artifact_name.strip(),
                "relation": relation.strip(),
                "artifact_digest": _normalize_digest(artifact_digest, field=f"downstream_evidence[{index}].artifact_digest")
                if artifact_digest
                else None,
                "artifact_url": item.get("artifact_url") or None,
            }
        )
    if not normalized and not (isinstance(route, str) and route.strip()):
        raise ValueError(
            f"intake {record.get('intake_id')}: downstream_evidence or downstream_route is required for every intake"
        )
    return normalized


def _minimum_controls_for(record: dict[str, Any], downstream: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "source_custody": "PASS",
        "source_hash": "PASS",
        "claims_boundary": "PASS",
        "human_review_status": "PASS",
        "routing_status": "PASS",
        "downstream_route_or_evidence": "PASS" if downstream or record.get("downstream_route") else "FAIL",
        "false_claim_guard": "PASS",
    }


def normalize_intake_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("each intake must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"intake {record.get('intake_id', '<unknown>')}: missing required fields: {', '.join(missing)}")

    intake_id = _require_string(record, "intake_id")
    source_sha256 = _normalize_digest(_require_string(record, "source_sha256"), field="source_sha256")
    evidence_status = _require_string(record, "evidence_status")
    maturity_label = _require_string(record, "maturity_label")
    human_review_status = _require_string(record, "human_review_status")
    routing_status = _require_string(record, "routing_status")
    claims_boundary = _require_claims_boundary(record)
    downstream = _require_downstream_route(record)

    if evidence_status not in RECOGNIZED_EVIDENCE_STATUSES:
        raise ValueError(f"intake {intake_id}: unrecognized evidence_status {evidence_status!r}")
    if maturity_label not in RECOGNIZED_MATURITY_LABELS:
        raise ValueError(f"intake {intake_id}: unrecognized maturity_label {maturity_label!r}")
    if human_review_status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError(f"intake {intake_id}: unsupported human_review_status {human_review_status!r}")
    if routing_status not in ALLOWED_ROUTING_STATUSES:
        raise ValueError(f"intake {intake_id}: unsupported routing_status {routing_status!r}")

    review_rationale = record.get("review_rationale")
    if human_review_status.startswith("REVIEWED_") and not (isinstance(review_rationale, str) and review_rationale.strip()):
        raise ValueError(f"intake {intake_id}: reviewed intakes require review_rationale")

    normalized = {
        "intake_id": intake_id,
        "intake_type": _require_string(record, "intake_type"),
        "source_system": _require_string(record, "source_system"),
        "source_locator": _require_string(record, "source_locator"),
        "source_retrieved_utc": _require_utc_timestamp(record, "source_retrieved_utc"),
        "source_sha256": source_sha256,
        "evidence_status": evidence_status,
        "maturity_label": maturity_label,
        "human_review_status": human_review_status,
        "routing_status": routing_status,
        "downstream_route": record.get("downstream_route") or None,
        "downstream_evidence": downstream,
        "owner": record.get("owner") or None,
        "priority": record.get("priority") or "UNSPECIFIED",
        "reviewer": record.get("reviewer") or None,
        "review_rationale": review_rationale or None,
        "claims_boundary": claims_boundary,
        "minimum_controls": _minimum_controls_for(record, downstream),
    }
    normalized["record_digest"] = canonical_digest(normalized)
    return normalized


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        if "intakes" in payload:
            records = payload["intakes"]
        elif "records" in payload:
            records = payload["records"]
        else:
            records = [payload]
    else:
        raise ValueError("intake file must contain an object, an intakes list, or a records list")
    if not isinstance(records, list) or not records:
        raise ValueError("at least one intake record is required")
    return records


def build_intake_minimum_ledger(
    *,
    intake_file: Path,
    repository: str,
    commit_sha: str,
    operator: str,
    executed_utc: str | None = None,
) -> dict[str, Any]:
    payload = _load_json(intake_file)
    records = [normalize_intake_record(record) for record in _records_from_payload(payload)]
    record_ids = [record["intake_id"] for record in records]
    duplicate_ids = sorted({record_id for record_id in record_ids if record_ids.count(record_id) > 1})
    if duplicate_ids:
        raise ValueError(f"duplicate intake_id values: {', '.join(duplicate_ids)}")

    generated_at = executed_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    review_counts = {status: 0 for status in sorted(ALLOWED_REVIEW_STATUSES)}
    routing_counts = {status: 0 for status in sorted(ALLOWED_ROUTING_STATUSES)}
    for record in records:
        review_counts[record["human_review_status"]] += 1
        routing_counts[record["routing_status"]] += 1

    ledger: dict[str, Any] = {
        "schema": INTAKE_MINIMUM_SCHEMA,
        "generated_utc": generated_at,
        "repository": repository,
        "commit_sha": commit_sha,
        "operator": operator,
        "input_files": {
            "intake_file": {
                "path": str(intake_file),
                "sha256": _sha256_file(intake_file),
            }
        },
        "required_fields": list(REQUIRED_FIELDS),
        "records": records,
        "summary": {
            "intake_count": len(records),
            "review_counts": review_counts,
            "routing_counts": routing_counts,
            "pending_human_review_count": review_counts["PENDING_HUMAN_REVIEW"],
            "reviewed_action_required_count": review_counts["REVIEWED_ACTION_REQUIRED"],
            "not_material_count": routing_counts["NOT_MATERIAL"],
        },
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    ledger["ledger_digest"] = canonical_digest(ledger)
    return ledger


def build_summary(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": INTAKE_MINIMUM_SCHEMA,
        "generated_utc": ledger["generated_utc"],
        "repository": ledger["repository"],
        "commit_sha": ledger["commit_sha"],
        "operator": ledger["operator"],
        "evidence_status": EVIDENCE_STATUS,
        "intake_count": ledger["summary"]["intake_count"],
        "pending_human_review_count": ledger["summary"]["pending_human_review_count"],
        "reviewed_action_required_count": ledger["summary"]["reviewed_action_required_count"],
        "not_material_count": ledger["summary"]["not_material_count"],
        "review_counts": ledger["summary"]["review_counts"],
        "routing_counts": ledger["summary"]["routing_counts"],
        "intake_minimum_ledger_sha256": ledger["ledger_digest"],
        "input_files": ledger["input_files"],
        "claims_boundary": CLAIMS_BOUNDARY,
    }


def write_intake_minimum_evidence(ledger: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "intake-minimum-ledger.json"
    summary_path = out_dir / "intake-minimum-summary.json"
    _write_json(ledger_path, ledger)
    summary = build_summary(ledger)
    summary["intake_minimum_ledger_file_sha256"] = _sha256_file(ledger_path)
    _write_json(summary_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a minimum governance ledger for new Worldshepherd/SARA intakes.")
    parser.add_argument("--intake-file", type=Path, required=True, help="JSON file containing one intake object or an intakes list.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for intake-minimum-ledger.json and summary.")
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--operator", default=os.getenv("USER", "unknown"))
    parser.add_argument("--executed-utc", default=None)
    args = parser.parse_args(argv)

    ledger = build_intake_minimum_ledger(
        intake_file=args.intake_file,
        repository=args.repository,
        commit_sha=args.commit_sha,
        operator=args.operator,
        executed_utc=args.executed_utc,
    )
    summary = write_intake_minimum_evidence(ledger, args.out)
    print(_json_text(summary), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
