from __future__ import annotations

import os
from pathlib import Path

import pytest

from worldshepherd_sara.echo_checkpoint_mldsa_lab import (
    LAB_ALGORITHM,
    LAB_CONTEXT,
    EchoMlDsaLabError,
    OpenSslMlDsa65LabSigner,
)


OPENSSL_ENV = "WS_OPENSSL35_BIN"
KEY_ENV = "WS_MLDSA65_KEY"


def lab_inputs() -> tuple[str, str]:
    openssl_path = os.getenv(OPENSSL_ENV, "")
    key_path = os.getenv(KEY_ENV, "")
    if not openssl_path or not key_path:
        pytest.skip("controlled-lab OpenSSL ML-DSA resources are not configured")
    return openssl_path, key_path


def signer() -> OpenSslMlDsa65LabSigner:
    openssl_path, key_path = lab_inputs()
    return OpenSslMlDsa65LabSigner(
        openssl_path=openssl_path,
        private_key_path=key_path,
        lab_mode=True,
    )


def test_lab_mode_is_mandatory():
    with pytest.raises(EchoMlDsaLabError, match="controlled-lab mode"):
        OpenSslMlDsa65LabSigner(
            openssl_path="/does/not/matter",
            private_key_path="/does/not/matter",
            lab_mode=False,
        )


def test_mldsa65_real_sign_verify_and_tamper_rejection():
    adapter = signer()
    payload = b'{"schema":"WS-ECHO-CHECKPOINT-LAB-V1","sequence":1,"root":"abc123"}'
    signature = adapter.sign(payload)

    assert adapter.algorithm == LAB_ALGORITHM
    assert adapter.context_string == LAB_CONTEXT
    assert len(signature) > 1000
    assert adapter.verify(payload, signature) is True
    assert adapter.verify(payload + b"!", signature) is False
    assert len(adapter.public_key_der_sha256) == 64
    assert b"BEGIN PUBLIC KEY" in adapter.public_key_pem


def test_exercise_emits_non_secret_bounded_evidence():
    adapter = signer()
    payload = b"WS-ECHO-CHECKPOINT-CANONICAL-LAB-PAYLOAD-V1"
    evidence = adapter.exercise(payload)
    body = evidence.to_dict()

    assert body["algorithm"] == "ML-DSA-65"
    assert body["context_string"] == "WS-ECHO-CHECKPOINT-V1"
    assert body["verified"] is True
    assert body["tamper_rejected"] is True
    assert body["production_authorized"] is False
    assert body["fips_module_validation_established"] is False
    assert len(body["public_key_der_sha256"]) == 64
    assert len(body["payload_sha256"]) == 64
    lower = body["claim_boundary"].lower()
    assert "controlled-lab" in lower
    assert "does not establish fips 140 module validation" in lower
    assert "production checkpoint deployment" in lower


def test_private_key_permissions_fail_closed(tmp_path):
    openssl_path, key_path = lab_inputs()
    insecure = tmp_path / "insecure-mldsa.pem"
    insecure.write_bytes(Path(key_path).read_bytes())
    insecure.chmod(0o644)

    with pytest.raises(EchoMlDsaLabError, match="group/other permissions"):
        OpenSslMlDsa65LabSigner(
            openssl_path=openssl_path,
            private_key_path=str(insecure.resolve()),
            lab_mode=True,
        )


def test_payload_size_and_signature_shape_are_bounded():
    adapter = signer()
    with pytest.raises(EchoMlDsaLabError, match="payload"):
        adapter.sign(b"")
    with pytest.raises(EchoMlDsaLabError, match="signature"):
        adapter.verify(b"message", b"")
