from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint_anchor import export_external_anchor
from worldshepherd_sara.audit_checkpoint_guarded import GuardedSaraAuditCheckpointManager
from worldshepherd_sara.audit_checkpoint_offline_verify import (
    SaraAuditOfflineVerificationError,
    verify_offline_export,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T19:{sequence:02d}:00+00:00",
            event="offline_verifier_evidence",
            actor="admin_operator",
            payload={"sequence": sequence, "state": "expected"},
        )
    )


def _write_case(
    root: Path,
    name: str,
    *,
    audit_bytes: bytes,
    ledger_bytes: bytes,
    anchor_bytes: bytes,
) -> tuple[Path, Path, Path]:
    case = root / name
    case.mkdir()
    audit = (case / "audit.jsonl").resolve()
    ledger = (case / "audit-checkpoints.jsonl").resolve()
    anchor = (case / "external-anchor.json").resolve()
    audit.write_bytes(audit_bytes)
    ledger.write_bytes(ledger_bytes)
    anchor.write_bytes(anchor_bytes)
    for path in (audit, ledger, anchor):
        path.chmod(0o600)
    return audit, ledger, anchor


def _verify(paths: tuple[Path, Path, Path]) -> dict[str, Any]:
    audit, ledger, anchor = paths
    return verify_offline_export(
        audit_path=audit,
        checkpoint_ledger_path=ledger,
        external_anchor_path=anchor,
    )


