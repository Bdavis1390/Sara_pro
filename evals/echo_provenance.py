#!/usr/bin/env python3
"""Emit a deterministic, hash-chained provenance stream for AGI evaluation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def chain_record(sequence: int, previous_hash: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    material = {
        "sequence": sequence,
        "previous_hash": previous_hash,
        "payload": payload,
    }
    record_hash = hashlib.sha256(canonical(material)).hexdigest()
    return {**material, "record_hash": f"sha256:{record_hash}"}


def build_chain(bundle: Dict[str, Any], gate_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = bundle.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("bundle.evidence must be an array")

    system_id = bundle.get("system_id") or gate_output.get("system_id")
    if not system_id:
        raise ValueError("system_id is required")

    payloads: List[Dict[str, Any]] = [{
        "event_type": "AGI_GATE_EVALUATION",
        "system_id": system_id,
        "system_version": bundle.get("system_version", "UNKNOWN"),
        "intelligence_state": gate_output.get("intelligence_state", "UNKNOWN"),
        "prime_policy": gate_output.get("prime_policy", {}),
        "gate_config_schema": gate_output.get("gate_config_schema"),
    }]

    for record in evidence:
        if not isinstance(record, dict):
            raise ValueError("every evidence record must be an object")
        evidence_id = record.get("evidence_id")
        if not evidence_id:
            raise ValueError("every evidence record must contain evidence_id")
        payloads.append({
            "event_type": "AGI_EVIDENCE",
            "system_id": system_id,
            "evidence_id": evidence_id,
            "metric_names": record.get("metric_names", []),
            "source_or_artifact_hash": record.get("source_or_artifact_hash"),
            "task_hash": record.get("task_hash"),
            "grader_version": record.get("grader_version"),
            "claim_state": record.get("claim_state"),
            "evaluation_date": record.get("evaluation_date"),
        })

    previous = "GENESIS"
    output = []
    for sequence, payload in enumerate(payloads):
        record = chain_record(sequence, previous, payload)
        output.append(record)
        previous = record["record_hash"]
    return output


def verify_chain(records: Iterable[Dict[str, Any]]) -> bool:
    previous = "GENESIS"
    for expected_sequence, record in enumerate(records):
        material = {
            "sequence": record.get("sequence"),
            "previous_hash": record.get("previous_hash"),
            "payload": record.get("payload"),
        }
        digest = "sha256:" + hashlib.sha256(canonical(material)).hexdigest()
        if record.get("sequence") != expected_sequence:
            return False
        if record.get("previous_hash") != previous:
            return False
        if record.get("record_hash") != digest:
            return False
        previous = digest
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Export hash-chained AGI evaluation provenance")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("gate_output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        records = build_chain(load_json(args.bundle), load_json(args.gate_output))
        if args.verify and not verify_chain(records):
            raise ValueError("generated provenance chain failed verification")
        for record in records:
            print(json.dumps(record, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Provenance export error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
