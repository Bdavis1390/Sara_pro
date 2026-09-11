#!/usr/bin/env python3
"""Merge normalized evaluation adapter outputs into one AGI gate result bundle.

The merger fails closed on system identity mismatches, conflicting metric values,
conflicting validity records, or duplicate evidence IDs. It performs no scoring;
ws_agi_gate.py remains the only promotion evaluator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return data


def _merge_unique(target: Dict[str, Any], source: Dict[str, Any], label: str) -> None:
    for key, value in source.items():
        if key in target and target[key] != value:
            raise ValueError(f"conflicting {label} for {key}: {target[key]!r} vs {value!r}")
        target[key] = value


def merge_adapters(
    adapters: Iterable[Dict[str, Any]],
    system_id: str,
    system_version: str,
    deployment_state: str = "BLOCKED",
) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    metric_validity: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []
    evidence_ids = set()
    adapter_schemas = []

    for index, adapter in enumerate(adapters):
        adapter_system_id = adapter.get("system_id")
        adapter_system_version = adapter.get("system_version")
        if adapter_system_id != system_id:
            raise ValueError(
                f"adapter {index} system_id mismatch: {adapter_system_id!r} != {system_id!r}"
            )
        if adapter_system_version != system_version:
            raise ValueError(
                "adapter "
                f"{index} system_version mismatch: {adapter_system_version!r} != {system_version!r}"
            )

        adapter_metrics = adapter.get("metrics", {})
        adapter_validity = adapter.get("metric_validity", {})
        adapter_evidence = adapter.get("evidence", [])
        if not isinstance(adapter_metrics, dict):
            raise ValueError(f"adapter {index} metrics must be an object")
        if not isinstance(adapter_validity, dict):
            raise ValueError(f"adapter {index} metric_validity must be an object")
        if not isinstance(adapter_evidence, list):
            raise ValueError(f"adapter {index} evidence must be an array")

        _merge_unique(metrics, adapter_metrics, "metric value")
        _merge_unique(metric_validity, adapter_validity, "metric validity")

        for record in adapter_evidence:
            if not isinstance(record, dict):
                raise ValueError(f"adapter {index} contains non-object evidence")
            evidence_id = record.get("evidence_id")
            if not evidence_id:
                raise ValueError(f"adapter {index} evidence missing evidence_id")
            if evidence_id in evidence_ids:
                raise ValueError(f"duplicate evidence_id across adapters: {evidence_id}")
            evidence_ids.add(evidence_id)
            evidence.append(record)

        adapter_schemas.append(adapter.get("schema", "UNKNOWN"))

    return {
        "schema": "WS-AGI-GATE-BUNDLE-V1.0",
        "system_id": system_id,
        "system_version": system_version,
        "deployment_state": deployment_state,
        "metrics": metrics,
        "metric_validity": metric_validity,
        "evidence": evidence,
        "source_adapter_schemas": adapter_schemas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Worldshepherd AGI adapter outputs")
    parser.add_argument("inputs", nargs="+", type=Path, help="Adapter output JSON files")
    parser.add_argument("--system-id", required=True)
    parser.add_argument("--system-version", required=True)
    parser.add_argument("--deployment-state", default="BLOCKED")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        adapters = [_load(path) for path in args.inputs]
        output = merge_adapters(
            adapters,
            system_id=args.system_id,
            system_version=args.system_version,
            deployment_state=args.deployment_state,
        )
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"AGI bundle merge error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