def _expect_rejected(
    paths: tuple[Path, Path, Path],
    expected_fragment: str,
) -> dict[str, Any]:
    try:
        _verify(paths)
    except SaraAuditOfflineVerificationError as exc:
        message = str(exc)
        if expected_fragment not in message:
            raise RuntimeError(
                f"unexpected rejection; wanted {expected_fragment!r}, got {message!r}"
            ) from exc
        return {"detected": True, "error": message}
    raise RuntimeError(f"adversarial case was not rejected: {expected_fragment}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-audit-offline-evidence-") as temp:
        root = Path(temp)
        producer_root = root / "producer"
        external_root = root / "external"
        evaluator_root = root / "evaluator"
        external_root.mkdir()
        evaluator_root.mkdir()
        key = Ed25519PrivateKey.generate()

        first_store = DurableStore(producer_root)
        first_manager = GuardedSaraAuditCheckpointManager(
            first_store,
            private_key=key,
            key_id="SARA-AUDIT-OFFLINE-EVIDENCE-V1",
        )
        _append(first_store, 1)
        _append(first_store, 2)
        first_manager.create_checkpoint()
        first_audit = first_store.audit_path.read_bytes()
        first_ledger = first_manager.ledger_path.read_bytes()

        # Reconstruct the producer from durable state to model a service restart.
        restarted_store = DurableStore(producer_root)
        restarted_manager = GuardedSaraAuditCheckpointManager(
            restarted_store,
            private_key=key,
            key_id="SARA-AUDIT-OFFLINE-EVIDENCE-V1",
        )
        _append(restarted_store, 3)
        second = restarted_manager.create_checkpoint()
        anchor_path = (external_root / "anchor-sequence-2.json").resolve()
        anchor = export_external_anchor(restarted_manager, anchor_path)
        anchor_bytes = anchor_path.read_bytes()
        latest_audit = restarted_store.audit_path.read_bytes()
        latest_ledger = restarted_manager.ledger_path.read_bytes()

        baseline_paths = _write_case(
            evaluator_root,
            "baseline",
            audit_bytes=latest_audit,
            ledger_bytes=latest_ledger,
            anchor_bytes=anchor_bytes,
        )
        baseline = _verify(baseline_paths)
        if baseline["status"] != "PASS":
            raise RuntimeError(f"baseline offline verification failed: {baseline}")

        _append(restarted_store, 4)
        tail_paths = _write_case(
            evaluator_root,
            "uncheckpointed-tail",
            audit_bytes=restarted_store.audit_path.read_bytes(),
            ledger_bytes=latest_ledger,
            anchor_bytes=anchor_bytes,
        )
        tail = _verify(tail_paths)
        if tail["status"] != "PASS_WITH_UNCHECKPOINTED_TAIL":
            raise RuntimeError(f"tail visibility failed: {tail}")

        rollback_paths = _write_case(
            evaluator_root,
            "audit-rollback",
            audit_bytes=first_audit,
            ledger_bytes=latest_ledger,
            anchor_bytes=anchor_bytes,
        )
        audit_rollback = _expect_rejected(rollback_paths, "rollback/truncation")

        coordinated_paths = _write_case(
            evaluator_root,
            "coordinated-local-rollback",
            audit_bytes=first_audit,
            ledger_bytes=first_ledger,
            anchor_bytes=anchor_bytes,
        )
        coordinated_rollback = _expect_rejected(
            coordinated_paths, "rollback/latest-digest mismatch"
        )

        mutated_lines = latest_audit.decode("utf-8").splitlines()
        mutated_first = json.loads(mutated_lines[0])
        mutated_first["payload"]["state"] = "tampered"
        mutated_lines[0] = json.dumps(
            mutated_first,
            sort_keys=True,
            separators=(",", ":"),
        )
        mutated_audit = ("\n".join(mutated_lines) + "\n").encode("utf-8")
        mutation_paths = _write_case(
            evaluator_root,
            "checkpointed-content-mutation",
            audit_bytes=mutated_audit,
            ledger_bytes=latest_ledger,
            anchor_bytes=anchor_bytes,
        )
        content_mutation = _expect_rejected(
            mutation_paths, "prefix integrity mismatch"
        )

        tampered_ledger_lines = latest_ledger.decode("utf-8").splitlines()
        latest_bundle = json.loads(tampered_ledger_lines[-1])
        latest_bundle["manifest"]["record_count"] = 99
        tampered_ledger_lines[-1] = json.dumps(
            latest_bundle,
            sort_keys=True,
            separators=(",", ":"),
        )
        tampered_ledger = ("\n".join(tampered_ledger_lines) + "\n").encode("utf-8")
        ledger_tamper_paths = _write_case(
            evaluator_root,
            "signed-ledger-tamper",
            audit_bytes=latest_audit,
            ledger_bytes=tampered_ledger,
            anchor_bytes=anchor_bytes,
        )
        signed_ledger_tamper = _expect_rejected(
            ledger_tamper_paths, "manifest digest mismatch"
        )

    result = {
        "schema": "WS-SARA-AUDIT-OFFLINE-ADVERSARIAL-EVIDENCE-V1",
        "result": "PASS",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "producer": {
            "restart_reconstruction_exercised": True,
            "checkpoint_sequence_after_restart": second["manifest"]["sequence"],
            "checkpoint_sha256": second["checkpoint_sha256"],
            "anchor_sha256": anchor["anchor_sha256"],
            "checkpoint_record_count": anchor["checkpoint_record_count"],
        },
        "offline_evaluator": {
            "private_key_input": False,
            "running_sara_service": False,
            "baseline_status": baseline["status"],
            "uncheckpointed_tail_status": tail["status"],
            "uncheckpointed_tail_records": tail["uncheckpointed_records"],
        },
        "adversarial_acceptance": {
            "audit_rollback_after_restart_detected": audit_rollback["detected"],
            "coordinated_local_audit_and_ledger_rollback_detected_against_external_pin": coordinated_rollback["detected"],
            "checkpointed_content_mutation_detected": content_mutation["detected"],
            "signed_checkpoint_ledger_tampering_detected": signed_ledger_tamper["detected"],
            "newer_uncheckpointed_tail_explicitly_visible": tail["status"] == "PASS_WITH_UNCHECKPOINTED_TAIL",
        },
        "claims_boundary": [
            "This is an internal, single-host reproducibility test using exported files and an independently supplied anchor file.",
            "The offline evaluator requires no private signing key and no running SARA service.",
            "Rollback resistance depends on retaining the external anchor in a trust boundary independent of local SARA audit/checkpoint storage.",
            "This does not establish WORM retention, a public transparency log, third-party attestation, signing-key non-compromise, CMMC/NIST/SPRS assessment, classified authorization, or operational deployment.",
        ],
    }
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
