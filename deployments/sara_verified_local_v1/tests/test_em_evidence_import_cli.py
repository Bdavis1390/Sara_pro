import hashlib
import json
from pathlib import Path

import pytest

from worldshepherd_sara.em_d5 import D5EvidencePackage, D5InteractionEffect
from worldshepherd_sara.em_evidence_import_cli import import_uc06_evidence, main
from worldshepherd_sara.em_recovery import RecoveryReceipt


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_recovery(tmp_path: Path) -> tuple[Path, Path]:
    receipt = tmp_path / "recovery-receipt.txt"
    receipt_bytes = b"sealed recovery execution receipt\n"
    receipt.write_bytes(receipt_bytes)

    package = RecoveryReceipt(
        source_receipt=str(receipt.resolve()),
        source_receipt_sha256=_sha(receipt_bytes),
        completed_job_count=28,
        exit_zero_count=28,
        nonzero_exit_count=0,
        retained_output_count=28,
        durable_checkpoint_count=28,
        replacement_a027_fresh_output=True,
        direct_mpi_binary_topology=True,
        mpi_stdin_none=True,
        palace_stdin_dev_null=True,
        sleep_inhibitor_used=True,
    )
    package_path = tmp_path / "recovery-package.json"
    package_path.write_text(package.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return package_path, receipt


def _d5_effects() -> list[D5InteractionEffect]:
    names = [
        "STATE",
        "POLARIZATION",
        "ANGLE",
        "STATE_X_POLARIZATION",
        "STATE_X_ANGLE",
        "POLARIZATION_X_ANGLE",
        "STATE_X_POLARIZATION_X_ANGLE",
    ]
    return [
        D5InteractionEffect(
            principal_component=pc,
            effect=name,
            fraction_of_pc_variance=1.0 / 7.0,
        )
        for pc in (1, 2, 3)
        for name in names
    ]


def _write_d5(tmp_path: Path) -> tuple[Path, Path]:
    receipt = tmp_path / "d5-receipt.txt"
    receipt_bytes = b"sealed D5 diagnostic receipt\n"
    receipt.write_bytes(receipt_bytes)

    package = D5EvidencePackage(
        source_receipt=str(receipt.resolve()),
        source_receipt_sha256=_sha(receipt_bytes),
        interaction_effects=_d5_effects(),
        claims_boundary=["DIAGNOSTIC_ONLY", "NO_GATE_CHANGE"],
    )
    package_path = tmp_path / "d5-package.json"
    package_path.write_text(package.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return package_path, receipt


def test_recovery_import_establishes_execution_only(tmp_path: Path):
    package, receipt = _write_recovery(tmp_path)
    report = import_uc06_evidence(
        recovery_package=package,
        recovery_receipt=receipt,
    )

    assert report["read_only_import"] is True
    assert report["persisted_state_mutation"] is False
    assert report["network_mutation"] is False
    assert report["hardware_action_authorized"] is False

    imported = report["imported_evidence"]
    assert len(imported) == 1
    assert imported[0]["kind"] == "POWER_RECOVERY"
    assert imported[0]["sha256_match"] is True
    assert len(imported[0]["package_file_sha256"]) == 64

    maturity = report["maturity"]
    assert maturity["recovery_a027_a054_completion"] == "EXECUTION_COMPLETE"
    assert maturity["medium_fine_convergence"] == "NOT_ADJUDICATED"
    assert maturity["energy_closure"] == "PENDING"
    assert maturity["hardware_action"] == "NOT_AUTHORIZED"


def test_combined_d5_and_recovery_reduce_independently(tmp_path: Path):
    recovery_package, recovery_receipt = _write_recovery(tmp_path)
    d5_package, d5_receipt = _write_d5(tmp_path)

    report = import_uc06_evidence(
        d5_package=d5_package,
        d5_receipt=d5_receipt,
        recovery_package=recovery_package,
        recovery_receipt=recovery_receipt,
    )
    maturity = report["maturity"]

    assert maturity["d5_interaction_sparse_analysis"] == "INGESTED_DIAGNOSTIC"
    assert maturity["recovery_a027_a054_completion"] == "EXECUTION_COMPLETE"
    assert maturity["frozen_convergence_overall"] == "NOT_ADJUDICATED"
    assert maturity["physical_validation"] == "NOT_VALIDATED"
    assert maturity["full_campaign"] == "NOT_AUTHORIZED"
    assert maturity["hardware_action"] == "NOT_AUTHORIZED"


def test_tampered_receipt_fails_closed(tmp_path: Path):
    package, receipt = _write_recovery(tmp_path)
    receipt.write_bytes(b"tampered recovery receipt\n")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        import_uc06_evidence(
            recovery_package=package,
            recovery_receipt=receipt,
        )


def test_declared_source_path_must_match_actual_receipt(tmp_path: Path):
    package, receipt = _write_recovery(tmp_path)
    copied = tmp_path / "copied-receipt.txt"
    copied.write_bytes(receipt.read_bytes())

    with pytest.raises(ValueError, match="source_receipt path does not match"):
        import_uc06_evidence(
            recovery_package=package,
            recovery_receipt=copied,
        )


def test_package_receipt_pair_is_required(tmp_path: Path):
    package, _ = _write_recovery(tmp_path)

    with pytest.raises(ValueError, match="requires both package and receipt"):
        import_uc06_evidence(recovery_package=package)


def test_cli_emits_deterministic_read_only_json(tmp_path: Path, capsys):
    package, receipt = _write_recovery(tmp_path)

    rc = main(
        [
            "--recovery-package",
            str(package),
            "--recovery-receipt",
            str(receipt),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert captured.err == ""
    assert payload["schema_version"].endswith("v0.1")
    assert payload["read_only_import"] is True
    assert payload["persisted_state_mutation"] is False
    assert payload["hardware_action_authorized"] is False
    assert payload["maturity"]["recovery_a027_a054_completion"] == "EXECUTION_COMPLETE"


def test_cli_error_is_machine_readable_and_nonzero(tmp_path: Path, capsys):
    package, receipt = _write_recovery(tmp_path)
    receipt.write_bytes(b"wrong bytes\n")

    rc = main(
        [
            "--recovery-package",
            str(package),
            "--recovery-receipt",
            str(receipt),
        ]
    )
    captured = capsys.readouterr()
    error = json.loads(captured.err)

    assert rc == 2
    assert captured.out == ""
    assert error["status"] == "ERROR"
    assert error["persisted_state_mutation"] is False
    assert error["hardware_action_authorized"] is False
