from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .qualification import canonical_digest

RELEASE_INDEX_SCHEMA = "WS-SARA-RELEASE-EVIDENCE-INDEX-V1"
INTAKE_MINIMUM_SCHEMA = "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1"
INTAKE_ARTIFACT_NAME = "intake-minimum-standard-evidence"
INTAKE_ARTIFACT_KEY = "intake_minimum_standard_evidence"

CLAIMS_BOUNDARY_APPENDIX = (
    " Intake evidence linkage does not establish source truth, opportunity eligibility, award probability, "
    "partner validation, supplier approval, certification, CMMC/NIST/DFARS conformity, classified access, "
    "DOE validation, external reproduction, field performance, hardware performance, export-control clearance, "
    "software supply-chain completeness, absence of vulnerabilities, advisory-feed completeness, vulnerability "
    "scan pass, vulnerability remediation, human-review completion, exploitability analysis, license legal review, "
    "SLSA compliance, or operational authority."
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required JSON file missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file missing for digest: {path}")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_digest(value: str | None, *, field: str, required: bool = True) -> str | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{field} is required")
        return None
    raw = str(value).strip()
    if raw.startswith("sha256:"):
        raw = raw[len("sha256:") :]
    if len(raw) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in raw):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return "sha256:" + raw.lower()


def _artifact_record(*, artifact_id: str | None, digest: str | None, url: str | None) -> dict[str, Any]:
    return {
        "name": INTAKE_ARTIFACT_NAME,
        "artifact_id": artifact_id or None,
        "artifact_digest": _normalize_digest(digest, field="intake-minimum-standard-evidence.digest"),
        "artifact_url": url or None,
    }


def _validate_release_index(index: dict[str, Any]) -> None:
    if index.get("schema") != RELEASE_INDEX_SCHEMA:
        raise ValueError("unexpected release index schema")
    if "artifacts" not in index or not isinstance(index["artifacts"], dict):
        raise ValueError("release index missing artifacts object")
    if "local_evidence" not in index or not isinstance(index["local_evidence"], dict):
        raise ValueError("release index missing local_evidence object")
    claims_boundary = index.get("claims_boundary", "")
    if not isinstance(claims_boundary, str) or "does not establish" not in claims_boundary:
        raise ValueError("release index missing claims boundary")


def _validate_intake_summary(summary: dict[str, Any]) -> None:
    if summary.get("schema") != INTAKE_MINIMUM_SCHEMA:
        raise ValueError("unexpected intake minimum summary schema")
    if summary.get("evidence_status") != "INTERNAL_INTAKE_STANDARD_UNSIGNED":
        raise ValueError("unexpected intake minimum evidence status")
    if summary.get("intake_count", 0) <= 0:
        raise ValueError("intake minimum summary must include at least one intake")
    for field in ("intake_minimum_ledger_sha256", "intake_minimum_ledger_file_sha256"):
        if not str(summary.get(field, "")).startswith("sha256:"):
            raise ValueError(f"intake minimum summary missing {field}")
    claims_boundary = summary.get("claims_boundary", "")
    if not isinstance(claims_boundary, str) or "does not establish" not in claims_boundary:
        raise ValueError("intake minimum summary missing claims boundary")


def _validate_intake_ledger(
    ledger: dict[str, Any],
    summary: dict[str, Any],
    ledger_path: Path,
) -> None:
    if ledger.get("schema") != INTAKE_MINIMUM_SCHEMA:
        raise ValueError("unexpected intake minimum ledger schema")
    records = ledger.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("intake minimum ledger must include at least one record")
    ledger_summary = ledger.get("summary")
    if not isinstance(ledger_summary, dict):
        raise ValueError("intake minimum ledger missing summary")

    recorded_ledger_digest = _normalize_digest(
        ledger.get("ledger_digest"),
        field="intake minimum ledger ledger_digest",
    )
    digest_input = dict(ledger)
    digest_input.pop("ledger_digest", None)
    actual_ledger_digest = canonical_digest(digest_input)
    if recorded_ledger_digest != actual_ledger_digest:
        raise ValueError(
            "intake minimum canonical ledger digest mismatch: "
            f"ledger records {recorded_ledger_digest}, content is {actual_ledger_digest}"
        )

    summary_ledger_digest = _normalize_digest(
        summary.get("intake_minimum_ledger_sha256"),
        field="intake minimum summary intake_minimum_ledger_sha256",
    )
    if summary_ledger_digest != actual_ledger_digest:
        raise ValueError("intake minimum summary canonical ledger digest mismatch")

    summary_file_digest = _normalize_digest(
        summary.get("intake_minimum_ledger_file_sha256"),
        field="intake minimum summary intake_minimum_ledger_file_sha256",
    )
    actual_file_digest = _sha256_file(ledger_path)
    if summary_file_digest != actual_file_digest:
        raise ValueError(
            "intake minimum ledger file digest mismatch: "
            f"summary records {summary_file_digest}, file is {actual_file_digest}"
        )

    if summary.get("intake_count") != len(records) or ledger_summary.get("intake_count") != len(records):
        raise ValueError("intake minimum intake_count does not match ledger records")
    for field in (
        "pending_human_review_count",
        "reviewed_action_required_count",
        "not_material_count",
        "review_counts",
        "routing_counts",
    ):
        if summary.get(field) != ledger_summary.get(field):
            raise ValueError(f"intake minimum summary {field} does not match ledger")

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("intake minimum ledger records must be objects")
        recorded_record_digest = _normalize_digest(
            record.get("record_digest"),
            field="intake minimum record record_digest",
        )
        record_input = dict(record)
        record_input.pop("record_digest", None)
        if recorded_record_digest != canonical_digest(record_input):
            raise ValueError(f"intake minimum record digest mismatch: {record.get('intake_id')}")


