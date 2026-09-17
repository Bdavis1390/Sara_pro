from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import stat
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryWitnessConflict,
    RegistryWitnessCoordinates,
    RegistryWitnessRollbackDetected,
    ZERO_HASH,
    build_signed_witness_receipt,
)


WITNESS_DB_SCHEMA = "WS-SARA-REGISTRY-REMOTE-WITNESS-LEDGER-V1"
WITNESS_PUBLIC_KEY_SCHEMA = "WS-SARA-REGISTRY-WITNESS-PUBLIC-KEY-V1"
WITNESS_ID_ENV = "REGISTRY_WITNESS_ID"
WITNESS_NAMESPACE_ENV = "REGISTRY_WITNESS_NAMESPACE"
WITNESS_KEY_FILE_ENV = "REGISTRY_WITNESS_PRIVATE_KEY_FILE"
WITNESS_KEY_ID_ENV = "REGISTRY_WITNESS_SIGNING_KEY_ID"
WITNESS_TOKEN_FILE_ENV = "REGISTRY_WITNESS_SERVICE_TOKEN_FILE"
WITNESS_DB_PATH_ENV = "REGISTRY_WITNESS_DB_PATH"
MAX_KEY_FILE_BYTES = 16 * 1024
MAX_TOKEN_FILE_BYTES = 4 * 1024
MIN_TOKEN_CHARS = 32
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_NAMESPACE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RegistryWitnessServiceConfigError(RuntimeError):
    pass


class RegistryWitnessLedgerError(RuntimeError):
    pass


class WitnessAdvanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation: int = Field(ge=0)
    state_root_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    commit_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class RegistryWitnessLedger:
    """Durable monotonic receipt ledger for one configured witness identity.

    The ledger gives the service durable monotonic state. Hosting this ledger in
    a separate process is not, by itself, evidence of independent administration
    or an external trust domain; deployment evidence must establish that.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        private_key: Ed25519PrivateKey,
        witness_id: str,
        key_id: str,
        namespace: str,
    ) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.db_path.parent, 0o700)
        self._private_key = private_key
        self.witness_id = _validate_id(witness_id, "witness id")
        self.key_id = _validate_id(key_id, "witness key id")
        self.namespace = _validate_namespace(namespace)
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS witness_receipts (
                    namespace TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation >= 0),
                    receipt_sha256 TEXT NOT NULL UNIQUE,
                    receipt_json TEXT NOT NULL,
                    PRIMARY KEY(namespace, generation)
                );
                CREATE TABLE IF NOT EXISTS witness_heads (
                    namespace TEXT PRIMARY KEY,
                    generation INTEGER NOT NULL CHECK(generation >= 0),
                    receipt_sha256 TEXT NOT NULL,
                    FOREIGN KEY(namespace, generation)
                        REFERENCES witness_receipts(namespace, generation),
                    FOREIGN KEY(receipt_sha256)
                        REFERENCES witness_receipts(receipt_sha256)
                );
                """
            )
            required = {
                "schema": WITNESS_DB_SCHEMA,
                "witness_id": self.witness_id,
                "namespace": self.namespace,
                "key_id": self.key_id,
                "key_fingerprint_sha256": self.fingerprint_sha256,
            }
            for name, expected in required.items():
                row = connection.execute(
                    "SELECT value FROM metadata WHERE name=?",
                    (name,),
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO metadata(name,value) VALUES(?,?)",
                        (name, expected),
                    )
                elif row["value"] != expected:
                    raise RegistryWitnessServiceConfigError(
                        f"witness ledger metadata mismatch for {name}"
                    )
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        os.chmod(self.db_path, 0o600)

    @staticmethod
    def _decode_receipt(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        try:
            value = json.loads(row["receipt_json"])
        except json.JSONDecodeError as exc:
            raise RegistryWitnessLedgerError("stored witness receipt is invalid JSON") from exc
        if not isinstance(value, dict):
            raise RegistryWitnessLedgerError("stored witness receipt is not an object")
        return value

    def read_head(self) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT r.receipt_json FROM witness_heads h "
                "JOIN witness_receipts r ON r.namespace=h.namespace "
                "AND r.generation=h.generation "
                "WHERE h.namespace=?",
                (self.namespace,),
            ).fetchone()
            return self._decode_receipt(row)
        finally:
            connection.close()

    def witness(self, coordinates: RegistryWitnessCoordinates) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT h.generation, h.receipt_sha256, r.receipt_json "
                "FROM witness_heads h "
                "JOIN witness_receipts r ON r.namespace=h.namespace "
                "AND r.generation=h.generation "
                "WHERE h.namespace=?",
                (self.namespace,),
            ).fetchone()
            current = self._decode_receipt(row)
            if current is not None:
                current_generation = int(current["generation"])
                if coordinates.generation < current_generation:
                    raise RegistryWitnessRollbackDetected(
                        "remote witness refuses a generation lower than its durable head"
                    )
                if coordinates.generation == current_generation:
                    if (
                        coordinates.state_root_sha256 != current["state_root_sha256"]
                        or coordinates.commit_hash != current["commit_hash"]
                    ):
                        raise RegistryWitnessConflict(
                            "remote witness refuses conflicting checkpoint coordinates at the same generation"
                        )
                    connection.commit()
                    return current
                previous = str(current["receipt_sha256"])
            else:
                previous = ZERO_HASH

            receipt = build_signed_witness_receipt(
                private_key=self._private_key,
                witness_id=self.witness_id,
                key_id=self.key_id,
                namespace=self.namespace,
                coordinates=coordinates,
                previous_receipt_sha256=previous,
                witness_mode=REMOTE_WITNESS_MODE,
            )
            receipt_json = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "INSERT INTO witness_receipts(namespace,generation,receipt_sha256,receipt_json) "
                "VALUES(?,?,?,?)",
                (
                    self.namespace,
                    coordinates.generation,
                    receipt["receipt_sha256"],
                    receipt_json,
                ),
            )
            connection.execute(
                "INSERT INTO witness_heads(namespace,generation,receipt_sha256) VALUES(?,?,?) "
                "ON CONFLICT(namespace) DO UPDATE SET "
                "generation=excluded.generation, receipt_sha256=excluded.receipt_sha256",
                (
                    self.namespace,
                    coordinates.generation,
                    receipt["receipt_sha256"],
                ),
            )
            connection.commit()
            return receipt
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()


