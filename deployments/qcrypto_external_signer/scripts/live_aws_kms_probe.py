#!/usr/bin/env python3
"""Opt-in live AWS KMS ML-DSA-65 integration probe.

This script signs only a fixed Worldshepherd attestation test message. It does not
construct or sign a blockchain transaction, broadcast to any network, enable
mainnet authority, or move value. AWS credentials are obtained only through the
normal boto3 credential chain and are never accepted as command-line arguments or
written to the evidence artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from qcrypto_external_signer.aws_kms_provider import AwsKmsMlDsa65Provider
from qcrypto_external_signer.opaque_provider import provider_operation_id, verify_provider_result

_PROBE_CONTEXT = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"
_PROBE_MESSAGE = b"WS-QCRYPTO-LIVE-AWS-KMS-INTEGRATION-PROBE-V1-NON-TRANSACTION"


def _canonical_sha(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-id", required=True, help="AWS KMS ML_DSA_65 key ARN, UUID, or alias")
    parser.add_argument("--region", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("install the optional AWS dependency with: pip install -e '.[aws]'") from exc

    kms = boto3.client("kms", region_name=args.region)
    provider = AwsKmsMlDsa65Provider(kms_client=kms, key_id=args.key_id)
    operation_id = provider_operation_id(
        key_handle=provider.key_handle,
        message=_PROBE_MESSAGE,
        context=_PROBE_CONTEXT,
    )
    result = provider.begin_sign(operation_id, _PROBE_MESSAGE, _PROBE_CONTEXT)
    verified = verify_provider_result(
        result,
        public_key_bytes=provider.public_key_bytes,
        message=_PROBE_MESSAGE,
        context=_PROBE_CONTEXT,
    )
    if not verified:
        raise SystemExit("live AWS KMS signature did not verify locally")

    evidence = {
        "schema": "WS-QCRYPTO-LIVE-AWS-KMS-INTEGRATION-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "LIVE_AWS_KMS_ML_DSA_65_PROVIDER_CALL_OBSERVED",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "aws_live_api_called": True,
        "non_transaction_probe_only": True,
        "key_handle_sha256": hashlib.sha256(provider.key_handle.encode()).hexdigest(),
        "public_key_fingerprint_sha256": provider.fingerprint_sha256,
        "algorithm": provider.algorithm,
        "message_type": "EXTERNAL_MU",
        "signing_algorithm": "ML_DSA_SHAKE_256",
        "fips204_nonempty_context_preserved": True,
        "signature_verified_locally": True,
        "provider_documentation_fips_basis": (
            "AWS documents ML-DSA keys and signing operations in AWS KMS as protected by "
            "FIPS 140-3 Security Level 3 validated HSMs."
        ),
        "provider_documentation_url": "https://docs.aws.amazon.com/kms/latest/developerguide/mldsa.html",
        "worldshepherd_fips_validation_established": False,
        "federal_compliance_established": False,
        "independent_validation_established": False,
        "chain_native_transaction_signature": False,
        "transaction_broadcast": False,
        "mainnet_authority": False,
        "real_value_moved": False,
        "end_to_end_pq_cryptocurrency_security_established": False,
        "claims_boundary": (
            "A passing artifact establishes only that this Worldshepherd adapter successfully used a live "
            "AWS KMS ML-DSA-65 key for a non-transaction test signature and verified it locally. It does "
            "not make Worldshepherd a FIPS-validated product, establish Federal compliance or independent "
            "validation, authorize blockchain-native signing or broadcast, enable mainnet, move value, or "
            "establish end-to-end post-quantum security of Bitcoin or Ethereum."
        ),
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    Path(args.output).write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("live_aws_kms_probe: PASS")
    print("public_key_fingerprint_sha256:", evidence["public_key_fingerprint_sha256"])
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
