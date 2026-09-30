from __future__ import annotations

import base64
import hashlib
import queue
import socket
import ssl
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.sda import (
    SdaContractValidationState,
    SdaIngestDisposition,
    SdaInterfaceContract,
    SdaObservation,
    SdaSourceClass,
    SdaSourceIdentity,
    evaluate_sda_ingest,
)
from worldshepherd_sara.sda_identity import (
    SdaWorkloadIdentityAssertion,
    canonical_sda_workload_identity_message,
    verify_sda_workload_identity,
)
from worldshepherd_sara.sda_transport_identity import (
    assert_transport_identity_bound_to_workload,
    inspect_tls_peer_certificate,
    verify_tls_peer_for_workload,
)


NOW = datetime(2026, 9, 18, 0, 15, tzinfo=timezone.utc)
WORKLOAD_ID = "spiffe://worldshepherd.internal/sda/adapter/synth-radar-a"
PRIME_KEY_ID = "SDA-TRANSPORT-PRIME-K1"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _certificate_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_ca():
    key = _new_rsa_key()
    cert_now = _certificate_now()
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name("WS-SDA Test CA"))
        .issuer_name(_name("WS-SDA Test CA"))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(cert_now - timedelta(days=1))
        .not_valid_after(cert_now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _build_leaf(
    *,
    ca_key,
    ca_cert,
    common_name: str,
    san_dns: str | None = None,
    san_uri: str | None = None,
    client_auth: bool = False,
    server_auth: bool = False,
):
    key = _new_rsa_key()
    cert_now = _certificate_now()
    names: list[x509.GeneralName] = []
    if san_dns:
        names.append(x509.DNSName(san_dns))
    if san_uri:
        names.append(x509.UniformResourceIdentifier(san_uri))
    ekus = []
    if client_auth:
        ekus.append(ExtendedKeyUsageOID.CLIENT_AUTH)
    if server_auth:
        ekus.append(ExtendedKeyUsageOID.SERVER_AUTH)

    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(common_name))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(cert_now - timedelta(hours=1))
        .not_valid_after(cert_now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )
    if names:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(names),
            critical=False,
        )
    if ekus:
        builder = builder.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)
    return key, builder.sign(ca_key, hashes.SHA256())


def _pem_key(key) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )


def _pem_cert(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def _der_cert(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.DER)


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def _prime_workload_identity(client_cert: x509.Certificate):
    private = ed25519.Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            PRIME_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        }
    )
    fingerprint = "sha256:" + hashlib.sha256(_der_cert(client_cert)).hexdigest()
    unsigned = SdaWorkloadIdentityAssertion(
        key_id=PRIME_KEY_ID,
        workload_id=WORKLOAD_ID,
        source_id="SYNTH-RADAR-A",
        adapter_id="WS-SDA-SYNTH",
        adapter_version="1.0.0",
        transport_cert_sha256=fingerprint,
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(minutes=2),
        nonce="nonce-sda-transport-0001",
        signature_b64url="placeholder",
    )
    signature = _b64url(
        private.sign(canonical_sda_workload_identity_message(unsigned))
    )
    assertion = unsigned.model_copy(update={"signature_b64url": signature})
    return verify_sda_workload_identity(assertion, verifier=verifier, now=NOW)


def _sda_contract() -> SdaInterfaceContract:
    return SdaInterfaceContract(
        contract_id="SDA-CONTRACT-MTLS-001",
        source_id="SYNTH-RADAR-A",
        adapter_id="WS-SDA-SYNTH",
        adapter_version="1.0.0",
        authoritative_spec_ref="internal://ws-sda/mtls-contract-v1",
        authoritative_spec_digest="sha256:" + "b" * 64,
        allowed_reference_frames=["GCRF"],
        allowed_releasability_tags=["US_ONLY"],
        max_age_seconds=600.0,
        max_future_skew_seconds=30.0,
        max_clock_uncertainty_seconds=0.05,
        validation_state=SdaContractValidationState.SYNTHETIC,
        validation_ref="test://sda-mtls-contract",
        require_workload_identity=True,
        require_transport_identity=True,
        enabled=True,
    )


