from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any

from .audit_checkpoint import SaraAuditCheckpointError, SaraAuditCheckpointManager
from .audit_checkpoint_verify import verify_checkpoint_chain


AUDIT_EXTERNAL_ANCHOR_SCHEMA = "WS-SARA-AUDIT-EXTERNAL-ANCHOR-V1"
MAX_EXTERNAL_ANCHOR_BYTES = 32 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SaraAuditExternalAnchorError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _is_inside(candidate: Path, root: Path) -> bool:
    candidate = candidate.resolve(strict=False)
    root = root.resolve(strict=True)
    return candidate == root or root in candidate.parents


def build_external_anchor(manager: SaraAuditCheckpointManager) -> dict[str, Any]:
    bundles = manager._read_ledger()
    if not bundles:
        raise SaraAuditExternalAnchorError(
            "cannot export external anchor before a signed audit checkpoint exists"
        )
    verified = verify_checkpoint_chain(bundles, manager.fingerprint_sha256)
    latest = bundles[-1]["manifest"]
    anchor = {
        "schema": AUDIT_EXTERNAL_ANCHOR_SCHEMA,
        "issuer": "SARA",
        "purpose": "EXTERNAL_LATEST_AUDIT_CHECKPOINT_PIN",
        "checkpoint_sha256": verified["last_checkpoint_sha256"],
        "checkpoint_sequence": verified["last_sequence"],
        "checkpoint_record_count": verified["last_record_count"],
        "checkpoint_created_at": latest["created_at"],
        "key_id": verified["key_id"],
        "key_fingerprint_sha256": manager.fingerprint_sha256,
        "public_key": manager.public_key_record(),
        "claims_boundary": (
            "This file is a portable latest-checkpoint pin. Rollback resistance exists only "
            "when the anchor is retained in a trust boundary independent of local SARA data. "
            "The file itself is not WORM storage, a transparency log, or third-party attestation."
        ),
    }
    anchor["anchor_sha256"] = hashlib.sha256(_canonical(anchor)).hexdigest()
    return anchor


