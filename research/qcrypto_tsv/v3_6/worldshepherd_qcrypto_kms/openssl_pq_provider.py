"""Actual OpenSSL 3.5+ ML-DSA / SLH-DSA application-authorization provider.

This is a software-key provider for controlled local/test deployments.  It performs
real FIPS 204/205 signatures through OpenSSL's default provider, but it is not an HSM,
TEE, FIPS module validation claim, or Bitcoin consensus signer.  Private-key use must
be explicitly enabled by the caller.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from .crypto_agility import algorithm_spec, normalize_algorithm_id
from .operation_journal import FileOperationJournal, OperationJournalConflict, OperationJournalError
from .pq_quorum import PqProviderAttestation
from .release_policy import BitcoinReleaseIntent


class OpenSslPqProviderError(RuntimeError):
    pass


_DOMAIN = b"WS-QCRYPTO-OPENSSL-PQ-AUTH-V1\x00"
_MAX_MESSAGE = 1_048_576
_OPENSSL_NAMES = {
    "ML-DSA-44": "ML-DSA-44",
    "ML-DSA-65": "ML-DSA-65",
    "ML-DSA-87": "ML-DSA-87",
    "SLH-DSA-SHA2-128s": "SLH-DSA-SHA2-128s",
    "SLH-DSA-SHAKE-128s": "SLH-DSA-SHAKE-128s",
    "SLH-DSA-SHA2-192s": "SLH-DSA-SHA2-192s",
    "SLH-DSA-SHAKE-192s": "SLH-DSA-SHAKE-192s",
    "SLH-DSA-SHA2-256s": "SLH-DSA-SHA2-256s",
    "SLH-DSA-SHAKE-256s": "SLH-DSA-SHAKE-256s",
}


def _payload(message: bytes, context: bytes) -> bytes:
    if not isinstance(message, (bytes, bytearray)) or not isinstance(context, (bytes, bytearray)):
        raise OpenSslPqProviderError("message/context must be bytes")
    if len(context) > 65535:
        raise OpenSslPqProviderError("context too long")
    out = _DOMAIN + len(context).to_bytes(2, "big") + bytes(context) + bytes(message)
    if len(out) > _MAX_MESSAGE:
        raise OpenSslPqProviderError("domain-separated authorization message exceeds local software-provider limit")
    return out


def _safe_private_key(path: Path) -> None:
    if path.is_symlink() or not path.exists():
        raise OpenSslPqProviderError("private key path must be an existing non-symlink file")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode):
        raise OpenSslPqProviderError("private key must be a regular file")
    if st.st_mode & 0o077:
        raise OpenSslPqProviderError("software PQ private key must not grant group/other permissions")


def _run(args: list[str], *, timeout: float = 30.0, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    try:
        cp = subprocess.run(args, input=input_bytes, capture_output=True, check=False, timeout=timeout)
    except FileNotFoundError as exc:
        raise OpenSslPqProviderError("openssl executable is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise OpenSslPqProviderError("openssl operation timed out") from exc
    if cp.returncode != 0:
        msg = (cp.stderr or cp.stdout or b"openssl failed")[:1000].decode("utf-8", "replace")
        raise OpenSslPqProviderError(msg)
    return cp


def generate_openssl_pq_private_key(
    path: str | os.PathLike,
    *,
    algorithm_id: str,
    openssl_executable: str = "openssl",
) -> dict:
    """Generate a software PQ private key with private file permissions.

    Existing files are never overwritten.  This helper is intended for REGTEST /
    SIGNET development, interoperability, and offline application authorization.
    """
    algorithm = normalize_algorithm_id(algorithm_id)
    if algorithm not in _OPENSSL_NAMES:
        raise OpenSslPqProviderError("algorithm is not enabled by the OpenSSL PQ provider")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise OpenSslPqProviderError("refusing to overwrite existing PQ private key")
    if shutil.which(openssl_executable) is None:
        raise OpenSslPqProviderError("openssl executable is unavailable")
    temp_fd, temp_name = tempfile.mkstemp(prefix=".qcrypto-key-", dir=target.parent)
    os.close(temp_fd)
    os.chmod(temp_name, 0o600)
    try:
        _run([openssl_executable, "genpkey", "-algorithm", _OPENSSL_NAMES[algorithm], "-out", temp_name], timeout=120.0)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, target)
        os.chmod(target, 0o600)
        dfd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    provider = OpenSslPqAuthorizationProvider(
        provider_id="KEYGEN-INSPECT",
        algorithm_id=algorithm,
        private_key_path=target,
        operation_journal=None,
        software_private_key_authorized=True,
        openssl_executable=openssl_executable,
    )
    return {
        "algorithm_id": algorithm,
        "private_key_path": str(target),
        "public_key_der_sha256": provider.key_fingerprint_sha256,
        "software_key": True,
        "production_hardware_protection_claim": False,
    }


class OpenSslPqAuthorizationProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        algorithm_id: str,
        private_key_path: str | os.PathLike,
        operation_journal: FileOperationJournal | None,
        software_private_key_authorized: bool = False,
        openssl_executable: str = "openssl",
        command_timeout_seconds: float = 30.0,
        fault_domain_id: str = "LOCAL_SOFTWARE",
    ) -> None:
        if not software_private_key_authorized:
            raise OpenSslPqProviderError("software private-key use requires explicit authorization")
        if not provider_id or len(provider_id) > 128:
            raise OpenSslPqProviderError("provider_id is required")
        algorithm = normalize_algorithm_id(algorithm_id)
        if algorithm not in _OPENSSL_NAMES:
            raise OpenSslPqProviderError("algorithm is not enabled by the OpenSSL PQ provider")
        if command_timeout_seconds <= 0:
            raise OpenSslPqProviderError("command timeout must be positive")
        self._provider_id = provider_id
        self._algorithm = algorithm
        self._private_key_path = Path(private_key_path)
        self._journal = operation_journal
        self._openssl = openssl_executable
        self._timeout = float(command_timeout_seconds)
        self._fault_domain_id = fault_domain_id.strip()
        if not self._fault_domain_id or len(self._fault_domain_id) > 128:
            raise OpenSslPqProviderError("fault_domain_id is invalid")
        if shutil.which(self._openssl) is None:
            raise OpenSslPqProviderError("openssl executable is unavailable")
        _safe_private_key(self._private_key_path)
        self._assert_key_algorithm()
        self._public_der = self._extract_public_der()
        self._fingerprint = hashlib.sha256(self._public_der).hexdigest()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def algorithm_id(self) -> str:
        return self._algorithm

    @property
    def key_fingerprint_sha256(self) -> str:
        return self._fingerprint

    @property
    def software_key(self) -> bool:
        return True

    @property
    def fault_domain_id(self) -> str:
        return self._fault_domain_id

    def _assert_key_algorithm(self) -> None:
        cp = _run([self._openssl, "pkey", "-in", str(self._private_key_path), "-text", "-noout"], timeout=self._timeout)
        first = cp.stdout.decode("utf-8", "replace").splitlines()[0] if cp.stdout else ""
        if not first.startswith(_OPENSSL_NAMES[self._algorithm] + " Private-Key"):
            raise OpenSslPqProviderError("private key algorithm does not match configured PQ algorithm")

    def _extract_public_der(self) -> bytes:
        cp = _run([self._openssl, "pkey", "-in", str(self._private_key_path), "-pubout", "-outform", "DER"], timeout=self._timeout)
        if not cp.stdout:
            raise OpenSslPqProviderError("unable to extract PQ public key")
        return bytes(cp.stdout)

    def _operation_id(self, intent: BitcoinReleaseIntent, context: bytes) -> str:
        body = (
            b"WS-QCRYPTO-OPENSSL-PQ-OP-V1\x00"
            + self._provider_id.encode()
            + b"\x00"
            + self._algorithm.encode()
            + b"\x00"
            + bytes.fromhex(self._fingerprint)
            + hashlib.sha256(context).digest()
            + hashlib.sha256(intent.canonical_bytes()).digest()
        )
        return "QCRYPTO-OPENSSL-PQ-" + hashlib.sha256(body).hexdigest()

    def sign_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes) -> PqProviderAttestation:
        _safe_private_key(self._private_key_path)
        self._assert_key_algorithm()
        public_now = self._extract_public_der()
        if hashlib.sha256(public_now).hexdigest() != self._fingerprint:
            raise OpenSslPqProviderError("PQ private/public key identity changed after provider initialization")
        operation_id = self._operation_id(intent, context)
        binding = {
            "provider_id": self._provider_id,
            "algorithm_id": self._algorithm,
            "key_fingerprint_sha256": self._fingerprint,
            "intent_sha256": intent.intent_sha256,
            "context_sha256": hashlib.sha256(context).hexdigest(),
        }
        if self._journal is not None:
            try:
                record, created = self._journal.claim_for_sign(operation_id, binding)
            except (OperationJournalError, OperationJournalConflict) as exc:
                raise OpenSslPqProviderError("operation journal rejected OpenSSL PQ signing claim") from exc
            if not created:
                if record.state == "SIGNED" and record.result:
                    raw = record.result
                    try:
                        return PqProviderAttestation(**raw)
                    except Exception as exc:
                        raise OpenSslPqProviderError("journal contains invalid OpenSSL PQ attestation") from exc
                raise OpenSslPqProviderError(f"journal state {record.state} forbids a second PQ signing attempt")
        else:
            created = False

        data = _payload(intent.canonical_bytes(), context)
        with tempfile.TemporaryDirectory(prefix="qcrypto-openssl-pq-") as td:
            msg = Path(td) / "message.bin"
            sig = Path(td) / "signature.bin"
            msg.write_bytes(data)
            os.chmod(msg, 0o600)
            try:
                _run([
                    self._openssl, "pkeyutl", "-sign", "-inkey", str(self._private_key_path),
                    "-rawin", "-in", str(msg), "-out", str(sig),
                ], timeout=self._timeout)
                signature = sig.read_bytes()
            except Exception as exc:
                if self._journal is not None and created:
                    self._journal.mark_indeterminate(operation_id, binding)
                raise OpenSslPqProviderError("OpenSSL PQ signature outcome failed or is ambiguous; retry is forbidden for this operation ID") from exc
        expected = algorithm_spec(self._algorithm).signature_bytes
        if len(signature) != expected:
            if self._journal is not None and created:
                self._journal.mark_indeterminate(operation_id, binding)
            raise OpenSslPqProviderError(f"OpenSSL returned {len(signature)} signature bytes; expected {expected}")
        if not self.verify_release_intent(intent=intent, context=context, signature=signature):
            if self._journal is not None and created:
                self._journal.mark_indeterminate(operation_id, binding)
            raise OpenSslPqProviderError("self-verification of OpenSSL PQ signature failed")
        att = PqProviderAttestation(
            intent_sha256=intent.intent_sha256,
            provider_id=self._provider_id,
            algorithm_id=self._algorithm,
            key_fingerprint_sha256=self._fingerprint,
            signature_b64url=__import__("base64").urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
            operation_id=operation_id,
            fault_domain_id=self.fault_domain_id,
        )
        if self._journal is not None:
            try:
                self._journal.mark_signed(operation_id, binding, att.to_dict())
            except (OperationJournalError, OperationJournalConflict) as exc:
                raise OpenSslPqProviderError("PQ signature succeeded but durable journal commit failed; retry is forbidden") from exc
        return att

    def verify_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes, signature: bytes) -> bool:
        if len(signature) != algorithm_spec(self._algorithm).signature_bytes:
            return False
        data = _payload(intent.canonical_bytes(), context)
        with tempfile.TemporaryDirectory(prefix="qcrypto-openssl-pq-verify-") as td:
            pub = Path(td) / "public.der"
            msg = Path(td) / "message.bin"
            sig = Path(td) / "signature.bin"
            pub.write_bytes(self._public_der)
            msg.write_bytes(data)
            sig.write_bytes(bytes(signature))
            os.chmod(pub, 0o600)
            os.chmod(msg, 0o600)
            os.chmod(sig, 0o600)
            try:
                cp = subprocess.run([
                    self._openssl, "pkeyutl", "-verify", "-pubin", "-keyform", "DER",
                    "-inkey", str(pub), "-rawin", "-in", str(msg), "-sigfile", str(sig),
                ], capture_output=True, check=False, timeout=self._timeout)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
            return cp.returncode == 0
