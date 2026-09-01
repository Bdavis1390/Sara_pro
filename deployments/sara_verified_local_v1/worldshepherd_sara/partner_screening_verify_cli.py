from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .partner_screening_cli import REQUIRED_OUTPUTS, _assert_sanitized_text, _file_digest, _json_text
from .qualification import canonical_digest

VERIFY_SCHEMA = "WS-PARTNER-SCREENING-VERIFY-V1"
PACKAGE_MANIFEST_SCHEMA = "WS-PARTNER-SCREENING-MANIFEST-V1"
BATCH_MANIFEST_SCHEMA = "WS-PARTNER-SCREENING-BATCH-MANIFEST-V1"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required manifest file missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return value


def _require_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a non-empty list of strings")
    return list(value)


def _require_string_dict(value: Any, *, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError(f"{field} must be a non-empty string map")
    return dict(value)


def _verify_manifest_bootstrap_digest(manifest_path: Path, manifest: dict[str, Any], artifact_digests: dict[str, str]) -> str | None:
    """Verify the manifest's recorded self-digest against its bootstrap form.

    `export_partner_screening_package()` first writes the manifest without a
    manifest self-entry, hashes that bootstrap manifest, then records the hash
    under `artifact_digests["manifest.json"]`. A verifier must therefore remove
    the self-entry before recomputing the digest.
    """
    recorded = artifact_digests.get("manifest.json")
    if recorded is None:
        return None
    bootstrap = dict(manifest)
    bootstrap_digests = dict(artifact_digests)
    bootstrap_digests.pop("manifest.json", None)
    bootstrap["artifact_digests"] = bootstrap_digests
    actual = canonical_digest({"path": "manifest.json", "content": _json_text(bootstrap)})
    if actual != recorded:
        raise ValueError(f"digest mismatch for {manifest_path}: expected {recorded}, got {actual}")
    return actual


def _verify_batch_digest(batch_manifest: dict[str, Any]) -> str:
    recorded = batch_manifest.get("batch_digest")
    if not isinstance(recorded, str) or not recorded.startswith("sha256:"):
        raise ValueError("batch manifest missing batch_digest")
    bootstrap = dict(batch_manifest)
    bootstrap.pop("batch_digest", None)
    actual = canonical_digest(bootstrap)
    if actual != recorded:
        raise ValueError(f"batch digest mismatch: expected {recorded}, got {actual}")
    return actual


def _read_all_text(root: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*")) if path.is_file())


def verify_partner_screening_package(package_dir: Path) -> dict[str, Any]:
    """Verify one exported partner-screening package without mutating it."""
    root = Path(package_dir)
    if not root.is_dir():
        raise ValueError(f"partner-screening package directory does not exist: {root}")

    manifest_path = root / "manifest.json"
    manifest = _load_json(manifest_path)
    if manifest.get("schema") != PACKAGE_MANIFEST_SCHEMA:
        raise ValueError(f"unexpected package manifest schema: {manifest.get('schema')}")

    output_files = _require_string_list(manifest.get("output_files"), field="manifest.output_files")
    artifact_digests = _require_string_dict(manifest.get("artifact_digests"), field="manifest.artifact_digests")

    missing_required = sorted((REQUIRED_OUTPUTS - {"manifest.json"}) - set(output_files))
    if missing_required:
        raise ValueError(f"package manifest missing required output files: {missing_required}")

    checked: dict[str, str] = {}
    for filename in sorted(output_files):
        path = root / filename
        if not path.is_file():
            raise ValueError(f"declared package file missing: {path}")
        expected = artifact_digests.get(filename)
        if expected is None:
            raise ValueError(f"artifact digest missing for package file: {filename}")
        actual = _file_digest(path)
        if actual != expected:
            raise ValueError(f"digest mismatch for {path}: expected {expected}, got {actual}")
        checked[filename] = actual

    manifest_bootstrap_digest = _verify_manifest_bootstrap_digest(manifest_path, manifest, artifact_digests)
    if manifest_bootstrap_digest:
        checked["manifest.json"] = manifest_bootstrap_digest

    _assert_sanitized_text(_read_all_text(root))

    return {
        "schema": VERIFY_SCHEMA,
        "status": "PASS",
        "verification_scope": "partner_screening_package",
        "package_dir": str(root),
        "partner_id": manifest.get("partner_id"),
        "package_id": manifest.get("package_id"),
        "source_bundle_digest": manifest.get("source_bundle_digest"),
        "checked_file_count": len(checked),
        "checked_files": sorted(checked),
        "manifest_bootstrap_digest": manifest_bootstrap_digest,
        "claims_boundary": "Digest verification only; this does not establish partner validation, supplier approval, certification, compliance conformity, external reproduction, field performance, hardware performance, classified access, or operational authority.",
    }


def _resolve_package_dir(batch_root: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record.get("output_dir", "")))
    partner_id = str(record.get("partner_id", "")).lower()
    lane = str(record.get("lane", ""))
    candidates = []
    if raw:
        candidates.append(raw)
        if raw.parts and raw.parts[0] == batch_root.name:
            candidates.append(batch_root.joinpath(*raw.parts[1:]))
    if partner_id and lane:
        candidates.append(batch_root / partner_id / lane)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise ValueError(f"could not resolve package directory for batch export record: {record}")


def verify_partner_screening_batch(batch_dir: Path) -> dict[str, Any]:
    """Verify a batch partner-screening artifact tree without mutating it."""
    root = Path(batch_dir)
    if not root.is_dir():
        raise ValueError(f"partner-screening batch directory does not exist: {root}")

    batch_manifest_path = root / "batch-manifest.json"
    batch_manifest = _load_json(batch_manifest_path)
    if batch_manifest.get("schema") != BATCH_MANIFEST_SCHEMA:
        raise ValueError(f"unexpected batch manifest schema: {batch_manifest.get('schema')}")

    exports = batch_manifest.get("exports")
    if not isinstance(exports, list) or not exports:
        raise ValueError("batch manifest must include a non-empty exports list")
    partners = _require_string_list(batch_manifest.get("partners"), field="batch_manifest.partners")
    lanes = _require_string_list(batch_manifest.get("lanes"), field="batch_manifest.lanes")
    if batch_manifest.get("source_bundle_count") != len(set(lanes)):
        raise ValueError("batch source_bundle_count does not match lanes")
    if batch_manifest.get("package_count") != len(exports):
        raise ValueError("batch package_count does not match export records")
    if batch_manifest.get("package_count") != batch_manifest.get("source_bundle_count") * len(partners):
        raise ValueError("batch package_count does not match source bundles multiplied by partners")

    batch_digest = _verify_batch_digest(batch_manifest)
    _assert_sanitized_text(batch_manifest_path.read_text(encoding="utf-8"))

    package_reports = []
    for record in exports:
        if not isinstance(record, dict):
            raise ValueError("batch export records must be JSON objects")
        package_dir = _resolve_package_dir(root, record)
        report = verify_partner_screening_package(package_dir)
        if record.get("source_bundle_digest") != report.get("source_bundle_digest"):
            raise ValueError(f"source bundle digest mismatch for batch export record: {record}")
        if record.get("package_manifest_digest") != report.get("manifest_bootstrap_digest"):
            raise ValueError(f"package manifest digest mismatch for batch export record: {record}")
        package_reports.append(report)

    return {
        "schema": VERIFY_SCHEMA,
        "status": "PASS",
        "verification_scope": "partner_screening_batch",
        "batch_dir": str(root),
        "partners": partners,
        "lanes": sorted(set(lanes)),
        "source_bundle_count": batch_manifest.get("source_bundle_count"),
        "package_count": batch_manifest.get("package_count"),
        "verified_package_count": len(package_reports),
        "batch_digest": batch_digest,
        "claims_boundary": "Batch digest verification only; this does not establish partner validation, supplier approval, certification, compliance conformity, external reproduction, field performance, hardware performance, classified access, or operational authority.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify partner-screening package manifests and artifact digests.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path, help="Directory containing one partner-screening manifest.json.")
    group.add_argument("--batch", type=Path, help="Directory containing batch-manifest.json and partner/lane package folders.")
    args = parser.parse_args(argv)

    try:
        if args.package is not None:
            report = verify_partner_screening_package(args.package)
        else:
            report = verify_partner_screening_batch(args.batch)
    except Exception as exc:  # pragma: no cover - exercised through CLI behavior
        print(_json_text({"schema": VERIFY_SCHEMA, "status": "FAIL", "error": str(exc)}), end="", file=sys.stderr)
        return 1

    print(_json_text(report), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
