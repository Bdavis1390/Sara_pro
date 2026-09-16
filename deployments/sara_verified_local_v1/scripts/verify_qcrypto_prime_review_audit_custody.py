#!/usr/bin/env python3
"""Persist and reconstruct one PRIME/QCRYPTO review warrant in native SARA audit custody."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from worldshepherd_sara.event_outbox import drain_event_outbox, outbox_status
from worldshepherd_sara.qcrypto_audit_adapter import (
    new_qcrypto_audit_instance_id,
    qcrypto_decision_digest,
    queue_qcrypto_projection_patch,
)
from worldshepherd_sara.qcrypto_audit_verifier import verify_qcrypto_audit_chain
from worldshepherd_sara.qcrypto_prime_review_adapter import prime_governed_review_projection
from worldshepherd_sara.storage import DurableStore


CUSTODY_SCHEMA = "WS-QCRYPTO-PRIME-REVIEW-SARA-AUDIT-CUSTODY-V1"


def _digest(value) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return sha256(canonical).hexdigest()


def _read_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("review evidence must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--output", default="prime-review-sara-audit-custody.json")
    parser.add_argument("--actor", default="SSPADAWANZZ")
    args = parser.parse_args()

    review = _read_json(args.review)
    projection = prime_governed_review_projection(review)
    decision_digest = qcrypto_decision_digest(projection)
    audit_instance_id = new_qcrypto_audit_instance_id()

    with tempfile.TemporaryDirectory(prefix="ws-qcrypto-prime-review-") as tempdir:
        store = DurableStore(Path(tempdir) / "data")

        def operation(registry):
            patch, ids = queue_qcrypto_projection_patch(
                registry,
                projection,
                actor=args.actor,
                audit_instance_id=audit_instance_id,
            )
            return patch, ids

        event_ids = store.transact_registry(operation)
        before = outbox_status(store.get_registry())
        delivered = drain_event_outbox(store, limit=4)
        after = outbox_status(store.get_registry())
        records = [
            item
            for item in store.read_audit(100)
            if isinstance(item, dict)
            and isinstance(item.get("payload"), dict)
            and item["payload"].get("audit_instance_id") == audit_instance_id
        ]
        verification = verify_qcrypto_audit_chain(
            records,
            decision_digest=decision_digest,
            audit_instance_id=audit_instance_id,
        )

    review_package_sha256 = review["summary"]["review_package_sha256"]
    correlation_id = projection["correlation_id"]
    if before != {"pending": 4, "delivered_retained": 0, "malformed": 0}:
        raise SystemExit(f"unexpected pre-drain outbox state: {before}")
    if delivered != 4:
        raise SystemExit(f"expected four delivered audit events, got {delivered}")
    if after.get("pending") != 0:
        raise SystemExit(f"audit outbox did not drain: {after}")
    if len(event_ids) != 4 or len(set(event_ids)) != 4:
        raise SystemExit("native SARA audit instance did not produce four stable event IDs")
    if not verification.complete or not verification.consistent:
        raise SystemExit(f"native SARA audit verification failed: {verification.verdict}")
    if verification.verdict != "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN":
        raise SystemExit(f"unexpected reconstruction verdict: {verification.verdict}")
    if tuple(verification.stages_present) != ("ECHO", "PRIME", "SARA", "OVERWATCH"):
        raise SystemExit("native SARA audit chain did not contain all four governed stages")
    if any(
        item["payload"].get("correlation_id") != correlation_id
        for item in records
    ):
        raise SystemExit("review correlation digest was not preserved across all audit stages")
    for item in records:
        payload = item["payload"]
        if payload.get("human_approval_required") is not True:
            raise SystemExit("audit custody lost the human approval boundary")
        for field in (
            "migration_executed",
            "execution_authority",
            "live_value_authorized",
            "federal_compliance_established",
            "ws_cae_conformance_established",
        ):
            if payload.get(field) is not False:
                raise SystemExit(f"audit custody illegally promoted {field}")
        if payload.get("_delivery_semantics") != "AT_LEAST_ONCE":
            raise SystemExit("native SARA at-least-once delivery semantics were not retained")

    evidence = {
        "schema": CUSTODY_SCHEMA,
        "status": "PASS",
        "claim_state": "PRIME_GOVERNED_REVIEW_WARRANT_RECONSTRUCTED_IN_NATIVE_SARA_AUDIT",
        "proof_scope": "DURABLE_INTERNAL_AUDIT_CUSTODY_NO_EXECUTION_AUTHORITY",
        "review_package_sha256": review_package_sha256,
        "source_review_evidence_sha256": review["evidence_sha256"],
        "correlation_id": correlation_id,
        "decision_digest": decision_digest,
        "audit_instance_id": audit_instance_id,
        "outbox_event_ids": event_ids,
        "outbox_before_drain": before,
        "outbox_after_drain": after,
        "delivered_event_count": delivered,
        "verification": verification.to_dict(),
        "projection": projection,
        "summary": {
            "four_stage_chain_reconstructed": True,
            "stages": list(verification.stages_present),
            "stable_outbox_event_id_count": len(set(event_ids)),
            "at_least_once_delivery_preserved": True,
            "review_correlation_preserved": True,
            "human_approval_required": True,
            "migration_executed": False,
            "execution_authority": False,
            "live_value_authorized": False,
            "federal_compliance_established": False,
            "ws_cae_conformance_established": False,
            "production_protocol_integration": False,
            "end_to_end_pq_security_established": False,
        },
    }
    evidence["evidence_sha256"] = _digest(evidence)
    Path(args.output).write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("prime_review_sara_audit_custody_status: PASS")
    print("decision_digest:", decision_digest)
    print("audit_instance_id:", audit_instance_id)
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
