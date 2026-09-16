from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


LAB_ALGORITHM = "ML-DSA-65"
LAB_CONTEXT = "WS-ECHO-CHECKPOINT-V1"
MIN_OPENSSL_VERSION = (3, 5, 0)
MAX_PRIVATE_KEY_BYTES = 64 * 1024
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_SUBPROCESS_OUTPUT_BYTES = 256 * 1024
_VERSION_RE = re.compile(r"^OpenSSL\s+(\d+)\.(\d+)\.(\d+)")


class EchoMlDsaLabError(RuntimeError):
    pass


@dataclass(frozen=True)
class MlDsaLabEvidence:
    algorithm: str
    openssl_version: str
    context_string: str
    public_key_der_sha256: str
    signature_length: int
    payload_sha256: str
    verified: bool
    tamper_rejected: bool
    production_authorized: bool = False
    fips_module_validation_established: bool = False
    claim_boundary: str = (
        "Controlled-lab FIPS-204 algorithm interoperability only; this does not establish "
        "FIPS 140 module validation, production checkpoint deployment, Federal compliance, "
        "live-value authorization, or end-to-end post-quantum security."
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "openssl_version": self.openssl_version,
            "context_string": self.context_string,
            "public_key_der_sha256": self.public_key_der_sha256,
            "signature_length": self.signature_length,
            "payload_sha256": self.payload_sha256,
            "verified": self.verified,
            "tamper_rejected": self.tamper_rejected,
            "production_authorized": self.production_authorized,
            "fips_module_validation_established": self.fips_module_validation_established,
            "claim_boundary": self.claim_boundary,
        }


def _validate_regular_file(path: Path, *, private: bool) -> None:
    if not path.is_absolute():
        raise EchoMlDsaLabError("path must be absolute")
    try:
        status = path.lstat()
    except OSError as exc:
        raise EchoMlDsaLabError(f"unable to inspect file: {path}") from exc
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise EchoMlDsaLabError("path must reference a regular non-symlink file")
    if private:
        if status.st_uid != os.geteuid():
            raise EchoMlDsaLabError("private key file must be owned by the current service UID")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise EchoMlDsaLabError("private key file must not grant group/other permissions")
        if status.st_size < 1 or status.st_size > MAX_PRIVATE_KEY_BYTES:
            raise EchoMlDsaLabError("private key file size is invalid")
    else:
        if status.st_mode & stat.S_IWGRP or status.st_mode & stat.S_IWOTH:
            raise EchoMlDsaLabError("OpenSSL executable must not be group/other writable")
        if not os.access(path, os.X_OK):
            raise EchoMlDsaLabError("OpenSSL path is not executable")


