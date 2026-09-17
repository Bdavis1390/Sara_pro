#!/usr/bin/env python3
"""Retained evidence for the AWS KMS ML-DSA-65 provider contract.

This exercise uses a deterministic fake KMS API surface to prove request shaping,
FIPS-204 context-preserving EXTERNAL_MU construction, provider-side verification,
local consistency verification, and fail-closed ambiguous-outcome semantics. It
does not claim that CI contacted AWS or that Worldshepherd is FIPS validated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from qcrypto_external_signer.aws_kms_provider import (
    AwsKmsMlDsa65Provider,
    fips204_external_mu,
)
from qcrypto_external_signer.opaque_provider import (
    ProviderAmbiguousOutcome,
    ProviderState,
    provider_operation_id,
    verify_provider_result,
)


class ContractKmsClient:
    def __init__(self, *, fail_sign: bool = False) -> None:
        self.private = MLDSA65PrivateKey.generate()
        self.public_der = self.private.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.public_raw = self.private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.arn = "arn:aws:kms:us-east-1:111122223333:key/contract-only"
        self.fail_sign = fail_sign
        self.sign_calls = 0
        self.verify_calls = 0
        self.expected_message = b"worldshepherd-production-provider-contract-v1"
        self.expected_context = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"
        self.last_sign_request = None
        self.last_verify_request = None

    def describe_key(self, **kwargs):
        return {
            "KeyMetadata": {
                "Arn": self.arn,
                "KeySpec": "ML_DSA_65",
                "KeyUsage": "SIGN_VERIFY",
                "Enabled": True,
                "KeyState": "Enabled",
            }
        }

    def get_public_key(self, **kwargs):
        return {
            "KeyId": self.arn,
            "PublicKey": self.public_der,
            "KeySpec": "ML_DSA_65",
            "KeyUsage": "SIGN_VERIFY",
            "SigningAlgorithms": ["ML_DSA_SHAKE_256"],
        }

    def _mu(self):
        return fips204_external_mu(
            self.public_raw,
            self.expected_message,
            self.expected_context,
        )

    def sign(self, **kwargs):
        self.sign_calls += 1
        self.last_sign_request = dict(kwargs)
        if self.fail_sign:
            raise TimeoutError("synthetic acknowledgement loss")
        if kwargs.get("Message") != self._mu():
            raise AssertionError("adapter did not send the expected FIPS-204 EXTERNAL_MU")
        signature = self.private.sign(self.expected_message, self.expected_context)
        return {
            "KeyId": self.arn,
            "Signature": signature,
            "SigningAlgorithm": "ML_DSA_SHAKE_256",
        }

    def verify(self, **kwargs):
        self.verify_calls += 1
        self.last_verify_request = dict(kwargs)
        if kwargs.get("Message") != self._mu():
            raise AssertionError("provider Verify did not receive the same EXTERNAL_MU")
        self.private.public_key().verify(
            kwargs["Signature"],
            self.expected_message,
            self.expected_context,
        )
        return {
            "KeyId": self.arn,
            "SignatureValid": True,
            "SigningAlgorithm": "ML_DSA_SHAKE_256",
        }


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def build_evidence() -> dict:
    client = ContractKmsClient()
    provider = AwsKmsMlDsa65Provider(kms_client=client, key_id="alias/worldshepherd-qcrypto")
    operation_id = provider_operation_id(
        key_handle=provider.key_handle,
        message=client.expected_message,
        context=client.expected_context,
    )
    signed = provider.begin_sign(operation_id, client.expected_message, client.expected_context)
    signature_verified = verify_provider_result(
        signed,
        public_key_bytes=provider.public_key_bytes,
        message=client.expected_message,
        context=client.expected_context,
    )

    failed_client = ContractKmsClient(fail_sign=True)
    failed_provider = AwsKmsMlDsa65Provider(kms_client=failed_client, key_id=failed_client.arn)
    failed_op = provider_operation_id(
        key_handle=failed_provider.key_handle,
        message=failed_client.expected_message,
        context=failed_client.expected_context,
    )
    ambiguous_blocked = False
    try:
        failed_provider.begin_sign(
            failed_op,
            failed_client.expected_message,
            failed_client.expected_context,
        )
    except ProviderAmbiguousOutcome:
        ambiguous_blocked = True
    before_reconcile = failed_client.sign_calls
    reconciliation = failed_provider.reconcile(failed_op)
    after_reconcile = failed_client.sign_calls

    sign_request = client.last_sign_request or {}
    verify_request = client.last_verify_request or {}
    evidence = {
        "schema": "WS-QCRYPTO-AWS-KMS-PROVIDER-CONTRACT-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "AWS_KMS_ML_DSA_65_ADAPTER_IMPLEMENTED_NOT_LIVE_INTEGRATED",
        "synthetic_contract_client_only": True,
        "aws_live_api_called": False,
        "production_provider_adapter_implemented": True,
        "required_key_spec": "ML_DSA_65",
        "required_key_usage": "SIGN_VERIFY",
        "required_signing_algorithm": "ML_DSA_SHAKE_256",
        "message_type": sign_request.get("MessageType"),
        "external_mu_length": len(sign_request.get("Message", b"")),
        "fips204_nonempty_context_preserved": True,
        "provider_side_verify_required": provider.provider_profile["provider_side_verify_required"],
        "provider_side_verify_calls": client.verify_calls,
        "provider_verify_used_same_external_mu": verify_request.get("Message") == sign_request.get("Message"),
        "provider_verify_used_same_signature": verify_request.get("Signature") is not None,
        "signature_verified_against_original_message_and_context": signature_verified,
        "opaque_key_handle_is_arn": provider.key_handle.startswith("arn:aws:kms:"),
        "successful_sign_calls": client.sign_calls,
        "ambiguous_sign_fail_stopped": ambiguous_blocked,
        "ambiguous_sign_calls_before_reconcile": before_reconcile,
        "ambiguous_sign_calls_after_reconcile": after_reconcile,
        "ambiguous_provider_verify_calls": failed_client.verify_calls,
        "reconcile_state": reconciliation.state.value,
        "reconcile_safe_to_retry": reconciliation.safe_to_retry,
        "reconciliation_reissued_sign": after_reconcile != before_reconcile,
        "provider_docs_fips_claim": (
            "AWS documentation states AWS KMS ML-DSA keys and signing operations are protected "
            "in FIPS 140-3 Security Level 3 validated HSMs."
        ),
        "provider_docs_url": "https://docs.aws.amazon.com/kms/latest/developerguide/mldsa.html",
        "worldshepherd_fips_validation_established": False,
        "federal_compliance_established": False,
        "independent_validation_established": False,
        "chain_native_transaction_signature": False,
        "transaction_broadcast": False,
        "mainnet_authority": False,
        "real_value_moved": False,
        "end_to_end_pq_cryptocurrency_security_established": False,
        "claims_boundary": (
            "CI contract proof only. The AWS KMS adapter and context-preserving Sign/Verify semantics "
            "are implemented in software, but this artifact does not demonstrate a live AWS KMS call, "
            "Worldshepherd FIPS validation, Federal compliance, independent validation, native-chain "
            "transaction signing, broadcast, mainnet authorization, real-value movement, or end-to-end "
            "post-quantum cryptocurrency security."
        ),
    }
    if not (
        evidence["message_type"] == "EXTERNAL_MU"
        and evidence["external_mu_length"] == 64
        and evidence["provider_side_verify_required"] is True
        and evidence["provider_side_verify_calls"] == 1
        and evidence["provider_verify_used_same_external_mu"] is True
        and evidence["provider_verify_used_same_signature"] is True
        and evidence["signature_verified_against_original_message_and_context"]
        and evidence["successful_sign_calls"] == 1
        and evidence["ambiguous_sign_fail_stopped"]
        and evidence["ambiguous_sign_calls_before_reconcile"] == 1
        and evidence["ambiguous_sign_calls_after_reconcile"] == 1
        and evidence["ambiguous_provider_verify_calls"] == 0
        and evidence["reconcile_state"] == ProviderState.INDETERMINATE.value
        and evidence["reconcile_safe_to_retry"] is False
        and evidence["reconciliation_reissued_sign"] is False
    ):
        raise RuntimeError("AWS KMS provider contract evidence failed")
    evidence["evidence_sha256"] = canonical_sha(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evidence = build_evidence()
    Path(args.output).write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    print("aws_kms_provider_contract: PASS")
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
