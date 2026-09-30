from __future__ import annotations

import base64
import hashlib
import tempfile
import unittest

from worldshepherd_qcrypto_kms.aws_kms_provider import (
    AwsKmsMlDsa65Provider,
    AwsKmsProviderConflict,
    AwsKmsProviderError,
    ProviderAmbiguousOutcome,
    ProviderState,
    provider_operation_id,
)
from worldshepherd_qcrypto_kms.operation_journal import FileOperationJournal


class FakeKms:
    def __init__(
        self,
        *,
        key_spec="ML_DSA_65",
        key_usage="SIGN_VERIFY",
        enabled=True,
        key_state="Enabled",
        fail_sign=False,
        endpoint="https://kms-fips.us-east-1.amazonaws.com",
        arn="arn:aws:kms:us-east-1:111122223333:key/12345678-1234-1234-1234-123456789abc",
    ):
        self.key_spec = key_spec
        self.key_usage = key_usage
        self.enabled = enabled
        self.key_state = key_state
        self.fail_sign = fail_sign
        self.sign_calls = []
        self.verify_calls = []
        self.public = b"synthetic-spki-public-key-der"
        self.arn = arn
        from types import SimpleNamespace
        self.meta = SimpleNamespace(endpoint_url=endpoint)

    def describe_key(self, **kwargs):
        return {"KeyMetadata": {
            "KeyId": "12345678-1234-1234-1234-123456789abc",
            "Arn": self.arn,
            "AWSAccountId": "111122223333",
            "KeySpec": self.key_spec,
            "KeyUsage": self.key_usage,
            "Enabled": self.enabled,
            "KeyState": self.key_state,
        }}

    def get_public_key(self, **kwargs):
        return {"PublicKey": self.public, "SigningAlgorithms": ["ML_DSA_SHAKE_256"]}

    def sign(self, **kwargs):
        self.sign_calls.append(kwargs)
        if self.fail_sign:
            raise TimeoutError("synthetic timeout after request dispatch")
        digest = hashlib.sha256(kwargs["Message"]).digest()
        return {"KeyId": self.arn, "SigningAlgorithm": "ML_DSA_SHAKE_256", "Signature": b"sig:" + digest, "ResponseMetadata": {"RequestId": "req-001"}}

    def verify(self, **kwargs):
        self.verify_calls.append(kwargs)
        return {"SignatureValid": kwargs["Signature"].startswith(b"sig:")}


