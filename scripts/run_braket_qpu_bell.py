#!/usr/bin/env python3
"""Execute QRF-BELL-001 as one governed Amazon Braket on-demand QPU task.

This CLI never accepts AWS access-key or secret-key values. Configure AWS credentials
outside Worldshepherd using the normal AWS SDK credential chain or AWS_PROFILE.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_braket_task import (
    build_braket_task_external_evidence,
    execute_braket_bell_task,
    record_from_raw_payload,
)


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen QRF-BELL-001 on a named Amazon Braket QPU and retain governed evidence."
    )
    parser.add_argument("--device-arn", required=True, help="Exact Amazon Braket QPU device ARN")
    parser.add_argument("--s3-bucket", required=True, help="Existing Braket output S3 bucket")
    parser.add_argument("--s3-prefix", default="worldshepherd/qrf-bell-001", help="S3 output key prefix")
    parser.add_argument("--shots", type=int, default=1024, help="Shot count; default 1024")
    parser.add_argument(
        "--per-task-usd",
        type=float,
        required=True,
        help="Current official Braket per-task rate captured before submission",
    )
    parser.add_argument(
        "--per-shot-usd",
        type=float,
        required=True,
        help="Current official selected-device per-shot rate captured before submission",
    )
    parser.add_argument(
        "--pricing-source",
        default="https://aws.amazon.com/braket/pricing/",
        help="Source used for the predeclared pricing rates",
    )
    parser.add_argument("--aws-profile", help="Optional AWS profile name; never an access key or secret")
    parser.add_argument("--poll-timeout-seconds", type=int, default=86400)
    parser.add_argument("--project-id", default="SARA-QRF")
    parser.add_argument("--campaign-gate-id", default="SARA-QRF-EXT-01")
    parser.add_argument(
        "--benchmark",
        default="benchmarks/quantum/bell_qasm3.qasm",
        help="Canonical QRF-BELL-001 source used only for frozen program identity",
    )
    parser.add_argument("--output-dir", default=".qrf-external/braket-qrf-bell-001")
    args = parser.parse_args()

    if args.aws_profile:
        if any(token in args.aws_profile.lower() for token in ("secret", "access_key", "sk-")):
            raise SystemExit("--aws-profile must be a profile name, not credential material")
        os.environ["AWS_PROFILE"] = args.aws_profile

    benchmark_path = Path(args.benchmark)
    if not benchmark_path.is_file():
        raise SystemExit(f"canonical benchmark not found: {benchmark_path}")
    canonical_source = benchmark_path.read_text(encoding="utf-8")

    raw = execute_braket_bell_task(
        canonical_program_source=canonical_source,
        device_arn=args.device_arn,
        shots=args.shots,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        per_task_usd=args.per_task_usd,
        per_shot_usd=args.per_shot_usd,
        pricing_source=args.pricing_source,
        poll_timeout_seconds=args.poll_timeout_seconds,
    )

    output_dir = Path(args.output_dir)
    raw_path = output_dir / "braket_qrf_bell_001_raw_task.json"
    _write_json(raw_path, raw)
    raw_digest = _sha256_file(raw_path)

    record = record_from_raw_payload(raw, result_artifact_digest=raw_digest)
    evidence = build_braket_task_external_evidence(
        record,
        project_id=args.project_id,
        campaign_gate_id=args.campaign_gate_id,
    )

    record_path = output_dir / "braket_qrf_bell_001_task_record.json"
    evidence_path = output_dir / "braket_qrf_bell_001_external_evidence.json"
    _write_json(record_path, asdict(record))
    _write_json(evidence_path, asdict(evidence))

    print(f"task_arn={record.quantum_task_arn}")
    print(f"device_arn={record.device_arn}")
    print(f"provider={record.provider}")
    print(f"shots={record.shots_successful}/{record.shots_requested}")
    print(f"raw_artifact={raw_path}")
    print(f"raw_artifact_digest={raw_digest}")
    print(f"task_record={record_path}")
    print(f"external_evidence={evidence_path}")
    print(f"cost_usd_predeclared_estimate={record.cost_usd:.8f}")
    print("claim_control=hardware execution is not readiness promotion; complete governed ingest and identified-human review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