def _sda_observation(active: SdaInterfaceContract) -> SdaObservation:
    covariance = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(6):
        covariance[index][index] = 1.0
    return SdaObservation(
        observation_id="OBS-MTLS-001",
        source_event_id="EVENT-MTLS-001",
        source_sequence=1,
        source=SdaSourceIdentity(
            source_id="SYNTH-RADAR-A",
            source_class=SdaSourceClass.SYNTHETIC,
            provider="Worldshepherd synthetic fixture",
            sensor_id="SYNTH-SENSOR-1",
            adapter_id="WS-SDA-SYNTH",
            adapter_version="1.0.0",
        ),
        observed_at=NOW,
        received_at=NOW + timedelta(seconds=1),
        time_system="UTC",
        clock_uncertainty_seconds=0.01,
        reference_frame="GCRF",
        position_km=(1.0, 2.0, 3.0),
        velocity_km_s=(0.1, 0.2, 0.3),
        covariance_6x6=covariance,
        measurement_confidence=0.8,
        source_reliability=0.8,
        handling_label="UNCLASSIFIED_SYNTHETIC",
        releasability_tags=["US_ONLY"],
        raw_source_digest="sha256:" + "a" * 64,
        interface_contract_id=active.contract_id,
        interface_contract_digest=active.digest(),
        transformation_refs=["adapter:synthetic-mtls-v1"],
    )


def _contexts(
    tmp_path: Path,
    *,
    ca_key,
    ca_cert,
    server_key,
    server_cert,
    client_key=None,
    client_cert=None,
):
    ca_path = _write(tmp_path / "ca.pem", _pem_cert(ca_cert))
    server_cert_path = _write(tmp_path / "server.pem", _pem_cert(server_cert))
    server_key_path = _write(tmp_path / "server.key", _pem_key(server_key))

    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.minimum_version = ssl.TLSVersion.TLSv1_2
    server_context.verify_mode = ssl.CERT_REQUIRED
    server_context.load_verify_locations(cafile=str(ca_path))
    server_context.load_cert_chain(
        certfile=str(server_cert_path),
        keyfile=str(server_key_path),
    )

    client_context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(ca_path),
    )
    client_context.minimum_version = ssl.TLSVersion.TLSv1_2
    client_context.check_hostname = True

    if client_key is not None and client_cert is not None:
        client_cert_path = _write(
            tmp_path / f"client-{client_cert.serial_number}.pem",
            _pem_cert(client_cert),
        )
        client_key_path = _write(
            tmp_path / f"client-{client_cert.serial_number}.key",
            _pem_key(client_key),
        )
        client_context.load_cert_chain(
            certfile=str(client_cert_path),
            keyfile=str(client_key_path),
        )
    return server_context, client_context


def _exchange(server_context, client_context, workload):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    results: queue.Queue[str] = queue.Queue()

    def serve():
        try:
            raw, _address = listener.accept()
            with raw:
                with server_context.wrap_socket(raw, server_side=True) as tls:
                    peer = tls.getpeercert(binary_form=True)
                    try:
                        verify_tls_peer_for_workload(peer, workload, now=NOW)
                        tls.sendall(b"OK")
                        results.put("OK")
                    except PrimeSentinelAuthorizationError as exc:
                        tls.sendall(b"DENY")
                        results.put("DENY:" + str(exc))
        except ssl.SSLError as exc:
            results.put("TLS_ERROR:" + str(exc))
        finally:
            listener.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    data = b""
    error: Exception | None = None
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            with client_context.wrap_socket(raw, server_hostname="localhost") as tls:
                data = tls.recv(16)
    except Exception as exc:  # handshake failure is part of the negative test surface
        error = exc

    thread.join(timeout=5)
    assert not thread.is_alive()
    return data, error, results.get(timeout=1)


def test_peer_certificate_inspection_and_signed_fingerprint_binding():
    ca_key, ca_cert = _build_ca()
    client_key, client_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter A",
        san_uri=WORKLOAD_ID,
        client_auth=True,
    )
    assert client_key is not None
    workload = _prime_workload_identity(client_cert)
    transport = inspect_tls_peer_certificate(_der_cert(client_cert))

    assert transport.client_auth_eku is True
    assert transport.basic_constraints_ca is False
    assert WORKLOAD_ID in transport.san_uris
    assert transport.certificate_sha256 == workload.transport_cert_sha256
    assert_transport_identity_bound_to_workload(transport, workload, now=NOW)


def test_same_ca_wrong_client_certificate_is_rejected_by_application_binding():
    ca_key, ca_cert = _build_ca()
    _good_key, good_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter A",
        san_uri=WORKLOAD_ID,
        client_auth=True,
    )
    _wrong_key, wrong_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter B",
        san_uri="spiffe://worldshepherd.internal/sda/adapter/other",
        client_auth=True,
    )

    workload = _prime_workload_identity(good_cert)
    wrong = inspect_tls_peer_certificate(_der_cert(wrong_cert))
    with pytest.raises(
        PrimeSentinelAuthorizationError,
        match="fingerprint",
    ):
        assert_transport_identity_bound_to_workload(wrong, workload, now=NOW)


