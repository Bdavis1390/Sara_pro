from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from model import FlexRequest
from trace import TracePoint, verify_trace


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def replay_payload(payload: dict) -> dict:
    request = FlexRequest(**payload["request"])
    points = [TracePoint(**point) for point in payload["points"]]
    result = verify_trace(
        request,
        float(payload["baseline_mw"]),
        points,
        authorized=bool(payload.get("authorized", True)),
        source_identity_valid=bool(payload.get("source_identity_valid", True)),
        authorization_evidence_valid=bool(
            payload.get("authorization_evidence_valid", True)
        ),
        request_provenance_valid=bool(payload.get("request_provenance_valid", True)),
        baseline_valid=bool(payload.get("baseline_valid", True)),
        clocks_synchronized=bool(payload.get("clocks_synchronized", True)),
        configuration_custody_valid=bool(
            payload.get("configuration_custody_valid", True)
        ),
        max_gap_s=float(payload.get("max_gap_s", 300.0)),
        energy_mismatch_tolerance_mwh=float(
            payload.get("energy_mismatch_tolerance_mwh", 0.25)
        ),
    )
    output = asdict(result)
    output["verdict"] = result.verdict.value
    output["reasons"] = list(result.reasons)
    output["input_sha256"] = _canonical_sha256(payload)
    output["trace_sha256"] = _canonical_sha256(payload["points"])
    output["provenance"] = payload.get("provenance")
    output["auxiliary_evidence"] = payload.get("auxiliary_evidence")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a WS-DCAR FLEX-001 trace")
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.trace.read_text(encoding="utf-8"))
    print(json.dumps(replay_payload(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
