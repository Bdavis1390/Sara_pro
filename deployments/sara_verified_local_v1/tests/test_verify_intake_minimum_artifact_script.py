from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from worldshepherd_sara.intake_minimum_cli import (
    build_intake_minimum_ledger,
    write_intake_minimum_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = ROOT / "scripts" / "verify_intake_minimum_artifact.sh"


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _build_evidence(tmp_path: Path) -> Path:
    intake_file = tmp_path / "intakes.json"
    _write_json(
        intake_file,
        {
            "intakes": [
                {
                    "intake_id": "WS-INTAKE-VERIFY-001",
                    "intake_type": "USER_DIRECTIVE",
                    "source_system": "test",
                    "source_locator": "test:verify-script",
                    "source_retrieved_utc": "2026-09-01T18:25:00Z",
                    "source_sha256": "sha256:" + "1" * 64,
                    "evidence_status": "RAW_INTAKE_UNSIGNED",
                    "maturity_label": "RAW_INTAKE",
                    "human_review_status": "PENDING_HUMAN_REVIEW",
                    "routing_status": "ROUTED_TO_BACKLOG",
                    "downstream_route": "Retain for bounded review.",
                    "claims_boundary": "This intake does not establish validation, compliance, or award probability.",
                }
            ]
        },
    )
    ledger = build_intake_minimum_ledger(
        intake_file=intake_file,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="pytest",
        executed_utc="2026-09-01T18:30:00Z",
    )
    out_dir = tmp_path / "intake_minimum_ci"
    write_intake_minimum_evidence(ledger, out_dir)
    return out_dir


def test_verify_intake_minimum_artifact_accepts_valid_evidence(tmp_path: Path) -> None:
    out_dir = _build_evidence(tmp_path)

    result = subprocess.run(["bash", str(VERIFY_SCRIPT), str(out_dir)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_verify_intake_minimum_artifact_rejects_canonical_digest_tamper(tmp_path: Path) -> None:
    out_dir = _build_evidence(tmp_path)
    ledger_path = out_dir / "intake-minimum-ledger.json"
    summary_path = out_dir / "intake-minimum-summary.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["operator"] = "tampered"
    _write_json(ledger_path, ledger)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["intake_minimum_ledger_file_sha256"] = (
        "sha256:" + hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    )
    _write_json(summary_path, summary)

    result = subprocess.run(["bash", str(VERIFY_SCRIPT), str(out_dir)], capture_output=True, text=True)

    assert result.returncode != 0
    assert "canonical ledger digest mismatch" in result.stderr
