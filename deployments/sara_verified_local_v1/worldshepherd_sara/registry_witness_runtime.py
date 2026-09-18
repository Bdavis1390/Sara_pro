from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import ssl
import stat
from pathlib import Path
from typing import Any

from .registry_monotonic_witness import (
    RegistryMonotonicWitnessClient,
    RegistryMonotonicWitnessVerifier,
)
from .registry_witness_gate import (
    RegistryWitnessPrecondition,
    prepare_registry_witness_precondition,
)
from .registry_witness_http import HttpsRegistryWitnessTransport
from .registry_witness_service import WITNESS_PUBLIC_KEY_SCHEMA
from .storage import DurableStore


WITNESS_URL_ENV = "REGISTRY_WITNESS_URL"
WITNESS_CLIENT_TOKEN_FILE_ENV = "REGISTRY_WITNESS_CLIENT_TOKEN_FILE"
WITNESS_PUBLIC_KEY_FILE_ENV = "REGISTRY_WITNESS_PUBLIC_KEY_FILE"
WITNESS_EXPECTED_FINGERPRINT_ENV = "REGISTRY_WITNESS_EXPECTED_FINGERPRINT_SHA256"
WITNESS_TIMEOUT_ENV = "REGISTRY_WITNESS_TIMEOUT_SECONDS"
WITNESS_CA_FILE_ENV = "REGISTRY_WITNESS_CA_FILE"
MAX_CLIENT_TOKEN_BYTES = 4 * 1024
MAX_PUBLIC_KEY_RECORD_BYTES = 16 * 1024
MAX_CA_BUNDLE_BYTES = 1024 * 1024
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_NAMESPACE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RegistryWitnessRuntimeConfigError(RuntimeError):
    pass


def _read_file(
    path_value: str,
    *,
    env_name: str,
    label: str,
    maximum: int,
    secret: bool,
) -> bytes:
    if not path_value:
        raise RegistryWitnessRuntimeConfigError(f"{env_name} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise RegistryWitnessRuntimeConfigError(f"{env_name} must be an absolute path")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise RegistryWitnessRuntimeConfigError(f"unable to inspect {label}") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise RegistryWitnessRuntimeConfigError(f"{label} must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RegistryWitnessRuntimeConfigError(f"unable to open {label} securely") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise RegistryWitnessRuntimeConfigError(f"{label} must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise RegistryWitnessRuntimeConfigError(f"{label} changed during secure open")
        if status.st_uid != os.geteuid():
            raise RegistryWitnessRuntimeConfigError(f"{label} must be owned by the service UID")
        permissions = stat.S_IMODE(status.st_mode)
        if secret and permissions & 0o077:
            raise RegistryWitnessRuntimeConfigError(
                f"{label} must not grant group/other permissions"
            )
        if not secret and permissions & 0o022:
            raise RegistryWitnessRuntimeConfigError(
                f"{label} must not be group/other writable"
            )
        if status.st_size < 1 or status.st_size > maximum:
            raise RegistryWitnessRuntimeConfigError(f"{label} size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > maximum:
        raise RegistryWitnessRuntimeConfigError(f"{label} is too large")
    return data


def _load_token(path_value: str) -> str:
    data = _read_file(
        path_value,
        env_name=WITNESS_CLIENT_TOKEN_FILE_ENV,
        label="registry witness client-token file",
        maximum=MAX_CLIENT_TOKEN_BYTES,
        secret=True,
    )
    try:
        token = data.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness client-token file must be UTF-8 text"
        ) from exc
    if not token or token != token.strip() or "\n" in token or "\r" in token:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness client-token file must contain one token"
        )
    if len(token) < 32:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness client token must be at least 32 characters"
        )
    return token