def test_real_mtls_requires_client_certificate_and_binds_tls_peer_to_workload(tmp_path):
    ca_key, ca_cert = _build_ca()
    server_key, server_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="WS-SDA localhost server",
        san_dns="localhost",
        server_auth=True,
    )
    client_key, client_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter A",
        san_uri=WORKLOAD_ID,
        client_auth=True,
    )
    wrong_key, wrong_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter B",
        san_uri="spiffe://worldshepherd.internal/sda/adapter/other",
        client_auth=True,
    )
    workload = _prime_workload_identity(client_cert)

    good_dir = tmp_path / "good"
    good_dir.mkdir()
    server_context, good_client = _contexts(
        good_dir,
        ca_key=ca_key,
        ca_cert=ca_cert,
        server_key=server_key,
        server_cert=server_cert,
        client_key=client_key,
        client_cert=client_cert,
    )
    data, error, server_result = _exchange(
        server_context,
        good_client,
        workload,
    )
    assert error is None
    assert data == b"OK"
    assert server_result == "OK"

    none_dir = tmp_path / "none"
    none_dir.mkdir()
    server_context, no_client = _contexts(
        none_dir,
        ca_key=ca_key,
        ca_cert=ca_cert,
        server_key=server_key,
        server_cert=server_cert,
    )
    data, error, server_result = _exchange(
        server_context,
        no_client,
        workload,
    )
    assert data == b""
    assert isinstance(error, ssl.SSLError)
    assert server_result.startswith("TLS_ERROR:")

    wrong_dir = tmp_path / "wrong"
    wrong_dir.mkdir()
    server_context, wrong_client = _contexts(
        wrong_dir,
        ca_key=ca_key,
        ca_cert=ca_cert,
        server_key=server_key,
        server_cert=server_cert,
        client_key=wrong_key,
        client_cert=wrong_cert,
    )
    data, error, server_result = _exchange(
        server_context,
        wrong_client,
        workload,
    )
    assert error is None
    assert data == b"DENY"
    assert "fingerprint" in server_result


def test_ingest_requires_and_accepts_exact_mtls_transport_binding():
    ca_key, ca_cert = _build_ca()
    _client_key, client_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter A",
        san_uri=WORKLOAD_ID,
        client_auth=True,
    )
    _wrong_key, wrong_cert = _build_leaf(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="SDA Adapter B",
        san_uri="spiffe://worldshepherd.internal/sda/adapter/other",
        client_auth=True,
    )

    active = _sda_contract()
    item = _sda_observation(active)
    workload = _prime_workload_identity(client_cert)
    correct_transport = inspect_tls_peer_certificate(_der_cert(client_cert))
    wrong_transport = inspect_tls_peer_certificate(_der_cert(wrong_cert))

    missing = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=workload,
        now=NOW,
    )
    assert missing.disposition == SdaIngestDisposition.REJECT
    assert any("requires verified mTLS transport identity" in reason for reason in missing.reasons)

    accepted = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=workload,
        transport_identity=correct_transport,
        now=NOW,
    )
    assert accepted.disposition == SdaIngestDisposition.ACCEPT

    rejected = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=workload,
        transport_identity=wrong_transport,
        now=NOW,
    )
    assert rejected.disposition == SdaIngestDisposition.REJECT
    assert any("fingerprint" in reason for reason in rejected.reasons)


def test_contract_cannot_require_transport_identity_without_workload_identity():
    with pytest.raises(ValueError, match="transport identity requires workload identity"):
        SdaInterfaceContract(
            contract_id="SDA-CONTRACT-INVALID-MTLS",
            source_id="SYNTH-RADAR-A",
            adapter_id="WS-SDA-SYNTH",
            adapter_version="1.0.0",
            authoritative_spec_ref="internal://ws-sda/invalid-mtls-contract",
            authoritative_spec_digest="sha256:" + "b" * 64,
            allowed_reference_frames=["GCRF"],
            allowed_releasability_tags=["US_ONLY"],
            max_age_seconds=600.0,
            max_future_skew_seconds=30.0,
            max_clock_uncertainty_seconds=0.05,
            validation_state=SdaContractValidationState.SYNTHETIC,
            validation_ref="test://invalid-mtls-contract",
            require_workload_identity=False,
            require_transport_identity=True,
            enabled=True,
        )
