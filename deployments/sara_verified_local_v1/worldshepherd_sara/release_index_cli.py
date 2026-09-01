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

CLAIMS_BOUNDARY = (
    "Release index records CI evidence custody only. It does not establish partner validation, "
    "supplier approval, certification, CMMC/NIST/DFARS conformity, classified access, DOE validation, "
    "external reproduction, field performance, hardware performance, export-control clearance, or operational authority."
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
    pre_artifact_id: str | None,
    pre_artifact_digest: str | None,
    pre_artifact_url: str | None,
    partner_artifact_id: str | None,
    partner_artifact_digest: str | None,
    partner_artifact_url: str | None,
    executed_utc: str | None = None,
) -> dict[str, Any]:
    """Build a machine-readable release evidence index for one SARA CI run."""
    if not commit_sha:
        raise ValueError("commit_sha is required")
    pre_root = Path(pre_dir)
    partner_root = Path(partner_dir)
    qualification_index = _load_json(pre_root / "qualification_index.json")
    partner_batch_manifest = _load_json(partner_root / "batch-manifest.json")

    if partner_batch_manifest.get("schema") != "WS-PARTNER-SCREENING-BATCH-MANIFEST-V1":
        raise ValueError("unexpected partner batch manifest schema")
    if qualification_index.get("schema") is None:
        raise ValueError("qualification index missing schema")

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
            "pre_full_bloom_qualification_evidence": pre_artifact,
            "partner_screening_batch_evidence": partner_artifact,
        },
        "local_evidence": {
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SARA release evidence index JSON for a CI run.")
    parser.add_argument("--out", type=Path, required=True, help="Output release-index.json path.")
    parser.add_argument("--pre-dir", type=Path, required=True, help="Directory containing PRE full-bloom evidence.")
    parser.add_argument("--partner-dir", type=Path, required=True, help="Directory containing partner-screening batch evidence.")
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
    parser.add_argument("--executed-utc", default=None)
    args = parser.parse_args(argv)

    pr_number = args.pr_number or _pr_number_from_event(os.getenv("GITHUB_EVENT_PATH"))
    merge_state = args.merge_state
    if merge_state is None:
        merge_state = "PR_CANDIDATE_UNMERGED" if args.event_name == "pull_request" else "POST_MERGE_OR_MANUAL_RUN"

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
        pre_artifact_id=args.pre_artifact_id,
        pre_artifact_digest=args.pre_artifact_digest,
        pre_artifact_url=args.pre_artifact_url,
        partner_artifact_id=args.partner_artifact_id,
        partner_artifact_digest=args.partner_artifact_digest,
        partner_artifact_url=args.partner_artifact_url,
        executed_utc=args.executed_utc,
    )
    _write_json(args.out, index)
    print(_json_text(index), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