def _decode_key(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise RegistryWitnessRuntimeConfigError("witness public key is missing")
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        raw = base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise RegistryWitnessRuntimeConfigError("witness public key is invalid base64url") from exc
    if len(raw) != 32:
        raise RegistryWitnessRuntimeConfigError("witness Ed25519 public key must be 32 bytes")
    return raw


def _load_public_key_record(path_value: str, expected_fingerprint: str) -> dict[str, str]:
    data = _read_file(
        path_value,
        env_name=WITNESS_PUBLIC_KEY_FILE_ENV,
        label="registry witness public-key record",
        maximum=MAX_PUBLIC_KEY_RECORD_BYTES,
        secret=False,
    )
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness public-key record must be UTF-8 JSON"
        ) from exc
    if not isinstance(record, dict):
        raise RegistryWitnessRuntimeConfigError(
            "registry witness public-key record must be an object"
        )
    required = {
        "schema",
        "issuer",
        "witness_id",
        "namespace",
        "algorithm",
        "key_id",
        "public_key_b64url",
        "fingerprint_sha256",
        "claims_boundary",
    }
    if set(record) != required:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness public-key record fields are invalid"
        )
    if record.get("schema") != WITNESS_PUBLIC_KEY_SCHEMA:
        raise RegistryWitnessRuntimeConfigError("registry witness public-key schema mismatch")
    if record.get("issuer") != "WORLD_SHEPHERD_REGISTRY_WITNESS":
        raise RegistryWitnessRuntimeConfigError("registry witness public-key issuer mismatch")
    if record.get("algorithm") != "Ed25519":
        raise RegistryWitnessRuntimeConfigError("registry witness public-key algorithm mismatch")
    witness_id = record.get("witness_id")
    key_id = record.get("key_id")
    namespace = record.get("namespace")
    if not isinstance(witness_id, str) or not _SAFE_ID.fullmatch(witness_id):
        raise RegistryWitnessRuntimeConfigError("registry witness id is invalid")
    if not isinstance(key_id, str) or not _SAFE_ID.fullmatch(key_id):
        raise RegistryWitnessRuntimeConfigError("registry witness key id is invalid")
    if not isinstance(namespace, str) or not _NAMESPACE.fullmatch(namespace):
        raise RegistryWitnessRuntimeConfigError("registry witness namespace is invalid")
    raw = _decode_key(record.get("public_key_b64url"))
    calculated = hashlib.sha256(raw).hexdigest()
    record_fingerprint = record.get("fingerprint_sha256")
    if not isinstance(record_fingerprint, str) or not _SHA256.fullmatch(record_fingerprint):
        raise RegistryWitnessRuntimeConfigError("registry witness key fingerprint is invalid")
    if calculated != record_fingerprint:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness public-key fingerprint does not match key material"
        )
    if not _SHA256.fullmatch(expected_fingerprint):
        raise RegistryWitnessRuntimeConfigError(
            f"{WITNESS_EXPECTED_FINGERPRINT_ENV} must be a lowercase SHA-256 digest"
        )
    if calculated != expected_fingerprint:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness key fingerprint does not match pinned expected fingerprint"
        )
    claims = record.get("claims_boundary")
    if not isinstance(claims, str) or not claims:
        raise RegistryWitnessRuntimeConfigError(
            "registry witness public-key claims boundary is missing"
        )
    return {
        "witness_id": witness_id,
        "key_id": key_id,
        "namespace": namespace,
        "public_key_b64url": str(record["public_key_b64url"]),
        "fingerprint_sha256": calculated,
    }


def load_registry_witness_client_from_environment() -> RegistryMonotonicWitnessClient:
    base_url = os.getenv(WITNESS_URL_ENV, "").strip()
    if not base_url:
        raise RegistryWitnessRuntimeConfigError(f"{WITNESS_URL_ENV} is required")
    token = _load_token(os.getenv(WITNESS_CLIENT_TOKEN_FILE_ENV, ""))
    expected_fingerprint = os.getenv(WITNESS_EXPECTED_FINGERPRINT_ENV, "").strip()
    key_record = _load_public_key_record(
        os.getenv(WITNESS_PUBLIC_KEY_FILE_ENV, ""),
        expected_fingerprint,
    )
    raw_timeout = os.getenv(WITNESS_TIMEOUT_ENV, "5").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise RegistryWitnessRuntimeConfigError(
            f"{WITNESS_TIMEOUT_ENV} must be a number"
        ) from exc

    verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={key_record["key_id"]: key_record["public_key_b64url"]},
        expected_witness_id=key_record["witness_id"],
        expected_namespace=key_record["namespace"],
    )
    ca_file = os.getenv(WITNESS_CA_FILE_ENV, "").strip()
    if ca_file:
        ca_bytes = _read_file(
            ca_file,
            env_name=WITNESS_CA_FILE_ENV,
            label="registry witness CA bundle",
            maximum=MAX_CA_BUNDLE_BYTES,
            secret=False,
        )
        try:
            ca_text = ca_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise RegistryWitnessRuntimeConfigError(
                "registry witness CA bundle must be PEM ASCII text"
            ) from exc
        try:
            ssl_context = ssl.create_default_context(cadata=ca_text)
        except ssl.SSLError as exc:
            raise RegistryWitnessRuntimeConfigError(
                "registry witness CA bundle could not initialize TLS trust"
            ) from exc
    else:
        ssl_context = ssl.create_default_context()

    transport = HttpsRegistryWitnessTransport(
        base_url=base_url,
        bearer_token=token,
        timeout_seconds=timeout,
        ssl_context=ssl_context,
    )
    return RegistryMonotonicWitnessClient(
        transport=transport,
        verifier=verifier,
    )


def prepare_remote_registry_witness_precondition_from_environment(
    store: DurableStore,
) -> RegistryWitnessPrecondition:
    client = load_registry_witness_client_from_environment()
    return prepare_registry_witness_precondition(store, client)
