from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint import (
    SaraAuditCheckpointError,
    SaraAuditCheckpointManager,
)
from worldshepherd_sara.audit_checkpoint_verify import (
    SaraAuditCheckpointVerificationError,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T12:{sequence:02d}:00+00:00",
            event="audit_checkpoint_evidence",
            actor="admin_operator",
            payload={"sequence": sequence, "value": f"VALUE-{sequence}"},
        )
    )


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _rewrite(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    path.chmod(0o600)


def _case(
    *,
    name: str,
    source_dir: Path,
    key: Ed25519PrivateKey,
    key_id: str,
    mutate: Callable[[DurableStore, SaraAuditCheckpointManager], None],
    expected_exception: type[Exception],
    match_text: str,
    expected_pin: str | None = None,
) -> dict:
    target = source_dir.parent / f"case-{name}"
    shutil.copytree(source_dir, target)
    store = DurableStore(target)
    manager = SaraAuditCheckpointManager(store, private_key=key, key_id=key_id)
    mutate(store, manager)
    try:
        manager.verify_current(expected_latest_checkpoint_sha256=expected_pin)
    except expected_exception as exc:
        if match_text not in str(exc):
            raise RuntimeError(
                f"{name}: expected error containing {match_text!r}, got {exc!r}"
            ) from exc
        return {"case": name, "detected": True, "error": str(exc)}
    raise RuntimeError(f"{name}: tampering was not detected")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default="UNKNOWN")
    args = parser.parse_args()

    key = Ed25519PrivateKey.generate()
    key_id = "SARA-AUDIT-EVIDENCE-V1"
    with tempfile.TemporaryDirectory(prefix="ws-audit-checkpoint-") as temp:
        root = Path(temp)
        source = root / "source"
        store = DurableStore(source)
        manager = SaraAuditCheckpointManager(store, private_key=key, key_id=key_id)
        for sequence in range(1, 5):
            _append(store, sequence)
        first = manager.create_checkpoint()
        exact = manager.verify_current()
        if exact["status"] != "PASS":
            raise RuntimeError("exact checkpoint verification did not pass")

        _append(store, 5)
        tail = manager.verify_current()
        if tail["status"] != "PASS_WITH_UNCHECKPOINTED_TAIL":
            raise RuntimeError("uncheckpointed tail was not surfaced")
        second = manager.create_checkpoint()
        pinned = manager.verify_current(
            expected_latest_checkpoint_sha256=second["checkpoint_sha256"]
        )
        if pinned["status"] != "PASS":
            raise RuntimeError("pinned latest checkpoint verification did not pass")

        sealed_source = root / "sealed"
        shutil.copytree(source, sealed_source)

        def mutate_content(case_store, _manager):
            rows = _rows(case_store.audit_path)
            rows[1]["payload"]["value"] = "ATTACKER-EDIT"
            _rewrite(case_store.audit_path, rows)

        def reorder(case_store, _manager):
            rows = _rows(case_store.audit_path)
            rows[0], rows[1] = rows[1], rows[0]
            _rewrite(case_store.audit_path, rows)

        def truncate(case_store, _manager):
            rows = _rows(case_store.audit_path)
            _rewrite(case_store.audit_path, rows[:-1])

        def rollback_checkpoint(_store, case_manager):
            case_manager.ledger_path.write_text(
                json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            case_manager.ledger_path.chmod(0o600)

        cases = [
            _case(
                name="historical-content-mutation",
                source_dir=sealed_source,
                key=key,
                key_id=key_id,
                mutate=mutate_content,
                expected_exception=SaraAuditCheckpointError,
                match_text="prefix integrity mismatch",
            ),
            _case(
                name="historical-record-reordering",
                source_dir=sealed_source,
                key=key,
                key_id=key_id,
                mutate=reorder,
                expected_exception=SaraAuditCheckpointError,
                match_text="prefix integrity mismatch",
            ),
            _case(
                name="checkpointed-tail-truncation",
                source_dir=sealed_source,
                key=key,
                key_id=key_id,
                mutate=truncate,
                expected_exception=SaraAuditCheckpointError,
                match_text="truncation detected",
            ),
            _case(
                name="local-checkpoint-ledger-rollback-with-external-pin",
                source_dir=sealed_source,
                key=key,
                key_id=key_id,
                mutate=rollback_checkpoint,
                expected_exception=SaraAuditCheckpointVerificationError,
                match_text="rollback/latest-digest mismatch",
                expected_pin=second["checkpoint_sha256"],
            ),
        ]

        result = {
            "schema": "WS-SARA-AUDIT-CHECKPOINT-ADVERSARIAL-EVIDENCE-V1",
            "result": "PASS",
            "software_commit": args.software_commit,
            "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "baseline": {
                "checkpoint_1_records": first["manifest"]["record_count"],
                "checkpoint_2_records": second["manifest"]["record_count"],
                "exact_checkpoint_status": exact["status"],
                "uncheckpointed_tail_status": tail["status"],
                "pinned_latest_status": pinned["status"],
                "latest_checkpoint_sha256": second["checkpoint_sha256"],
                "key_fingerprint_sha256": manager.fingerprint_sha256,
            },
            "adversarial_cases": cases,
            "acceptance_checks": {
                "signed_exact_prefix_verifies": True,
                "uncheckpointed_tail_is_visible": True,
                "historical_content_mutation_detected": True,
                "historical_reordering_detected": True,
                "checkpointed_truncation_detected": True,
                "externally_pinned_checkpoint_rollback_detected": True,
            },
            "claims_boundary": [
                "Internal local software evidence only.",
                "The signed checkpoint protects only the checkpointed SARA audit prefix.",
                "A newer uncheckpointed tail is surfaced but is not cryptographically covered by the older checkpoint.",
                "Local rollback of both audit and checkpoint evidence cannot be proven stale without a separately retained expected latest checkpoint digest or external anchor.",
                "Compromise of the signing key or signer is outside this guarantee.",
                "No WORM retention, external attestation, CUI/classified authorization, or government acceptance is claimed."
            ],
        }

    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