class RegistryWitnessService:
    def __init__(
        self,
        *,
        ledger: RegistryWitnessLedger,
        service_token: str,
    ) -> None:
        self.ledger = ledger
        if len(service_token) < MIN_TOKEN_CHARS or service_token != service_token.strip():
            raise RegistryWitnessServiceConfigError(
                f"registry witness service token must be at least {MIN_TOKEN_CHARS} characters"
            )
        self.service_token = service_token

    @classmethod
    def from_environment(cls) -> "RegistryWitnessService":
        private_key = _load_private_key_file(os.getenv(WITNESS_KEY_FILE_ENV, ""))
        witness_id = _load_required_id(WITNESS_ID_ENV)
        key_id = _load_required_id(WITNESS_KEY_ID_ENV)
        namespace = os.getenv(WITNESS_NAMESPACE_ENV, "").strip()
        if not _NAMESPACE.fullmatch(namespace):
            raise RegistryWitnessServiceConfigError(
                f"{WITNESS_NAMESPACE_ENV} must be 1-256 safe namespace characters"
            )
        db_path = os.getenv(WITNESS_DB_PATH_ENV, "").strip()
        if not db_path or not Path(db_path).is_absolute():
            raise RegistryWitnessServiceConfigError(
                f"{WITNESS_DB_PATH_ENV} must be an absolute path"
            )
        token = _load_service_token_file(os.getenv(WITNESS_TOKEN_FILE_ENV, ""))
        return cls(
            ledger=RegistryWitnessLedger(
                db_path,
                private_key=private_key,
                witness_id=witness_id,
                key_id=key_id,
                namespace=namespace,
            ),
            service_token=token,
        )

    def public_key_record(self) -> dict[str, Any]:
        return {
            "schema": WITNESS_PUBLIC_KEY_SCHEMA,
            "issuer": "WORLD_SHEPHERD_REGISTRY_WITNESS",
            "witness_id": self.ledger.witness_id,
            "namespace": self.ledger.namespace,
            "algorithm": "Ed25519",
            "key_id": self.ledger.key_id,
            "public_key_b64url": self.ledger.public_key_b64url,
            "fingerprint_sha256": self.ledger.fingerprint_sha256,
            "claims_boundary": (
                "Public key identity only. It does not establish independent administration, "
                "external hosting, WORM retention, hardware-backed custody, or third-party attestation."
            ),
        }


