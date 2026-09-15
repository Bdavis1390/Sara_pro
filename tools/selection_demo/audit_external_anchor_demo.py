from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint import SaraAuditCheckpointManager
from worldshepherd_sara.audit_checkpoint_anchor import (
    SaraAuditExternalAnchorError,
    export_external_anchor,
    verify_with_external_anchor,
)
from worldshepherd_sara.audit_checkpoint_verify import (
    SaraAuditCheckpointVerificationError,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T14:{sequence:02d}:00+00:00",
            event="external_anchor_evidence",
            actor="admin_operator",
            payload={"sequence": sequence},
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--anchor-out", required=True)
    parser.add_argument("--software-commit", default="UNKNOWN")
    args = parser.parse_args()

    evidence_path = Path(args.out).resolve()
    anchor_path = Path(args.anchor_out).resolve()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_path.parent.mkdir(parents=True, exist_ok=True)

    key = Ed25519PrivateKey.generate()
    with tempfile.TemporaryDirectory(prefix="ws-sara-local-boundary-") as temp:
        local_root = Path(temp) / "sara-local-data"
        store = DurableStore(local_root)
        manager = SaraAuditCheckpointManager(
            store,
            private_key=key,
            key_id="SARA-AUDIT-EXTERNAL-ANCHOR-EVIDENCE-V1",
        )

        for sequence in range(1, 4):
            _append(store, sequence)
        first = manager.create_checkpoint()
        _append(store, 4)
        second = manager.create_checkpoint()

        anchor = export_external_anchor(manager, anchor_path)
        before = verify_with_external_anchor(manager, anchor_path)
        if before["status"] != "PASS":
            raise RuntimeError("external anchor did not verify before rollback attack")

        inside_boundary_rejected = False
        try:
            export_external_anchor(manager, (store.root / "not-external.json").resolve())
        except SaraAuditExternalAnchorError as exc:
            if "outside the SARA data directory" not in str(exc):
                raise
            inside_boundary_rejected = True
        if not inside_boundary_rejected:
            raise RuntimeError("anchor export inside SARA data boundary was not rejected")

        # Simulate local privileged rollback of the checkpoint ledger to a
        # still-valid earlier signed checkpoint. The independently retained
        # anchor remains outside the local SARA data directory.
        manager.ledger_path.write_text(
            json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        manager.ledger_path.chmod(0o600)

        rollback_detected = False
        rollback_error = ""
        try:
            verify_with_external_anchor(manager, anchor_path)
        except SaraAuditCheckpointVerificationError as exc:
            rollback_error = str(exc)
            if "rollback/latest-digest mismatch" not in rollback_error:
                raise
            rollback_detected = True
        if not rollback_detected:
            raise RuntimeError("external anchor did not detect local checkpoint rollback")

        result = {
            "schema": "WS-SARA-AUDIT-EXTERNAL-ANCHOR-EVIDENCE-V1",
            "result": "PASS",
            "software_commit": args.software_commit,
            "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "external_anchor": {
                "anchor_sha256": anchor["anchor_sha256"],
                "checkpoint_sha256": anchor["checkpoint_sha256"],
                "checkpoint_sequence": anchor["checkpoint_sequence"],
                "checkpoint_record_count": anchor["checkpoint_record_count"],
                "key_fingerprint_sha256": anchor["key_fingerprint_sha256"],
                "exported_outside_sara_data_dir": True,
            },
            "baseline_verification": before,
            "attack": {
                "type": "ROLL_BACK_LOCAL_CHECKPOINT_LEDGER_TO_PRIOR_VALID_SIGNED_CHECKPOINT",
                "rolled_back_to_checkpoint_sha256": first["checkpoint_sha256"],
                "externally_retained_latest_checkpoint_sha256": second["checkpoint_sha256"],
                "detected": rollback_detected,
                "error": rollback_error,
            },
            "acceptance_checks": {
                "latest_checkpoint_exported_outside_local_sara_boundary": True,
                "external_anchor_verified_before_attack": True,
                "export_inside_sara_data_boundary_rejected": inside_boundary_rejected,
                "local_checkpoint_rollback_detected_against_external_anchor": rollback_detected,
            },
            "claims_boundary": [
                "The CI artifact demonstrates an independently retained pin outside the temporary SARA data directory, not WORM storage.",
                "Repository/CI administrators may still delete or replace Actions artifacts; no transparency log or third-party attestation is claimed.",
                "Rollback resistance depends on trustworthy retention of the external anchor.",
                "Signing-key compromise remains outside the guarantee.",
                "No CUI/classified authorization, CMMC/NIST/SPRS assessment, government acceptance, or operational deployment is claimed."
            ],
        }

    evidence_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
