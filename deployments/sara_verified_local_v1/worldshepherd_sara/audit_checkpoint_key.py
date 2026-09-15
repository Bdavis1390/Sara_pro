from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV = "SARA_AUDIT_CHECKPOINT_PRIVATE_KEY_FILE"
AUDIT_CHECKPOINT_KEY_ID_ENV = "SARA_AUDIT_CHECKPOINT_KEY_ID"
MAX_AUDIT_CHECKPOINT_KEY_FILE_BYTES = 16 * 1024
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class SaraAuditCheckpointKeyConfigError(RuntimeError):
    pass


def load_audit_checkpoint_key_id() -> str:
    value = os.getenv(AUDIT_CHECKPOINT_KEY_ID_ENV, "").strip()
    if not _KEY_ID_PATTERN.fullmatch(value):
        raise SaraAuditCheckpointKeyConfigError(
            f"{AUDIT_CHECKPOINT_KEY_ID_ENV} must be 1-128 safe identifier characters"
        )
    return value


def load_audit_checkpoint_private_key() -> Ed25519PrivateKey:
    path_value = os.getenv(AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV, "").strip()
    if not path_value:
        raise SaraAuditCheckpointKeyConfigError(
            f"{AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV} is required"
        )
    path = Path(path_value)
    if not path.is_absolute():
        raise SaraAuditCheckpointKeyConfigError(
            f"{AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV} must be an absolute path"
        )
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise SaraAuditCheckpointKeyConfigError(
            "unable to inspect SARA audit checkpoint private key"
        ) from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise SaraAuditCheckpointKeyConfigError(
            "SARA audit checkpoint private key must not be a symbolic link"
        )

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SaraAuditCheckpointKeyConfigError(
            "unable to open SARA audit checkpoint private key securely"
        ) from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise SaraAuditCheckpointKeyConfigError(
                "SARA audit checkpoint private key must be a regular file"
            )
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise SaraAuditCheckpointKeyConfigError(
                "SARA audit checkpoint private key changed during secure open"
            )
        if status.st_uid != os.geteuid():
            raise SaraAuditCheckpointKeyConfigError(
                "SARA audit checkpoint private key must be owned by the service UID"
            )
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise SaraAuditCheckpointKeyConfigError(
                "SARA audit checkpoint private key must not grant group/other permissions"
            )
        if status.st_size < 1 or status.st_size > MAX_AUDIT_CHECKPOINT_KEY_FILE_BYTES:
            raise SaraAuditCheckpointKeyConfigError(
                "SARA audit checkpoint private key size is invalid"
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_AUDIT_CHECKPOINT_KEY_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if len(data) > MAX_AUDIT_CHECKPOINT_KEY_FILE_BYTES:
        raise SaraAuditCheckpointKeyConfigError(
            "SARA audit checkpoint private key is too large"
        )
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise SaraAuditCheckpointKeyConfigError(
            "SARA audit checkpoint private key must be an unencrypted PEM private key"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SaraAuditCheckpointKeyConfigError(
            "SARA audit checkpoint private key must contain Ed25519 material"
        )
    return key
