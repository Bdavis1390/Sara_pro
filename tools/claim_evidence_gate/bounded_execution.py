"""Bounded synthetic execution/custody demonstrator (not independent attestation).

A fixed affine transform consumes precisely the configuration bytes whose digest
is recorded in its self-reported receipt. No arbitrary shell commands or plugins.
Verification recomputes outputs from the recorded files; receipts are NOT signed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RECEIPT_SCHEMA = "WS-BOUNDED-EXECUTION-RECEIPT-V1"
OUTPUT_SCHEMA = "WS-AFFINE-SYNTHETIC-OUTPUT-V1"
ENGINE_ID = "ws-bounded-affine-0.1"
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
RUN_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
MAX_BYTES = 65536


class ExecutionCustodyError(ValueError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_bounded(root: Path, relative: str) -> bytes:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ExecutionCustodyError("invalid relative path")
    rel = Path(relative)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in relative.split("/")):
        raise ExecutionCustodyError("noncanonical or traversing path")
    base = root.resolve(strict=True)
    path = base
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ExecutionCustodyError("symlink rejected")
    if not path.is_file() or not path.resolve(strict=True).is_relative_to(base):
        raise ExecutionCustodyError("not a confined regular file")
    if path.stat().st_size > MAX_BYTES:
        raise ExecutionCustodyError("input exceeds size limit")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ExecutionCustodyError("input exceeds size limit")
    return raw


def parse_object(raw: bytes) -> dict:
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutionCustodyError("invalid JSON") from exc
    if not isinstance(result, dict):
        raise ExecutionCustodyError("expected JSON object")
    return result


def calculated_output(config_bytes: bytes, input_bytes: bytes) -> bytes:
    """The calculation consumes the same in-memory bytes that will be hashed."""
    config, values = parse_object(config_bytes), parse_object(input_bytes)
    if set(config) != {"operation", "scale", "offset"} or config["operation"] != "affine_v1":
        raise ExecutionCustodyError("unsupported synthetic operation")
    scale, offset = config["scale"], config["offset"]
    if any(type(v) is not int or abs(v) > 1000 for v in (scale, offset)):
        raise ExecutionCustodyError("invalid coefficients")
    if set(values) != {"samples"} or not isinstance(values["samples"], list):
        raise ExecutionCustodyError("invalid input schema")
    samples = values["samples"]
    if not 1 <= len(samples) <= 128 or any(type(v) is not int or abs(v) > 1000000 for v in samples):
        raise ExecutionCustodyError("invalid bounded sample array")
    output = {"schema": OUTPUT_SCHEMA, "samples": [scale * v + offset for v in samples]}
    return canonical(output) + b"\n"


def receipt_digest(fields: dict) -> str:
    return sha256(canonical(fields))


def run_bounded(root: Path, config_path: str, input_path: str, run_id: str) -> dict:
    """Create a local receipt from a fixed, sandboxable synthetic calculation.

    The process reads each input exactly once, hashes those bytes, and passes the
    identical byte objects into the calculation. This is software instrumentation,
    not an independently observed execution or trustworthy timestamp.
    """
    if not isinstance(run_id, str) or not RUN_PATTERN.fullmatch(run_id):
        raise ExecutionCustodyError("invalid run ID")
    root = Path(root)
    config_raw = read_bounded(root, config_path)
    input_raw = read_bounded(root, input_path)
    output_raw = calculated_output(config_raw, input_raw)
    output_rel = f"runs/{run_id}.output.json"
    receipt_rel = f"runs/{run_id}.receipt.json"
    directory = root.resolve(strict=True) / "runs"
    if directory.is_symlink():
        raise ExecutionCustodyError("symlinked run directory")
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink():
        raise ExecutionCustodyError("symlinked run directory")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "run_id": run_id,
        "engine": ENGINE_ID,
        "configuration": {"path": config_path, "sha256": sha256(config_raw)},
        "input": {"path": input_path, "sha256": sha256(input_raw)},
        "output": {"path": output_rel, "sha256": sha256(output_raw)},
        "source_sha256": sha256(Path(__file__).read_bytes()),
        "runtime": {"python": list(sys.version_info[:3])},
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "self_reported": True,
        "independent_witness": False,
    }
    receipt["receipt_sha256"] = receipt_digest(receipt)
    with (directory / f"{run_id}.output.json").open("xb") as file:
        file.write(output_raw)
    with (directory / f"{run_id}.receipt.json").open("xb") as file:
        file.write(canonical(receipt) + b"\n")
    return receipt


def verify_receipt(root: Path, receipt: dict) -> dict:
    """Verify local record consistency and reproduce the fixed computation."""
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise ExecutionCustodyError("unknown receipt schema")
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not RUN_PATTERN.fullmatch(run_id):
        raise ExecutionCustodyError("invalid recorded run ID")
    if receipt.get("engine") != ENGINE_ID or receipt.get("self_reported") is not True:
        raise ExecutionCustodyError("unknown engine or receipt provenance")
    if receipt.get("independent_witness") is not False:
        raise ExecutionCustodyError("self-reported receipt cannot claim external witnessing")
    fingerprint = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if not isinstance(fingerprint, str) or not SHA_PATTERN.fullmatch(fingerprint) or receipt_digest(body) != fingerprint:
        raise ExecutionCustodyError("receipt digest mismatch")
    claimed = {}
    for field in ("configuration", "input", "output"):
        desc = receipt.get(field)
        if not isinstance(desc, dict) or set(desc) != {"path", "sha256"}:
            raise ExecutionCustodyError(f"invalid {field} descriptor")
        if not isinstance(desc["sha256"], str) or not SHA_PATTERN.fullmatch(desc["sha256"]):
            raise ExecutionCustodyError(f"invalid {field} digest")
        raw = read_bounded(Path(root), desc["path"])
        if sha256(raw) != desc["sha256"]:
            raise ExecutionCustodyError(f"{field} bytes altered")
        claimed[field] = raw
    if receipt["output"]["path"] != f"runs/{run_id}.output.json":
        raise ExecutionCustodyError("output path does not match run ID")
    expected = calculated_output(claimed["configuration"], claimed["input"])
    if claimed["output"] != expected:
        raise ExecutionCustodyError("synthetic output inconsistent with claimed inputs")
    recorded_source = receipt.get("source_sha256")
    if not isinstance(recorded_source, str) or not SHA_PATTERN.fullmatch(recorded_source):
        raise ExecutionCustodyError("missing source identity")
    if recorded_source != sha256(Path(__file__).read_bytes()):
        raise ExecutionCustodyError("verifier source does not match recorded runner identity")
    return {
        "schema": "WS-BOUNDED-EXECUTION-VERIFICATION-V1",
        "status": "PASS",
        "run_id": run_id,
        "configuration_bytes_recomputed": True,
        "input_bytes_recomputed": True,
        "output_bytes_recomputed": True,
        "engine_source_matches_local_verifier": True,
        "independent_process_attestation": False,
        "independent_witness_verified": False,
        "preexecution_freeze_verified": False,
        "claims_boundary": "Local reproducible, self-reported synthetic process instrumentation only; no independent runtime identity, external timestamp, signed witness, or physical-science validation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    runner = subs.add_parser("run")
    runner.add_argument("--root", required=True)
    runner.add_argument("--config", required=True)
    runner.add_argument("--input", required=True)
    runner.add_argument("--run-id", required=True)
    verifier = subs.add_parser("verify")
    verifier.add_argument("--root", required=True)
    verifier.add_argument("--receipt", required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            result = run_bounded(Path(args.root), args.config, args.input, args.run_id)
        else:
            result = verify_receipt(
                Path(args.root),
                parse_object(read_bounded(Path(args.root), args.receipt)),
            )
    except (ExecutionCustodyError, OSError, ValueError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
