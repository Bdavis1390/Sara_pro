from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from worldshepherd_sara.registry_witness_runtime import (
    WITNESS_CA_FILE_ENV,
    WITNESS_CLIENT_TOKEN_FILE_ENV,
    WITNESS_EXPECTED_FINGERPRINT_ENV,
    WITNESS_PUBLIC_KEY_FILE_ENV,
    WITNESS_TIMEOUT_ENV,
    WITNESS_URL_ENV,
    RegistryWitnessRuntimeConfigError,
    load_registry_witness_client_from_environment,
)
from worldshepherd_sara.registry_witness_http import RegistryWitnessTransportConfigError
from worldshepherd_sara.registry_witness_service import (
    RegistryWitnessLedger,
    RegistryWitnessService,
)


TOKEN = "registry-witness-runtime-token-0123456789abcdef"


def _configure(monkeypatch, tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger = RegistryWitnessLedger(
        tmp_path / "service" / "witness.db",
        private_key=private_key,
        witness_id="WS-RUNTIME-PIN",
        key_id="WS-RUNTIME-PIN-KEY",
        namespace="worldshepherd/sara/runtime-pin",
    )
    service = RegistryWitnessService(ledger=ledger, service_token=TOKEN)
    public_record = service.public_key_record()

    token_path = tmp_path / "client-token"
    token_path.write_text(TOKEN + "\n", encoding="utf-8")
    os.chmod(token_path, 0o600)
    public_path = tmp_path / "witness-public-key.json"
    public_path.write_text(json.dumps(public_record, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(public_path, 0o644)

    monkeypatch.setenv(WITNESS_URL_ENV, "https://witness.example.test")
    monkeypatch.setenv(WITNESS_CLIENT_TOKEN_FILE_ENV, str(token_path.resolve()))
    monkeypatch.setenv(WITNESS_PUBLIC_KEY_FILE_ENV, str(public_path.resolve()))
    monkeypatch.setenv(
        WITNESS_EXPECTED_FINGERPRINT_ENV,
        public_record["fingerprint_sha256"],
    )
    monkeypatch.setenv(WITNESS_TIMEOUT_ENV, "7.5")
    return service, token_path, public_path


def test_runtime_client_uses_static_pinned_key_record_and_https(monkeypatch, tmp_path):
    service, _token_path, _public_path = _configure(monkeypatch, tmp_path)

    client = load_registry_witness_client_from_environment()

    assert client.verifier.expected_witness_id == service.ledger.witness_id
    assert client.verifier.expected_namespace == service.ledger.namespace
    assert client.transport.base_url == "https://witness.example.test"
    assert client.transport.timeout_seconds == 7.5


def test_expected_fingerprint_mismatch_is_rejected(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv(WITNESS_EXPECTED_FINGERPRINT_ENV, "0" * 64)

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="does not match pinned expected fingerprint",
    ):
        load_registry_witness_client_from_environment()


def test_public_key_record_key_material_tamper_is_rejected(monkeypatch, tmp_path):
    _service, _token_path, public_path = _configure(monkeypatch, tmp_path)
    record = json.loads(public_path.read_text(encoding="utf-8"))
    replacement = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    import base64

    record["public_key_b64url"] = base64.urlsafe_b64encode(replacement).rstrip(b"=").decode("ascii")
    public_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="fingerprint does not match key material",
    ):
        load_registry_witness_client_from_environment()


def test_public_key_record_must_not_be_group_or_other_writable(monkeypatch, tmp_path):
    _service, _token_path, public_path = _configure(monkeypatch, tmp_path)
    os.chmod(public_path, 0o666)

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="must not be group/other writable",
    ):
        load_registry_witness_client_from_environment()


def test_client_token_symlink_is_rejected(monkeypatch, tmp_path):
    _service, token_path, _public_path = _configure(monkeypatch, tmp_path)
    link = tmp_path / "token-link"
    link.symlink_to(token_path)
    monkeypatch.setenv(WITNESS_CLIENT_TOKEN_FILE_ENV, str(link.absolute()))

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="must not be a symbolic link",
    ):
        load_registry_witness_client_from_environment()


def test_runtime_rejects_plain_http_witness_url(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv(WITNESS_URL_ENV, "http://witness.example.test")

    with pytest.raises(RegistryWitnessTransportConfigError, match="requires HTTPS"):
        load_registry_witness_client_from_environment()



def _write_test_ca(path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "WS G9D Runtime Test CA")]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(path, 0o644)
    return path


def test_runtime_client_accepts_secure_private_ca_and_keeps_hostname_verification(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    ca_path = _write_test_ca(tmp_path / "ca.pem")
    monkeypatch.setenv(WITNESS_CA_FILE_ENV, str(ca_path.resolve()))

    client = load_registry_witness_client_from_environment()

    assert client.transport.ssl_context.check_hostname is True
    assert client.transport.ssl_context.verify_mode == ssl.CERT_REQUIRED


def test_runtime_ca_bundle_must_use_absolute_path(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv(WITNESS_CA_FILE_ENV, "relative-ca.pem")

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="must be an absolute path",
    ):
        load_registry_witness_client_from_environment()


def test_runtime_ca_bundle_symlink_is_rejected(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    ca_path = _write_test_ca(tmp_path / "ca.pem")
    link = tmp_path / "ca-link.pem"
    link.symlink_to(ca_path)
    monkeypatch.setenv(WITNESS_CA_FILE_ENV, str(link.absolute()))

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="must not be a symbolic link",
    ):
        load_registry_witness_client_from_environment()


def test_runtime_invalid_ca_bundle_fails_closed(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    ca_path = tmp_path / "invalid-ca.pem"
    ca_path.write_text("not a certificate\n", encoding="ascii")
    os.chmod(ca_path, 0o644)
    monkeypatch.setenv(WITNESS_CA_FILE_ENV, str(ca_path.resolve()))

    with pytest.raises(
        RegistryWitnessRuntimeConfigError,
        match="could not initialize TLS trust",
    ):
        load_registry_witness_client_from_environment()