def _invoke(
    executable: Path,
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    timeout: float = 5.0,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            [str(executable), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EchoMlDsaLabError("OpenSSL subprocess execution failed") from exc
    if len(result.stdout) > MAX_SUBPROCESS_OUTPUT_BYTES or len(result.stderr) > MAX_SUBPROCESS_OUTPUT_BYTES:
        raise EchoMlDsaLabError("OpenSSL subprocess output exceeded safety limit")
    if result.returncode != 0 and not allow_failure:
        detail = result.stderr.decode("utf-8", errors="replace")[:1000].strip()
        raise EchoMlDsaLabError(f"OpenSSL command failed: {detail or result.returncode}")
    return result


def _version_tuple(executable: Path) -> tuple[tuple[int, int, int], str]:
    result = _invoke(executable, ["version", "-v"])
    text = result.stdout.decode("utf-8", errors="replace").strip()
    match = _VERSION_RE.match(text)
    if not match:
        raise EchoMlDsaLabError("unable to parse OpenSSL version")
    version = tuple(int(match.group(index)) for index in (1, 2, 3))
    return version, text


class OpenSslMlDsa65LabSigner:
    """Explicit lab-only ML-DSA-65 sign/verify adapter using OpenSSL >= 3.5.

    The adapter is intentionally not wired into the production ECHO checkpoint
    service. It exists to produce controlled interoperability evidence first.
    """

    def __init__(self, *, openssl_path: str, private_key_path: str, lab_mode: bool) -> None:
        if lab_mode is not True:
            raise EchoMlDsaLabError("ML-DSA signer is restricted to explicit controlled-lab mode")
        self.openssl_path = Path(openssl_path)
        self.private_key_path = Path(private_key_path)
        _validate_regular_file(self.openssl_path, private=False)
        _validate_regular_file(self.private_key_path, private=True)

        version, version_text = _version_tuple(self.openssl_path)
        if version < MIN_OPENSSL_VERSION:
            raise EchoMlDsaLabError("OpenSSL 3.5.0 or newer is required for ML-DSA")
        self.openssl_version = version_text

        algorithms = _invoke(self.openssl_path, ["list", "-signature-algorithms"]).stdout
        if LAB_ALGORITHM.encode("ascii") not in algorithms:
            raise EchoMlDsaLabError("OpenSSL provider does not advertise ML-DSA-65")

        _invoke(self.openssl_path, ["pkey", "-in", str(self.private_key_path), "-check", "-noout"])
        self.public_key_pem = _invoke(
            self.openssl_path,
            ["pkey", "-in", str(self.private_key_path), "-pubout"],
        ).stdout
        self.public_key_der = _invoke(
            self.openssl_path,
            ["pkey", "-in", str(self.private_key_path), "-pubout", "-outform", "DER"],
        ).stdout
        if not self.public_key_pem or not self.public_key_der:
            raise EchoMlDsaLabError("unable to derive ML-DSA public key")
        self.public_key_der_sha256 = hashlib.sha256(self.public_key_der).hexdigest()

        probe = b"WS-ECHO-MLDSA65-LAB-SELFTEST-V1"
        signature = self.sign(probe)
        if not self.verify(probe, signature):
            raise EchoMlDsaLabError("ML-DSA lab signer self-test failed")

    @property
    def algorithm(self) -> str:
        return LAB_ALGORITHM

    @property
    def context_string(self) -> str:
        return LAB_CONTEXT

    def sign(self, payload: bytes) -> bytes:
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_PAYLOAD_BYTES:
            raise EchoMlDsaLabError("payload must be non-empty bytes within the lab size limit")
        result = _invoke(
            self.openssl_path,
            [
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.private_key_path),
                "-pkeyopt",
                f"context-string:{LAB_CONTEXT}",
            ],
            input_bytes=payload,
        )
        if not result.stdout:
            raise EchoMlDsaLabError("ML-DSA signature output was empty")
        return result.stdout

    def verify(self, payload: bytes, signature: bytes) -> bool:
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_PAYLOAD_BYTES:
            raise EchoMlDsaLabError("payload must be non-empty bytes within the lab size limit")
        if not isinstance(signature, bytes) or not signature or len(signature) > 16 * 1024:
            raise EchoMlDsaLabError("signature is empty or exceeds the lab size limit")

        with tempfile.TemporaryDirectory(prefix="ws-mldsa65-verify-") as directory:
            root = Path(directory)
            public_path = root / "public.pem"
            signature_path = root / "signature.bin"
            public_path.write_bytes(self.public_key_pem)
            signature_path.write_bytes(signature)
            public_path.chmod(0o600)
            signature_path.chmod(0o600)
            result = _invoke(
                self.openssl_path,
                [
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(public_path),
                    "-sigfile",
                    str(signature_path),
                    "-pkeyopt",
                    f"context-string:{LAB_CONTEXT}",
                ],
                input_bytes=payload,
                allow_failure=True,
            )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        detail = result.stderr.decode("utf-8", errors="replace")[:1000].strip()
        raise EchoMlDsaLabError(f"OpenSSL verification failed unexpectedly: {detail or result.returncode}")

    def exercise(self, payload: bytes) -> MlDsaLabEvidence:
        signature = self.sign(payload)
        verified = self.verify(payload, signature)
        tampered_payload = payload + b"\x00"
        tamper_rejected = not self.verify(tampered_payload, signature)
        return MlDsaLabEvidence(
            algorithm=self.algorithm,
            openssl_version=self.openssl_version,
            context_string=self.context_string,
            public_key_der_sha256=self.public_key_der_sha256,
            signature_length=len(signature),
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            verified=verified,
            tamper_rejected=tamper_rejected,
        )
