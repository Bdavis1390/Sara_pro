#!/usr/bin/env python3
"""Generate bounded ML-DSA-65 ECHO checkpoint lab evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from worldshepherd_sara.echo_checkpoint_mldsa_lab import OpenSslMlDsa65LabSigner


def canonical_payload() -> bytes:
    body = {
        "schema": "WS-ECHO-CHECKPOINT-MLDSA-LAB-PAYLOAD-V1",
        "issuer": "ECHO_SENTINEL_LINK",
        "sequence": 1,
        "event_count": 4,
        "merkle_root_sha256": "1" * 64,
        "previous_checkpoint_sha256": None,
        "claims_boundary": "CONTROLLED_LAB_ONLY",
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openssl", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    signer = OpenSslMlDsa65LabSigner(
        openssl_path=args.openssl,
        private_key_path=args.private_key,
        lab_mode=True,
    )
    payload = canonical_payload()
    exercise = signer.exercise(payload).to_dict()
    if exercise["verified"] is not True or exercise["tamper_rejected"] is not True:
        raise SystemExit("ML-DSA controlled-lab sign/verify exercise failed")
    if exercise["production_authorized"] is not False:
        raise SystemExit("lab evidence improperly promoted production authorization")
    if exercise["fips_module_validation_established"] is not False:
        raise SystemExit("lab evidence improperly promoted FIPS module validation")

    evidence = {
        "schema": "WS-ECHO-MLDSA65-CONTROLLED-LAB-EVIDENCE-V1",
        "status": "PASS",
        "exercise": exercise,
        "payload_length": len(payload),
        "private_key_in_artifact": False,
        "runtime_integration_enabled": False,
        "production_checkpoint_signing_ready": False,
        "end_to_end_pq_security_established": False,
        "claim_boundary": (
            "Real ML-DSA-65 sign/verify interoperability was exercised in a controlled lab "
            "using an external OpenSSL provider. This does not establish production ECHO "
            "integration, FIPS 140 module validation, Federal compliance, live-value authority, "
            "or end-to-end post-quantum security."
        ),
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