def create_registry_witness_app(service: RegistryWitnessService) -> FastAPI:
    app = FastAPI(title="Worldshepherd Registry Monotonic Witness", version="1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "registry-monotonic-witness",
            "witness_id": service.ledger.witness_id,
            "namespace": service.ledger.namespace,
            "witness_mode": REMOTE_WITNESS_MODE,
            "independence_verified": False,
        }

    @app.get("/v1/public-key")
    def public_key() -> dict[str, Any]:
        return service.public_key_record()

    @app.get("/v1/head")
    def head(request: Request) -> dict[str, Any]:
        _require_bearer(request, service.service_token)
        receipt = service.ledger.read_head()
        if receipt is None:
            raise HTTPException(status_code=404, detail={"code": "NO_WITNESS_HEAD"})
        return receipt

    @app.post("/v1/witness")
    def witness(body: WitnessAdvanceRequest, request: Request) -> dict[str, Any]:
        _require_bearer(request, service.service_token)
        coordinates = RegistryWitnessCoordinates(
            generation=body.generation,
            state_root_sha256=body.state_root_sha256,
            commit_hash=body.commit_hash,
        )
        try:
            return service.ledger.witness(coordinates)
        except RegistryWitnessRollbackDetected as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "ROLLBACK_DETECTED", "message": str(exc)},
            ) from exc
        except RegistryWitnessConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "WITNESS_CONFLICT", "message": str(exc)},
            ) from exc

    return app


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _validate_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise RegistryWitnessServiceConfigError(f"{label} is invalid")
    return value


def _validate_namespace(value: Any) -> str:
    if not isinstance(value, str) or not _NAMESPACE.fullmatch(value):
        raise RegistryWitnessServiceConfigError("witness namespace is invalid")
    return value


def _load_required_id(env_name: str) -> str:
    value = os.getenv(env_name, "").strip()
    if not _SAFE_ID.fullmatch(value):
        raise RegistryWitnessServiceConfigError(
            f"{env_name} must be 1-128 safe identifier characters"
        )
    return value


def _read_owned_secret_file(
    path_value: str,
    *,
    env_name: str,
    label: str,
    max_bytes: int,
) -> bytes:
    if not path_value:
        raise RegistryWitnessServiceConfigError(f"{env_name} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise RegistryWitnessServiceConfigError(f"{env_name} must be an absolute path")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise RegistryWitnessServiceConfigError(f"unable to inspect {label}") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise RegistryWitnessServiceConfigError(f"{label} must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RegistryWitnessServiceConfigError(f"unable to open {label} securely") from exc
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise RegistryWitnessServiceConfigError(f"{label} must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (file_status.st_dev, file_status.st_ino):
            raise RegistryWitnessServiceConfigError(f"{label} changed during secure open")
        if file_status.st_uid != os.geteuid():
            raise RegistryWitnessServiceConfigError(f"{label} must be owned by the service UID")
        if stat.S_IMODE(file_status.st_mode) & 0o077:
            raise RegistryWitnessServiceConfigError(
                f"{label} must not grant group/other permissions"
            )
        if file_status.st_size < 1 or file_status.st_size > max_bytes:
            raise RegistryWitnessServiceConfigError(f"{label} size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(max_bytes + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > max_bytes:
        raise RegistryWitnessServiceConfigError(f"{label} is too large")
    return data


def _load_private_key_file(path_value: str) -> Ed25519PrivateKey:
    data = _read_owned_secret_file(
        path_value,
        env_name=WITNESS_KEY_FILE_ENV,
        label="registry witness private-key file",
        max_bytes=MAX_KEY_FILE_BYTES,
    )
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise RegistryWitnessServiceConfigError(
            "registry witness private-key file must contain an unencrypted PEM private key"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise RegistryWitnessServiceConfigError(
            "registry witness private-key file must contain an Ed25519 private key"
        )
    return key


def _load_service_token_file(path_value: str) -> str:
    data = _read_owned_secret_file(
        path_value,
        env_name=WITNESS_TOKEN_FILE_ENV,
        label="registry witness service-token file",
        max_bytes=MAX_TOKEN_FILE_BYTES,
    )
    try:
        token = data.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise RegistryWitnessServiceConfigError(
            "registry witness service-token file must be UTF-8 text"
        ) from exc
    if not token or token != token.strip() or "\n" in token or "\r" in token:
        raise RegistryWitnessServiceConfigError(
            "registry witness service-token file must contain one token"
        )
    if len(token) < MIN_TOKEN_CHARS:
        raise RegistryWitnessServiceConfigError(
            f"registry witness service token must be at least {MIN_TOKEN_CHARS} characters"
        )
    for other_name in ("SARA_ADMIN_TOKEN", "SARA_RELAY_TOKEN"):
        other = os.getenv(other_name, "")
        if other and hmac.compare_digest(token, other):
            raise RegistryWitnessServiceConfigError(
                f"registry witness service token must be independent from {other_name}"
            )
    return token


def _require_bearer(request: Request, expected_token: str) -> None:
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied:
        raise HTTPException(status_code=401, detail="registry witness bearer token required")
    if not hmac.compare_digest(supplied, expected_token):
        raise HTTPException(status_code=403, detail="registry witness bearer token rejected")
