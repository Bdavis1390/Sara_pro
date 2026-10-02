"""Local-only UC06-P1 sealed evidence importer.

This command verifies actual local receipt bytes, validates typed evidence packages,
and computes a read-only maturity report. It does not mutate repository/service state,
perform network actions, change scientific gates, or authorize hardware.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from .em_convergence_evidence import (
    CONVERGENCE_EVIDENCE_SCHEMA_VERSION,
    ConvergenceEvidencePackage,
)
from .em_d5 import D5EvidencePackage, D5_CONTRACT_VERSION
from .em_maturity_reducer import reduce_uc06_maturity
from .em_recovery import RecoveryReceipt, RECOVERY_CONTRACT_VERSION
from .em_sealed_receipts import (
    SealedEvidenceKind,
    VerifiedConvergenceEvidence,
    VerifiedD5Evidence,
    VerifiedRecoveryEvidence,
    verify_sealed_receipt_bytes,
)


IMPORT_REPORT_SCHEMA_VERSION = "worldshepherd.uc06-p1.evidence-import-report.v0.1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=True)


def _validate_pair(name: str, package: Path | None, receipt: Path | None) -> None:
    if (package is None) != (receipt is None):
        raise ValueError(f"{name} requires both package and receipt paths")


def _load_package(path: Path, model: type[BaseModel]) -> tuple[BaseModel, bytes]:
    raw = _resolved(path).read_bytes()
    if not raw:
        raise ValueError(f"evidence package must not be empty: {path}")
    return model.model_validate_json(raw), raw


def _require_declared_source(package: Any, receipt_path: Path) -> Path:
    actual = _resolved(receipt_path)
    declared = Path(package.source_receipt).expanduser().resolve(strict=False)
    if declared != actual:
        raise ValueError(
            "package source_receipt path does not match the local receipt path: "
            f"declared={declared} actual={actual}"
        )
    return actual


def _record(kind: str, package_path: Path, package_bytes: bytes, binding: Any) -> dict[str, object]:
    return {
        "kind": kind,
        "package_path": str(_resolved(package_path)),
        "package_file_sha256": _sha256(package_bytes),
        "source_receipt": binding.source_receipt,
        "source_receipt_sha256": binding.observed_sha256,
        "receipt_byte_length": binding.byte_length,
        "sha256_match": True,
        "read_only_import": True,
    }


def import_uc06_evidence(
    *,
    d5_package: Path | None = None,
    d5_receipt: Path | None = None,
    recovery_package: Path | None = None,
    recovery_receipt: Path | None = None,
    convergence_package: Path | None = None,
    convergence_receipt: Path | None = None,
) -> dict[str, object]:
    """Verify supplied local evidence and derive a non-persistent maturity report."""

    _validate_pair("D5 evidence", d5_package, d5_receipt)
    _validate_pair("recovery evidence", recovery_package, recovery_receipt)
    _validate_pair("convergence evidence", convergence_package, convergence_receipt)

    if not any((d5_package, recovery_package, convergence_package)):
        raise ValueError("at least one evidence package/receipt pair is required")

    verified_d5 = None
    verified_recovery = None
    verified_convergence = None
    imported: list[dict[str, object]] = []

    if d5_package is not None and d5_receipt is not None:
        package, package_bytes = _load_package(d5_package, D5EvidencePackage)
        assert isinstance(package, D5EvidencePackage)
        actual = _require_declared_source(package, d5_receipt)
        receipt_bytes = actual.read_bytes()
        binding = verify_sealed_receipt_bytes(
            evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
            evidence_contract_version=D5_CONTRACT_VERSION,
            source_receipt=package.source_receipt,
            expected_sha256=package.source_receipt_sha256,
            receipt_bytes=receipt_bytes,
        )
        verified_d5 = VerifiedD5Evidence(receipt=binding, package=package)
        imported.append(_record("D5_DIAGNOSTIC", d5_package, package_bytes, binding))

    if recovery_package is not None and recovery_receipt is not None:
        package, package_bytes = _load_package(recovery_package, RecoveryReceipt)
        assert isinstance(package, RecoveryReceipt)
        actual = _require_declared_source(package, recovery_receipt)
        receipt_bytes = actual.read_bytes()
        binding = verify_sealed_receipt_bytes(
            evidence_kind=SealedEvidenceKind.POWER_RECOVERY,
            evidence_contract_version=RECOVERY_CONTRACT_VERSION,
            source_receipt=package.source_receipt,
            expected_sha256=package.source_receipt_sha256,
            receipt_bytes=receipt_bytes,
        )
        verified_recovery = VerifiedRecoveryEvidence(receipt=binding, package=package)
        imported.append(_record("POWER_RECOVERY", recovery_package, package_bytes, binding))

    if convergence_package is not None and convergence_receipt is not None:
        package, package_bytes = _load_package(convergence_package, ConvergenceEvidencePackage)
        assert isinstance(package, ConvergenceEvidencePackage)
        actual = _require_declared_source(package, convergence_receipt)
        receipt_bytes = actual.read_bytes()
        binding = verify_sealed_receipt_bytes(
            evidence_kind=SealedEvidenceKind.FROZEN_CONVERGENCE,
            evidence_contract_version=CONVERGENCE_EVIDENCE_SCHEMA_VERSION,
            source_receipt=package.source_receipt,
            expected_sha256=package.source_receipt_sha256,
            receipt_bytes=receipt_bytes,
        )
        verified_convergence = VerifiedConvergenceEvidence(receipt=binding, package=package)
        imported.append(
            _record("FROZEN_CONVERGENCE", convergence_package, package_bytes, binding)
        )

    maturity = reduce_uc06_maturity(
        d5=verified_d5,
        recovery=verified_recovery,
        convergence=verified_convergence,
    )

    return {
        "schema_version": IMPORT_REPORT_SCHEMA_VERSION,
        "evidence_scope": "UC06-P1",
        "read_only_import": True,
        "persisted_state_mutation": False,
        "network_mutation": False,
        "hardware_action_authorized": False,
        "software_report_is_physics_validation": False,
        "imported_evidence": imported,
        "maturity": maturity.model_dump(mode="json"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify local UC06-P1 sealed receipts and typed evidence packages, then "
            "emit a read-only evidence-driven maturity report."
        )
    )
    parser.add_argument("--d5-package", type=Path)
    parser.add_argument("--d5-receipt", type=Path)
    parser.add_argument("--recovery-package", type=Path)
    parser.add_argument("--recovery-receipt", type=Path)
    parser.add_argument("--convergence-package", type=Path)
    parser.add_argument("--convergence-receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = import_uc06_evidence(
            d5_package=args.d5_package,
            d5_receipt=args.d5_receipt,
            recovery_package=args.recovery_package,
            recovery_receipt=args.recovery_receipt,
            convergence_package=args.convergence_package,
            convergence_receipt=args.convergence_receipt,
        )
    except (OSError, ValueError, ValidationError) as exc:
        error = {
            "schema_version": IMPORT_REPORT_SCHEMA_VERSION,
            "status": "ERROR",
            "read_only_import": True,
            "persisted_state_mutation": False,
            "hardware_action_authorized": False,
            "error": str(exc),
        }
        print(json.dumps(error, sort_keys=True), file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        output = args.output.expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
