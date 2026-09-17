from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .qualification import canonical_digest

RELEASE_INDEX_SCHEMA = "WS-SARA-RELEASE-EVIDENCE-INDEX-V1"
SBOM_EVIDENCE_SCHEMA = "WS-SOFTWARE-SUPPLY-CHAIN-EVIDENCE-V1"
VULNERABILITY_EVIDENCE_SCHEMA = "WS-VULNERABILITY-ADVISORY-EVIDENCE-V1"
HUMAN_TRIAGE_LEDGER_SCHEMA = "WS-VULNERABILITY-HUMAN-TRIAGE-LEDGER-V1"
MERGE_STATE_PR_CANDIDATE = "PR_CANDIDATE_UNMERGED"
MERGE_STATE_MAIN_PUSH = "MAIN_BRANCH_PUSH"
MERGE_STATE_MANUAL_OR_NON_MAIN = "MANUAL_OR_NON_MAIN_RUN"
ALLOWED_MERGE_STATES = {
    MERGE_STATE_PR_CANDIDATE,
    MERGE_STATE_MAIN_PUSH,
    MERGE_STATE_MANUAL_OR_NON_MAIN,
}

CLAIMS_BOUNDARY = (
    "Release index records CI evidence custody only. It does not establish partner validation, "
    "supplier approval, certification, CMMC/NIST/DFARS conformity, classified access, DOE validation, "
    "external reproduction, field performance, hardware performance, export-control clearance, "
    "software supply-chain completeness, absence of vulnerabilities, advisory-feed completeness, "
    "vulnerability scan pass, vulnerability remediation, human-review completion, exploitability analysis, "
    "license legal review, SLSA compliance, or operational authority."
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required JSON file missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file missing for digest: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _normalize_digest(value: str | None, *, field: str, required: bool = True) -> str | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{field} is required")
        return None
    raw = str(value).strip()
    if raw.startswith("sha256:"):
        hex_value = raw[len("sha256:") :]
    else:
        hex_value = raw
    if len(hex_value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in hex_value):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return f"sha256:{hex_value.lower()}"


def _artifact_record(*, name: str, artifact_id: str | None, digest: str | None, url: str | None, required: bool = True) -> dict[str, Any]:
    normalized = _normalize_digest(digest, field=f"{name}.digest", required=required)
    return {
        "name": name,
        "artifact_id": artifact_id or None,
        "artifact_digest": normalized,
        "artifact_url": url or None,
    }


def derive_merge_state(*, event_name: str, ref: str) -> str:
    """Derive the release-index merge-state label from GitHub event context."""
    if event_name == "pull_request":
        return MERGE_STATE_PR_CANDIDATE
    if event_name == "push" and ref == "refs/heads/main":
        return MERGE_STATE_MAIN_PUSH
    return MERGE_STATE_MANUAL_OR_NON_MAIN


def _validate_release_context(*, event_name: str, ref: str, pr_number: str | None, merge_state: str) -> None:
    if merge_state not in ALLOWED_MERGE_STATES:
        raise ValueError(f"merge_state must be one of {sorted(ALLOWED_MERGE_STATES)}")
    expected = derive_merge_state(event_name=event_name, ref=ref)
    if merge_state != expected:
        raise ValueError(
            f"merge_state {merge_state!r} does not match event/ref context; expected {expected!r} "
            f"for event_name={event_name!r}, ref={ref!r}"
        )
    if merge_state == MERGE_STATE_PR_CANDIDATE and not pr_number:
        raise ValueError("pull_request release indexes must include a PR number")
    if merge_state == MERGE_STATE_MAIN_PUSH and pr_number:
        raise ValueError("main push release indexes must not include a PR number")


def _validate_sbom_summary(sbom_summary: dict[str, Any]) -> None:
    if sbom_summary.get("schema") != SBOM_EVIDENCE_SCHEMA:
        raise ValueError("unexpected SBOM evidence summary schema")
    if sbom_summary.get("evidence_status") != "INTERNAL_CI_GENERATED_UNSIGNED":
        raise ValueError("unexpected SBOM evidence status")
    if not sbom_summary.get("software_sbom_sha256", "").startswith("sha256:"):
        raise ValueError("SBOM summary missing software_sbom_sha256")
    claims_boundary = sbom_summary.get("claims_boundary", "")
    if "does not establish" not in claims_boundary:
        raise ValueError("SBOM summary missing claims boundary")


def _validate_vulnerability_summary(
    vulnerability_summary: dict[str, Any],
    vulnerability_report_path: Path,
) -> None:
    if vulnerability_summary.get("schema") != VULNERABILITY_EVIDENCE_SCHEMA:
        raise ValueError("unexpected vulnerability evidence summary schema")
    if vulnerability_summary.get("evidence_status") != "INTERNAL_CI_GENERATED_UNSIGNED":
        raise ValueError("unexpected vulnerability evidence status")
    recorded_digest = _normalize_digest(
        vulnerability_summary.get("vulnerability_report_sha256"),
        field="vulnerability summary vulnerability_report_sha256",
    )
    actual_digest = _sha256_file(vulnerability_report_path)
    if recorded_digest != actual_digest:
        raise ValueError(
            "vulnerability report digest mismatch: "
            f"summary records {recorded_digest}, file is {actual_digest}"
        )
    claims_boundary = vulnerability_summary.get("claims_boundary", "")
    if "does not establish" not in claims_boundary:
        raise ValueError("vulnerability summary missing claims boundary")


def _validate_human_triage_summary(
    human_triage_summary: dict[str, Any],
    human_triage_ledger_path: Path,
) -> None:
    if human_triage_summary.get("schema") != HUMAN_TRIAGE_LEDGER_SCHEMA:
        raise ValueError("unexpected human triage summary schema")
    if human_triage_summary.get("evidence_status") != "INTERNAL_REVIEW_LEDGER_UNSIGNED":
        raise ValueError("unexpected human triage evidence status")
    recorded_digest = _normalize_digest(
        human_triage_summary.get("human_triage_ledger_sha256"),
        field="human triage summary human_triage_ledger_sha256",
    )
    actual_digest = _sha256_file(human_triage_ledger_path)
    if recorded_digest != actual_digest:
        raise ValueError(
            "human triage ledger digest mismatch: "
            f"summary records {recorded_digest}, file is {actual_digest}"
        )
    claims_boundary = human_triage_summary.get("claims_boundary", "")
    if "does not establish" not in claims_boundary:
        raise ValueError("human triage summary missing claims boundary")


def build_release_evidence_index(
    *,
    repository: str,
    commit_sha: str,
    workflow_name: str,
    workflow_run_id: str,
    workflow_run_number: str,
    event_name: str,
    ref: str,
    pr_number: str | None,
    merge_state: str,
    pre_dir: Path,
    partner_dir: Path,
    sbom_dir: Path,
    vulnerability_dir: Path,
    human_triage_dir: Path,
    pre_artifact_id: str | None,
    pre_artifact_digest: str | None,
    pre_artifact_url: str | None,
    partner_artifact_id: str | None,
    partner_artifact_digest: str | None,
    partner_artifact_url: str | None,
    sbom_artifact_id: str | None,
    sbom_artifact_digest: str | None,
    sbom_artifact_url: str | None,
    vulnerability_artifact_id: str | None,
    vulnerability_artifact_digest: str | None,
    vulnerability_artifact_url: str | None,
    human_triage_artifact_id: str | None,
    human_triage_artifact_digest: str | None,
    human_triage_artifact_url: str | None,
    executed_utc: str | None = None,
) -> dict[str, Any]:
    """Build a machine-readable release evidence index for one SARA CI run."""
    if not commit_sha:
        raise ValueError("commit_sha is required")
    _validate_release_context(event_name=event_name, ref=ref, pr_number=pr_number, merge_state=merge_state)
    pre_root = Path(pre_dir)
    partner_root = Path(partner_dir)
    sbom_root = Path(sbom_dir)
    vulnerability_root = Path(vulnerability_dir)
    human_triage_root = Path(human_triage_dir)

    qualification_index = _load_json(pre_root / "qualification_index.json")
    partner_batch_manifest = _load_json(partner_root / "batch-manifest.json")
    sbom_summary = _load_json(sbom_root / "sbom-evidence-summary.json")
    vulnerability_summary = _load_json(vulnerability_root / "vulnerability-evidence-summary.json")
    human_triage_summary = _load_json(human_triage_root / "human-triage-summary.json")

    if partner_batch_manifest.get("schema") != "WS-PARTNER-SCREENING-BATCH-MANIFEST-V1":
        raise ValueError("unexpected partner batch manifest schema")
    if qualification_index.get("schema") is None:
        raise ValueError("qualification index missing schema")
    _validate_sbom_summary(sbom_summary)
    _validate_vulnerability_summary(
        vulnerability_summary,
        vulnerability_root / "vulnerability-advisory-report.json",
    )
    _validate_human_triage_summary(
        human_triage_summary,
        human_triage_root / "human-triage-ledger.json",
    )

    generated_at = executed_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    pre_artifact = _artifact_record(
        name="pre-full-bloom-qualification-evidence",
        artifact_id=pre_artifact_id,
        digest=pre_artifact_digest,
        url=pre_artifact_url,
    )
    partner_artifact = _artifact_record(
        name="partner-screening-batch-evidence",
        artifact_id=partner_artifact_id,
        digest=partner_artifact_digest,
        url=partner_artifact_url,
    )
    sbom_artifact = _artifact_record(
        name="software-sbom-evidence",
        artifact_id=sbom_artifact_id,
        digest=sbom_artifact_digest,
        url=sbom_artifact_url,
    )
    vulnerability_artifact = _artifact_record(
        name="vulnerability-advisory-evidence",
        artifact_id=vulnerability_artifact_id,
        digest=vulnerability_artifact_digest,
        url=vulnerability_artifact_url,
    )
    human_triage_artifact = _artifact_record(
        name="human-triage-ledger-evidence",
        artifact_id=human_triage_artifact_id,
        digest=human_triage_artifact_digest,
        url=human_triage_artifact_url,
    )

    index: dict[str, Any] = {
        "schema": RELEASE_INDEX_SCHEMA,
        "generated_utc": generated_at,
        "repository": repository,
        "commit_sha": commit_sha,
        "workflow": {
            "name": workflow_name,
            "run_id": workflow_run_id,
            "run_number": workflow_run_number,
            "event_name": event_name,
            "ref": ref,
            "pull_request_number": pr_number or None,
            "merge_state": merge_state,
        },
        "artifacts": {
            "software_sbom_evidence": sbom_artifact,
            "vulnerability_advisory_evidence": vulnerability_artifact,
            "human_triage_ledger_evidence": human_triage_artifact,
            "pre_full_bloom_qualification_evidence": pre_artifact,
            "partner_screening_batch_evidence": partner_artifact,
        },
        "local_evidence": {
            "sbom_summary_path": str(sbom_root / "sbom-evidence-summary.json"),
            "sbom_summary_sha256": _sha256_file(sbom_root / "sbom-evidence-summary.json"),
            "software_sbom_path": str(sbom_root / "software-sbom.json"),
            "software_sbom_sha256": _sha256_file(sbom_root / "software-sbom.json"),
            "sbom_component_count": sbom_summary.get("component_count"),
            "sbom_evidence_status": sbom_summary.get("evidence_status"),
            "sbom_input_files": sbom_summary.get("input_files", {}),
            "vulnerability_summary_path": str(vulnerability_root / "vulnerability-evidence-summary.json"),
            "vulnerability_summary_sha256": _sha256_file(vulnerability_root / "vulnerability-evidence-summary.json"),
            "vulnerability_report_path": str(vulnerability_root / "vulnerability-advisory-report.json"),
            "vulnerability_report_sha256": _sha256_file(vulnerability_root / "vulnerability-advisory-report.json"),
            "vulnerability_advisory_record_count": vulnerability_summary.get("advisory_record_count"),
            "vulnerability_matched_advisory_count": vulnerability_summary.get("matched_advisory_count"),
            "vulnerability_evidence_status": vulnerability_summary.get("evidence_status"),
            "vulnerability_advisory_input_status": vulnerability_summary.get("advisory_input_status"),
            "vulnerability_input_files": vulnerability_summary.get("input_files", {}),
            "human_triage_summary_path": str(human_triage_root / "human-triage-summary.json"),
            "human_triage_summary_sha256": _sha256_file(human_triage_root / "human-triage-summary.json"),
            "human_triage_ledger_path": str(human_triage_root / "human-triage-ledger.json"),
            "human_triage_ledger_sha256": _sha256_file(human_triage_root / "human-triage-ledger.json"),
            "human_triage_evidence_status": human_triage_summary.get("evidence_status"),
            "human_triage_review_input_status": human_triage_summary.get("review_input_status"),
            "human_triage_overall_status": human_triage_summary.get("overall_status"),
            "human_triage_ledger_record_count": human_triage_summary.get("ledger_record_count"),
            "human_triage_review_required_count": human_triage_summary.get("human_review_required_count"),
            "human_triage_pending_review_count": human_triage_summary.get("pending_review_count"),
            "human_triage_patch_required_count": human_triage_summary.get("patch_required_count"),
            "human_triage_accepted_risk_count": human_triage_summary.get("accepted_risk_count"),
            "human_triage_deferred_count": human_triage_summary.get("deferred_count"),
            "human_triage_input_files": human_triage_summary.get("input_files", {}),
            "qualification_index_path": str(pre_root / "qualification_index.json"),
            "qualification_index_sha256": _sha256_file(pre_root / "qualification_index.json"),
            "partner_batch_manifest_path": str(partner_root / "batch-manifest.json"),
            "partner_batch_manifest_sha256": _sha256_file(partner_root / "batch-manifest.json"),
            "partner_batch_digest": partner_batch_manifest.get("batch_digest"),
            "partner_package_count": partner_batch_manifest.get("package_count"),
            "partner_source_bundle_count": partner_batch_manifest.get("source_bundle_count"),
            "partner_presets": partner_batch_manifest.get("partners", []),
            "partner_lanes": partner_batch_manifest.get("lanes", []),
        },
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    index["release_index_digest"] = canonical_digest(index)
    return index


def _pr_number_from_event(path: str | None) -> str | None:
    if not path:
        return None
    event_path = Path(path)
    if not event_path.is_file():
        return None
    event = _load_json(event_path)
    number = event.get("number") or event.get("pull_request", {}).get("number")
    return str(number) if number else None


def _resolve_pr_number(*, cli_value: str | None, event_name: str) -> str | None:
    if cli_value is not None:
        return cli_value or None
    if event_name == "pull_request":
        return _pr_number_from_event(os.getenv("GITHUB_EVENT_PATH"))
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SARA release evidence index JSON for a CI run.")
    parser.add_argument("--out", type=Path, required=True, help="Output release-index.json path.")
    parser.add_argument("--pre-dir", type=Path, required=True, help="Directory containing PRE full-bloom evidence.")
    parser.add_argument("--partner-dir", type=Path, required=True, help="Directory containing partner-screening batch evidence.")
    parser.add_argument("--sbom-dir", type=Path, required=True, help="Directory containing software SBOM evidence.")
    parser.add_argument(
        "--vulnerability-dir",
        type=Path,
        required=True,
        help="Directory containing vulnerability/advisory evidence.",
    )
    parser.add_argument(
        "--human-triage-dir",
        type=Path,
        required=True,
        help="Directory containing human-review advisory triage ledger evidence.",
    )
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--workflow-name", default=os.getenv("GITHUB_WORKFLOW", ""))
    parser.add_argument("--workflow-run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument("--workflow-run-number", default=os.getenv("GITHUB_RUN_NUMBER", ""))
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--ref", default=os.getenv("GITHUB_REF", ""))
    parser.add_argument("--pr-number", default=None)
    parser.add_argument("--merge-state", default=None)
    parser.add_argument("--pre-artifact-id", default=None)
    parser.add_argument("--pre-artifact-digest", default=None)
    parser.add_argument("--pre-artifact-url", default=None)
    parser.add_argument("--partner-artifact-id", default=None)
    parser.add_argument("--partner-artifact-digest", default=None)
    parser.add_argument("--partner-artifact-url", default=None)
    parser.add_argument("--sbom-artifact-id", default=None)
    parser.add_argument("--sbom-artifact-digest", default=None)
    parser.add_argument("--sbom-artifact-url", default=None)
    parser.add_argument("--vulnerability-artifact-id", default=None)
    parser.add_argument("--vulnerability-artifact-digest", default=None)
    parser.add_argument("--vulnerability-artifact-url", default=None)
    parser.add_argument("--human-triage-artifact-id", default=None)
    parser.add_argument("--human-triage-artifact-digest", default=None)
    parser.add_argument("--human-triage-artifact-url", default=None)
    parser.add_argument("--executed-utc", default=None)
    args = parser.parse_args(argv)

    pr_number = _resolve_pr_number(cli_value=args.pr_number, event_name=args.event_name)
    merge_state = args.merge_state or derive_merge_state(event_name=args.event_name, ref=args.ref)

    index = build_release_evidence_index(
        repository=args.repository,
        commit_sha=args.commit_sha,
        workflow_name=args.workflow_name,
        workflow_run_id=args.workflow_run_id,
        workflow_run_number=args.workflow_run_number,
        event_name=args.event_name,
        ref=args.ref,
        pr_number=pr_number,
        merge_state=merge_state,
        pre_dir=args.pre_dir,
        partner_dir=args.partner_dir,
        sbom_dir=args.sbom_dir,
        vulnerability_dir=args.vulnerability_dir,
        human_triage_dir=args.human_triage_dir,
        pre_artifact_id=args.pre_artifact_id,
        pre_artifact_digest=args.pre_artifact_digest,
        pre_artifact_url=args.pre_artifact_url,
        partner_artifact_id=args.partner_artifact_id,
        partner_artifact_digest=args.partner_artifact_digest,
        partner_artifact_url=args.partner_artifact_url,
        sbom_artifact_id=args.sbom_artifact_id,
        sbom_artifact_digest=args.sbom_artifact_digest,
        sbom_artifact_url=args.sbom_artifact_url,
        vulnerability_artifact_id=args.vulnerability_artifact_id,
        vulnerability_artifact_digest=args.vulnerability_artifact_digest,
        vulnerability_artifact_url=args.vulnerability_artifact_url,
        human_triage_artifact_id=args.human_triage_artifact_id,
        human_triage_artifact_digest=args.human_triage_artifact_digest,
        human_triage_artifact_url=args.human_triage_artifact_url,
        executed_utc=args.executed_utc,
    )
    _write_json(args.out, index)
    print(_json_text(index), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