def _validate_anchor(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != AUDIT_EXTERNAL_ANCHOR_SCHEMA:
        raise SaraAuditExternalAnchorError("external audit anchor schema mismatch")
    if value.get("issuer") != "SARA" or value.get("purpose") != "EXTERNAL_LATEST_AUDIT_CHECKPOINT_PIN":
        raise SaraAuditExternalAnchorError("external audit anchor purpose mismatch")
    checkpoint = value.get("checkpoint_sha256")
    fingerprint = value.get("key_fingerprint_sha256")
    anchor_digest = value.get("anchor_sha256")
    for label, digest in (
        ("checkpoint digest", checkpoint),
        ("key fingerprint", fingerprint),
        ("anchor digest", anchor_digest),
    ):
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise SaraAuditExternalAnchorError(f"external audit anchor {label} is invalid")
    sequence = value.get("checkpoint_sequence")
    record_count = value.get("checkpoint_record_count")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SaraAuditExternalAnchorError("external audit anchor sequence is invalid")
    if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 1:
        raise SaraAuditExternalAnchorError("external audit anchor record count is invalid")
    key_id = value.get("key_id")
    if not isinstance(key_id, str) or not key_id:
        raise SaraAuditExternalAnchorError("external audit anchor key ID is invalid")
    public = value.get("public_key")
    if not isinstance(public, dict):
        raise SaraAuditExternalAnchorError("external audit anchor public-key record is missing")
    unsigned = dict(value)
    unsigned.pop("anchor_sha256", None)
    actual_anchor_digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if actual_anchor_digest != anchor_digest:
        raise SaraAuditExternalAnchorError("external audit anchor content digest mismatch")
    return value


def export_external_anchor(
    manager: SaraAuditCheckpointManager,
    output_path: str | Path,
) -> dict[str, Any]:
    path = Path(output_path)
    if not path.is_absolute():
        raise SaraAuditExternalAnchorError("external audit anchor path must be absolute")
    if _is_inside(path, manager.store.root):
        raise SaraAuditExternalAnchorError(
            "external audit anchor must be outside the SARA data directory"
        )
    if path.exists() or path.is_symlink():
        raise SaraAuditExternalAnchorError(
            "external audit anchor path already exists; use a new versioned path"
        )
    parent = path.parent
    if not parent.exists():
        raise SaraAuditExternalAnchorError("external audit anchor parent directory must exist")
    parent_status = parent.lstat()
    if stat.S_ISLNK(parent_status.st_mode) or not stat.S_ISDIR(parent_status.st_mode):
        raise SaraAuditExternalAnchorError(
            "external audit anchor parent must be a real directory"
        )

    anchor = build_external_anchor(manager)
    payload = json.dumps(anchor, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > MAX_EXTERNAL_ANCHOR_BYTES:
        raise SaraAuditExternalAnchorError("external audit anchor exceeds size limit")

    temp = parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temp,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise SaraAuditExternalAnchorError(
                "external audit anchor temporary file must be regular"
            )
        os.fchmod(descriptor, 0o600)
        data = payload.encode("utf-8")
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("external anchor write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temp, path)
        path.chmod(0o600)
        directory_fd = os.open(
            parent,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except (OSError, SaraAuditExternalAnchorError) as exc:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)
        if isinstance(exc, SaraAuditExternalAnchorError):
            raise
        raise SaraAuditExternalAnchorError(
            "unable to durably export external audit anchor"
        ) from exc
    return anchor


def load_external_anchor(path_value: str | Path) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_absolute():
        raise SaraAuditExternalAnchorError("external audit anchor path must be absolute")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise SaraAuditExternalAnchorError("unable to inspect external audit anchor") from exc
    if stat.S_ISLNK(link_status.st_mode) or not stat.S_ISREG(link_status.st_mode):
        raise SaraAuditExternalAnchorError("external audit anchor must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SaraAuditExternalAnchorError("unable to open external audit anchor securely") from exc
    try:
        status = os.fstat(descriptor)
        if (status.st_dev, status.st_ino) != (link_status.st_dev, link_status.st_ino):
            raise SaraAuditExternalAnchorError("external audit anchor changed during secure open")
        if status.st_size < 1 or status.st_size > MAX_EXTERNAL_ANCHOR_BYTES:
            raise SaraAuditExternalAnchorError("external audit anchor size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_EXTERNAL_ANCHOR_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_EXTERNAL_ANCHOR_BYTES:
        raise SaraAuditExternalAnchorError("external audit anchor exceeds size limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaraAuditExternalAnchorError("external audit anchor is invalid JSON") from exc
    return _validate_anchor(value)


def verify_with_external_anchor(
    manager: SaraAuditCheckpointManager,
    anchor_path: str | Path,
) -> dict[str, Any]:
    path = Path(anchor_path)
    if _is_inside(path, manager.store.root):
        raise SaraAuditExternalAnchorError(
            "verification anchor must be outside the SARA data directory"
        )
    anchor = load_external_anchor(path)
    if anchor["key_fingerprint_sha256"] != manager.fingerprint_sha256:
        raise SaraAuditExternalAnchorError(
            "external audit anchor key fingerprint does not match configured signer"
        )
    if anchor["key_id"] != manager.key_id:
        raise SaraAuditExternalAnchorError(
            "external audit anchor key ID does not match configured signer"
        )
    try:
        status = manager.verify_current(
            expected_latest_checkpoint_sha256=anchor["checkpoint_sha256"]
        )
    except SaraAuditCheckpointError:
        raise
    if status.get("latest_sequence") != anchor["checkpoint_sequence"]:
        raise SaraAuditExternalAnchorError(
            "external audit anchor checkpoint sequence does not match local verified chain"
        )
    if status.get("checkpointed_records") != anchor["checkpoint_record_count"]:
        raise SaraAuditExternalAnchorError(
            "external audit anchor record count does not match local verified chain"
        )
    return {
        "schema": "WS-SARA-AUDIT-EXTERNAL-ANCHOR-VERIFICATION-V1",
        "status": "PASS",
        "anchor_sha256": anchor["anchor_sha256"],
        "checkpoint_sha256": anchor["checkpoint_sha256"],
        "checkpoint_sequence": anchor["checkpoint_sequence"],
        "checkpoint_record_count": anchor["checkpoint_record_count"],
        "local_integrity_status": status["status"],
        "claims_boundary": (
            "PASS establishes agreement with this independently supplied anchor file. "
            "Trust still depends on retaining that anchor outside the local SARA storage boundary."
        ),
    }