def link_intake_evidence(
    *,
    release_index_path: Path,
    intake_dir: Path,
    intake_artifact_id: str | None,
    intake_artifact_digest: str | None,
    intake_artifact_url: str | None,
) -> dict[str, Any]:
    """Add intake-minimum artifact custody to an existing release-index record."""
    index = _load_json(release_index_path)
    _validate_release_index(index)

    intake_root = Path(intake_dir)
    summary_path = intake_root / "intake-minimum-summary.json"
    ledger_path = intake_root / "intake-minimum-ledger.json"
    summary = _load_json(summary_path)
    ledger = _load_json(ledger_path)
    _validate_intake_summary(summary)
    _validate_intake_ledger(ledger, summary, ledger_path)

    index.pop("release_index_digest", None)
    index["artifacts"][INTAKE_ARTIFACT_KEY] = _artifact_record(
        artifact_id=intake_artifact_id,
        digest=intake_artifact_digest,
        url=intake_artifact_url,
    )
    index["local_evidence"].update(
        {
            "intake_minimum_summary_path": str(summary_path),
            "intake_minimum_summary_sha256": _sha256_file(summary_path),
            "intake_minimum_ledger_path": str(ledger_path),
            "intake_minimum_ledger_sha256": _sha256_file(ledger_path),
            "intake_minimum_ledger_digest": summary.get("intake_minimum_ledger_sha256"),
            "intake_minimum_evidence_status": summary.get("evidence_status"),
            "intake_minimum_intake_count": summary.get("intake_count"),
            "intake_minimum_pending_human_review_count": summary.get("pending_human_review_count"),
            "intake_minimum_reviewed_action_required_count": summary.get("reviewed_action_required_count"),
            "intake_minimum_not_material_count": summary.get("not_material_count"),
            "intake_minimum_review_counts": summary.get("review_counts", {}),
            "intake_minimum_routing_counts": summary.get("routing_counts", {}),
            "intake_minimum_input_files": summary.get("input_files", {}),
        }
    )
    if "intake evidence linkage" not in index["claims_boundary"].lower():
        index["claims_boundary"] = index["claims_boundary"].rstrip() + CLAIMS_BOUNDARY_APPENDIX
    index["release_index_digest"] = canonical_digest(index)
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Link intake-minimum evidence into an existing SARA release index.")
    parser.add_argument("--release-index", type=Path, required=True, help="Path to release-index.json to update.")
    parser.add_argument("--intake-dir", type=Path, required=True, help="Directory containing intake-minimum evidence.")
    parser.add_argument("--intake-artifact-id", default=None)
    parser.add_argument("--intake-artifact-digest", required=True)
    parser.add_argument("--intake-artifact-url", default=None)
    parser.add_argument("--out", type=Path, default=None, help="Optional output path. Defaults to in-place update.")
    args = parser.parse_args(argv)

    index = link_intake_evidence(
        release_index_path=args.release_index,
        intake_dir=args.intake_dir,
        intake_artifact_id=args.intake_artifact_id,
        intake_artifact_digest=args.intake_artifact_digest,
        intake_artifact_url=args.intake_artifact_url,
    )
    out_path = args.out or args.release_index
    _write_json(out_path, index)
    print(_json_text(index), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