class AwsKmsProviderTests(unittest.TestCase):
    def make_journal(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return FileOperationJournal(td.name)

    def provider(self, fake=None, **kwargs):
        production = kwargs.pop("production", True)
        journal = kwargs.pop("journal", self.make_journal() if production else None)
        return AwsKmsMlDsa65Provider(
            kms_client=fake or FakeKms(),
            key_id="alias/worldshepherd-qcrypto-mldsa65",
            region=kwargs.pop("region", "us-east-1"),
            fips_endpoint_requested=kwargs.pop("fips", True),
            production_profile=production,
            operation_journal=journal,
        )

    def test_descriptor_fail_closed_and_nonexportable(self):
        p = self.provider()
        d = p.descriptor
        self.assertEqual(d.key_spec, "ML_DSA_65")
        self.assertEqual(d.key_usage, "SIGN_VERIFY")
        self.assertTrue(d.enabled)
        self.assertTrue(d.fips_endpoint_requested)
        self.assertFalse(d.private_key_export_supported)
        self.assertFalse(d.chain_native_signing_supported)
        self.assertFalse(d.transaction_broadcast_supported)
        self.assertFalse(d.mainnet_authority)
        self.assertFalse(hasattr(p, "export_private_key"))
        self.assertFalse(hasattr(p, "private_key_bytes"))

    def test_wrong_key_spec_usage_or_state_is_rejected(self):
        for fake in (
            FakeKms(key_spec="ECC_SECG_P256K1"),
            FakeKms(key_usage="ENCRYPT_DECRYPT"),
            FakeKms(enabled=False),
            FakeKms(key_state="PendingDeletion"),
        ):
            with self.assertRaises(AwsKmsProviderError):
                self.provider(fake)

    def test_production_requires_durable_journal_and_exact_fips_origin(self):
        with self.assertRaises(AwsKmsProviderError):
            AwsKmsMlDsa65Provider(
                kms_client=FakeKms(), key_id="k", region="us-east-1",
                fips_endpoint_requested=True, production_profile=True,
                operation_journal=None,
            )
        with self.assertRaises(AwsKmsProviderError):
            self.provider(FakeKms(endpoint="https://kms-fips.us-east-1.amazonaws.com.attacker.invalid"))
        with self.assertRaises(AwsKmsProviderError):
            self.provider(FakeKms(endpoint="http://kms-fips.us-east-1.amazonaws.com"))
        with self.assertRaises(AwsKmsProviderError):
            self.provider(FakeKms(endpoint="https://kms-fips.us-west-2.amazonaws.com"))
        p = AwsKmsMlDsa65Provider(
            kms_client=FakeKms(), key_id="k", region="us-east-1",
            fips_endpoint_requested=False, production_profile=False,
        )
        self.assertFalse(p.descriptor.fips_endpoint_requested)

    def test_arn_region_and_account_binding(self):
        with self.assertRaises(AwsKmsProviderError):
            self.provider(FakeKms(arn="arn:aws:kms:us-west-2:111122223333:key/abc"))
        with self.assertRaises(AwsKmsProviderError):
            self.provider(FakeKms(arn="arn:aws-cn:kms:us-east-1:111122223333:key/abc"))

        class BadAccount(FakeKms):
            def describe_key(self, **kwargs):
                out = super().describe_key(**kwargs)
                out["KeyMetadata"]["AWSAccountId"] = "999900001111"
                return out

        with self.assertRaises(AwsKmsProviderError):
            self.provider(BadAccount())

    def test_exactly_one_sign_call_and_expected_kms_parameters(self):
        fake = FakeKms()
        p = self.provider(fake)
        msg = b"release-binding"
        ctx = b"WS-QCRYPTO-CUSTODY-RELEASE-V1"
        op = provider_operation_id(key_arn=p.key_handle, message=msg, context=ctx)
        result = p.begin_sign(op, msg, ctx)
        self.assertEqual(result.state, ProviderState.SIGNED)
        self.assertEqual(result.aws_request_id, "req-001")
        self.assertEqual(len(fake.sign_calls), 1)
        call = fake.sign_calls[0]
        self.assertEqual(call["KeyId"], p.key_handle)
        self.assertEqual(call["MessageType"], "RAW")
        self.assertEqual(call["SigningAlgorithm"], "ML_DSA_SHAKE_256")
        self.assertIn(ctx, call["Message"])
        self.assertIn(msg, call["Message"])
        again = p.begin_sign(op, msg, ctx)
        self.assertEqual(again, result)
        self.assertEqual(len(fake.sign_calls), 1)

    def test_signed_result_replays_after_provider_restart_without_resign(self):
        fake = FakeKms()
        journal = self.make_journal()
        p1 = self.provider(fake, journal=journal)
        msg, ctx = b"durable", b"restart"
        op = provider_operation_id(key_arn=p1.key_handle, message=msg, context=ctx)
        r1 = p1.begin_sign(op, msg, ctx)
        self.assertEqual(len(fake.sign_calls), 1)
        p2 = self.provider(fake, journal=journal)
        r2 = p2.begin_sign(op, msg, ctx)
        self.assertEqual(r1, r2)
        self.assertEqual(len(fake.sign_calls), 1)

    def test_ambiguous_sign_is_durable_across_restart_and_never_retried(self):
        journal = self.make_journal()
        failing = FakeKms(fail_sign=True)
        p1 = self.provider(failing, journal=journal)
        msg, ctx = b"m", b"c"
        op = provider_operation_id(key_arn=p1.key_handle, message=msg, context=ctx)
        with self.assertRaises(ProviderAmbiguousOutcome):
            p1.begin_sign(op, msg, ctx)
        self.assertEqual(len(failing.sign_calls), 1)

        healthy = FakeKms(fail_sign=False)
        p2 = self.provider(healthy, journal=journal)
        with self.assertRaises(ProviderAmbiguousOutcome):
            p2.begin_sign(op, msg, ctx)
        self.assertEqual(len(healthy.sign_calls), 0)
        state = p2.reconcile(op)
        self.assertEqual(state.state, ProviderState.INDETERMINATE)
        self.assertFalse(state.safe_to_retry)

    def test_operation_id_binds_key_message_and_context(self):
        p = self.provider()
        a = provider_operation_id(key_arn=p.key_handle, message=b"m", context=b"c")
        b = provider_operation_id(key_arn=p.key_handle, message=b"m2", context=b"c")
        c = provider_operation_id(key_arn=p.key_handle, message=b"m", context=b"c2")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        with self.assertRaises(Exception):
            p.begin_sign(b, b"m", b"c")

    def test_public_key_substitution_is_detected_before_sign_without_poisoning_journal(self):
        fake = FakeKms()
        journal = self.make_journal()
        p = self.provider(fake, journal=journal)
        fake.public = b"different-public-key"
        msg, ctx = b"release", b"context"
        op = provider_operation_id(key_arn=p.key_handle, message=msg, context=ctx)
        with self.assertRaises(AwsKmsProviderConflict):
            p.begin_sign(op, msg, ctx)
        self.assertEqual(fake.sign_calls, [])
        self.assertIsNone(journal.get(op))

    def test_kms_verify_uses_identical_domain_separated_message(self):
        fake = FakeKms()
        p = self.provider(fake)
        msg, ctx = b"release", b"context"
        op = provider_operation_id(key_arn=p.key_handle, message=msg, context=ctx)
        result = p.begin_sign(op, msg, ctx)
        raw = base64.urlsafe_b64decode(result.signature_b64url + "=" * (-len(result.signature_b64url) % 4))
        self.assertTrue(p.verify_with_kms(message=msg, context=ctx, signature=raw))
        self.assertEqual(fake.verify_calls[0]["Message"], fake.sign_calls[0]["Message"])

    def test_raw_size_limit_fails_closed_without_claiming_journal(self):
        journal = self.make_journal()
        p = self.provider(journal=journal)
        msg, ctx = b"x" * 4096, b"context"
        op = provider_operation_id(key_arn=p.key_handle, message=msg, context=ctx)
        with self.assertRaises(AwsKmsProviderError):
            p.begin_sign(op, msg, ctx)
        self.assertIsNone(journal.get(op))

    def test_sign_response_key_or_algorithm_mismatch_becomes_indeterminate(self):
        class BadResponse(FakeKms):
            def sign(self, **kwargs):
                out = super().sign(**kwargs)
                out["KeyId"] = "arn:aws:kms:us-east-1:111122223333:key/other"
                return out
        fake = BadResponse()
        journal = self.make_journal()
        p = self.provider(fake, journal=journal)
        msg, ctx = b"response-binding", b"context"
        op = provider_operation_id(key_arn=p.key_handle, message=msg, context=ctx)
        with self.assertRaises(ProviderAmbiguousOutcome):
            p.begin_sign(op, msg, ctx)
        self.assertEqual(journal.get(op).state, "INDETERMINATE")


class ClientFactoryTests(unittest.TestCase):
    def test_production_client_config_is_fips_and_single_attempt(self):
        from worldshepherd_qcrypto_kms.client_factory import production_botocore_config_kwargs
        cfg = production_botocore_config_kwargs("us-east-1")
        self.assertTrue(cfg["use_fips_endpoint"])
        self.assertEqual(cfg["retries"]["total_max_attempts"], 1)
        self.assertEqual(cfg["region_name"], "us-east-1")


if __name__ == "__main__":
    unittest.main()
