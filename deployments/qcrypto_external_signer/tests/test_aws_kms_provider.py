from __future__ import annotations

import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from qcrypto_external_signer.aws_kms_provider import (
    AwsKmsMlDsa65Provider,
    fips204_external_mu,
)
from qcrypto_external_signer.opaque_provider import (
    OpaqueProviderReleaseSigner,
    ProviderAmbiguousOutcome,
    ProviderError,
    ProviderState,
    provider_operation_id,
    verify_provider_result,
)


class FakeKms:
    def __init__(
        self,
        *,
        fail_sign: bool = False,
        fail_verify: bool = False,
        enabled: bool = True,
        key_spec: str = "ML_DSA_65",
    ):
        self.private = MLDSA65PrivateKey.generate()
        self.public_der = self.private.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.public_raw = self.private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.arn = "arn:aws:kms:us-east-1:111122223333:key/00000000-1111-2222-3333-444444444444"
        self.fail_sign = fail_sign
        self.fail_verify = fail_verify
        self.enabled = enabled
        self.key_spec = key_spec
        self.sign_calls = 0
        self.verify_calls = 0
        self.expected_message: bytes | None = None
        self.expected_context: bytes | None = None
        self.last_sign_request = None
        self.last_verify_request = None

    def describe_key(self, **kwargs):
        return {
            "KeyMetadata": {
                "Arn": self.arn,
                "KeySpec": self.key_spec,
                "KeyUsage": "SIGN_VERIFY",
                "Enabled": self.enabled,
                "KeyState": "Enabled" if self.enabled else "Disabled",
            }
        }

    def get_public_key(self, **kwargs):
        return {
            "KeyId": self.arn,
            "PublicKey": self.public_der,
            "KeySpec": self.key_spec,
            "KeyUsage": "SIGN_VERIFY",
            "SigningAlgorithms": ["ML_DSA_SHAKE_256"],
        }

    def _expected_mu(self):
        assert self.expected_message is not None
        assert self.expected_context is not None
        return fips204_external_mu(
            self.public_raw,
            self.expected_message,
            self.expected_context,
        )

    def sign(self, **kwargs):
        self.sign_calls += 1
        self.last_sign_request = dict(kwargs)
        if self.fail_sign:
            raise TimeoutError("simulated lost KMS acknowledgement")
        assert kwargs["Message"] == self._expected_mu()
        signature = self.private.sign(self.expected_message, self.expected_context)
        return {
            "KeyId": self.arn,
            "Signature": signature,
            "SigningAlgorithm": "ML_DSA_SHAKE_256",
        }

    def verify(self, **kwargs):
        self.verify_calls += 1
        self.last_verify_request = dict(kwargs)
        if self.fail_verify:
            raise TimeoutError("simulated KMS Verify failure")
        assert kwargs["Message"] == self._expected_mu()
        assert kwargs["MessageType"] == "EXTERNAL_MU"
        assert kwargs["SigningAlgorithm"] == "ML_DSA_SHAKE_256"
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


def test_external_mu_preserves_nonempty_fips204_context():
    private = MLDSA65PrivateKey.generate()
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    message = b"worldshepherd-kms-contract-message"
    context = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"

    tr = hashlib.shake_256(raw).digest(64)
    expected = hashlib.shake_256(
        tr + b"\x00" + bytes((len(context),)) + context + message
    ).digest(64)
    assert fips204_external_mu(raw, message, context) == expected
    assert len(expected) == 64


def test_kms_provider_sign_and_provider_verify_context_bound_signature():
    kms = FakeKms()
    provider = AwsKmsMlDsa65Provider(kms_client=kms, key_id="alias/worldshepherd-qcrypto")
    signer = OpaqueProviderReleaseSigner(provider)
    message = b"canonical-custody-release-binding"
    context = signer.context
    kms.expected_message = message
    kms.expected_context = context
    operation_id = provider_operation_id(
        key_handle=provider.key_handle,
        message=message,
        context=context,
    )

    result = provider.begin_sign(operation_id, message, context)
    assert result.state is ProviderState.SIGNED
    assert kms.sign_calls == 1
    assert kms.verify_calls == 1
    assert provider.provider_verify_count == 1
    assert kms.last_sign_request["KeyId"] == kms.arn
    assert kms.last_sign_request["MessageType"] == "EXTERNAL_MU"
    assert kms.last_sign_request["SigningAlgorithm"] == "ML_DSA_SHAKE_256"
    assert len(kms.last_sign_request["Message"]) == 64
    assert kms.last_verify_request["Message"] == kms.last_sign_request["Message"]
    assert kms.last_verify_request["Signature"] == result_signature_bytes(result)
    assert verify_provider_result(
        result,
        public_key_bytes=provider.public_key_bytes,
        message=message,
        context=context,
    )
    assert provider.provider_profile["provider_side_verify_required"] is True
    assert provider.provider_profile["worldshepherd_fips_validation_established"] is False


def result_signature_bytes(result):
    import base64
    raw = result.signature_b64url.encode("ascii")
    return base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)


def test_kms_ambiguous_sign_never_auto_retries_or_reissues_on_reconcile():
    kms = FakeKms(fail_sign=True)
    provider = AwsKmsMlDsa65Provider(kms_client=kms, key_id=kms.arn)
    message = b"ambiguous-kms-release-binding"
    context = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"
    kms.expected_message = message
    kms.expected_context = context
    operation_id = provider_operation_id(
        key_handle=provider.key_handle,
        message=message,
        context=context,
    )

    with pytest.raises(ProviderAmbiguousOutcome):
        provider.begin_sign(operation_id, message, context)
    assert kms.sign_calls == 1
    assert kms.verify_calls == 0

    reconciled = provider.reconcile(operation_id)
    assert reconciled.state is ProviderState.INDETERMINATE
    assert reconciled.safe_to_retry is False
    assert kms.sign_calls == 1
    assert kms.verify_calls == 0

    with pytest.raises(ProviderAmbiguousOutcome):
        provider.begin_sign(operation_id, message, context)
    assert kms.sign_calls == 1


def test_kms_verify_failure_after_sign_is_indeterminate_and_never_resigns():
    kms = FakeKms(fail_verify=True)
    provider = AwsKmsMlDsa65Provider(kms_client=kms, key_id=kms.arn)
    message = b"kms-verify-failure-binding"
    context = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"
    kms.expected_message = message
    kms.expected_context = context
    operation_id = provider_operation_id(
        key_handle=provider.key_handle,
        message=message,
        context=context,
    )

    with pytest.raises(ProviderAmbiguousOutcome, match="Verify"):
        provider.begin_sign(operation_id, message, context)
    assert kms.sign_calls == 1
    assert kms.verify_calls == 1
    assert provider.reconcile(operation_id).state is ProviderState.INDETERMINATE
    assert kms.sign_calls == 1


def test_kms_provider_rejects_disabled_or_wrong_spec_key_before_signing():
    disabled = FakeKms(enabled=False)
    with pytest.raises(ProviderError, match="enabled"):
        AwsKmsMlDsa65Provider(kms_client=disabled, key_id=disabled.arn)
    assert disabled.sign_calls == 0

    wrong = FakeKms(key_spec="ML_DSA_44")
    with pytest.raises(ProviderError, match="ML_DSA_65"):
        AwsKmsMlDsa65Provider(kms_client=wrong, key_id=wrong.arn)
    assert wrong.sign_calls == 0
