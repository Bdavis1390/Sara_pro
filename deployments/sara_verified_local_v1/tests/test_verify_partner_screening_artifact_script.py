from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from worldshepherd_sara.geo_provenance import build_geo_prov_bundle
from worldshepherd_sara.partner_screening_cli import export_partner_screening_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "verify_partner_screening_artifact.sh"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_batch_export(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    bundle = build_geo_prov_bundle(
        software_commit="downloaded-artifact-script-test",
        executed_utc="2026-09-01T17:00:00Z",
        operator="pytest",
    )
    _write_json(bundle_dir / "geo_prov_qualification_bundle.json", bundle)
    out_dir = tmp_path / "partner_screening_ci"
    export_partner_screening_batch(bundle_dir, out_dir, partners=["BAE_SYSTEMS", "GENERIC_PRIME"])
    return out_dir


def _zip_tree(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())


def test_downloaded_artifact_script_verifies_extracted_batch(tmp_path: Path) -> None:
    batch_dir = _make_batch_export(tmp_path)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(batch_dir)],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["verification_scope"] == "partner_screening_batch"
    assert report["verified_package_count"] == report["package_count"]


def test_downloaded_artifact_script_verifies_zip_and_expected_digest(tmp_path: Path) -> None:
    if shutil.which("unzip") is None:
        raise AssertionError("unzip must be available in CI to verify downloaded artifacts")

    batch_dir = _make_batch_export(tmp_path)
    zip_path = tmp_path / "partner-screening-batch-evidence.zip"
    _zip_tree(batch_dir, zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    result = subprocess.run(
        ["bash", str(SCRIPT), str(zip_path), f"sha256:{digest}"],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["verification_scope"] == "partner_screening_batch"


def test_downloaded_artifact_script_rejects_wrong_zip_digest(tmp_path: Path) -> None:
    if shutil.which("unzip") is None:
        raise AssertionError("unzip must be available in CI to verify downloaded artifacts")

    batch_dir = _make_batch_export(tmp_path)
    zip_path = tmp_path / "partner-screening-batch-evidence.zip"
    _zip_tree(batch_dir, zip_path)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(zip_path), "sha256:" + "0" * 64],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0
    assert "artifact ZIP digest mismatch" in result.stderr
