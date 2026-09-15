from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import Any

from .audit_checkpoint import (
    AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA,
    MAX_CHECKPOINT_LINE_BYTES,
    audit_chain_seed,
    audit_chain_step,
    audit_record_digest,
)
from .audit_checkpoint_anchor import load_external_anchor
from .audit_checkpoint_verify import (
    SaraAuditCheckpointVerificationError,
    verify_checkpoint_chain,
)
from .limits import MAX_AUDIT_LINE_BYTES


OFFLINE_VERIFICATION_SCHEMA = "WS-SARA-AUDIT-OFFLINE-VERIFICATION-V1"


class SaraAuditOfflineVerificationError(ValueError):
    pass


def _open_regular(path_value: str | Path, label: str) -> tuple[int, Path]:
    path = Path(path_value)
    if not path.is_absolute():
        raise SaraAuditOfflineVerificationError(f"{label} path must be absolute")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise SaraAuditOfflineVerificationError(f"unable to inspect {label}") from exc
    if stat.S_ISLNK(link_status.st_mode) or not stat.S_ISREG(link_status.st_mode):
        raise SaraAuditOfflineVerificationError(f"{label} must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SaraAuditOfflineVerificationError(f"unable to open {label} securely") from exc
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (link_status.st_dev, link_status.st_ino):
            raise SaraAuditOfflineVerificationError(f"{label} changed during secure open")
        if not stat.S_ISREG(opened.st_mode):
            raise SaraAuditOfflineVerificationError(f"{label} must remain a regular file")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor, path


def _load_checkpoint_ledger(path_value: str | Path) -> list[dict[str, Any]]:
    descriptor, _path = _open_regular(path_value, "audit checkpoint ledger")
    bundles: list[dict[str, Any]] = []
    with os.fdopen(descriptor, "rb") as handle:
        while True:
            raw = handle.readline(MAX_CHECKPOINT_LINE_BYTES + 2)
            if not raw:
                break
            if len(raw) > MAX_CHECKPOINT_LINE_BYTES + 1:
                raise SaraAuditOfflineVerificationError(
                    "audit checkpoint ledger line exceeds configured limit"
                )
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            if not raw:
                raise SaraAuditOfflineVerificationError(
                    "audit checkpoint ledger contains an empty line"
                )
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SaraAuditOfflineVerificationError(
                    "audit checkpoint ledger contains invalid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise SaraAuditOfflineVerificationError(
                    "audit checkpoint ledger entry must be a JSON object"
                )
            bundles.append(value)
    if not bundles:
        raise SaraAuditOfflineVerificationError(
            "audit checkpoint ledger contains no signed checkpoints"
        )
    return bundles


def _validate_anchor_public_key(anchor: dict[str, Any]) -> None:
    public = anchor.get("public_key")
    if not isinstance(public, dict) or public.get("schema") != AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA:
        raise SaraAuditOfflineVerificationError("external anchor public-key schema mismatch")
    if public.get("issuer") != "SARA" or public.get("purpose") != "APPLICATION_AUDIT_CHECKPOINT_SIGNING":
        raise SaraAuditOfflineVerificationError("external anchor public-key purpose mismatch")
    if public.get("algorithm") != "Ed25519":
        raise SaraAuditOfflineVerificationError("external anchor public-key algorithm mismatch")
    if public.get("key_id") != anchor.get("key_id"):
        raise SaraAuditOfflineVerificationError("external anchor public-key ID mismatch")
    if public.get("fingerprint_sha256") != anchor.get("key_fingerprint_sha256"):
        raise SaraAuditOfflineVerificationError(
            "external anchor public-key fingerprint field mismatch"
        )
    encoded = public.get("public_key_b64url")
    if not isinstance(encoded, str) or not encoded:
        raise SaraAuditOfflineVerificationError("external anchor public key is missing")
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        public_bytes = base64.b64decode(
            padded.encode("ascii"), altchars=b"-_", validate=True
        )
    except (ValueError, UnicodeEncodeError) as exc:
        raise SaraAuditOfflineVerificationError(
            "external anchor public key is not valid base64url"
        ) from exc
    if len(public_bytes) != 32:
        raise SaraAuditOfflineVerificationError(
            "external anchor Ed25519 public key must be 32 bytes"
        )
    import hashlib

    if hashlib.sha256(public_bytes).hexdigest() != anchor.get("key_fingerprint_sha256"):
        raise SaraAuditOfflineVerificationError(
            "external anchor public key does not match pinned fingerprint"
        )


def _scan_audit(
    path_value: str | Path,
    checkpointed_records: int,
) -> dict[str, Any]:
    if checkpointed_records < 1:
        raise SaraAuditOfflineVerificationError(
            "checkpointed record count must be positive"
        )
    descriptor, _path = _open_regular(path_value, "SARA audit export")
    state = audit_chain_seed()
    current_records = 0
    prefix_head: str | None = None
    prefix_last_record: str | None = None
    with os.fdopen(descriptor, "rb") as handle:
        while True:
            raw = handle.readline(MAX_AUDIT_LINE_BYTES + 2)
            if not raw:
                break
            if len(raw) > MAX_AUDIT_LINE_BYTES + 1:
                raise SaraAuditOfflineVerificationError(
                    "SARA audit record exceeds configured line limit"
                )
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            if not raw:
                raise SaraAuditOfflineVerificationError(
                    "SARA audit export contains an empty record"
                )
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SaraAuditOfflineVerificationError(
                    "SARA audit export contains invalid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise SaraAuditOfflineVerificationError(
                    "SARA audit export record must be a JSON object"
                )
            try:
                digest = audit_record_digest(value)
            except Exception as exc:
                raise SaraAuditOfflineVerificationError(
                    "SARA audit export record failed semantic validation"
                ) from exc
            current_records += 1
            state = audit_chain_step(state, current_records, digest)
            if current_records == checkpointed_records:
                prefix_head = state.hex()
                prefix_last_record = digest.hex()

    if current_records < checkpointed_records:
        raise SaraAuditOfflineVerificationError(
            "SARA audit rollback/truncation detected relative to external anchor"
        )
    if prefix_head is None or prefix_last_record is None:
        raise SaraAuditOfflineVerificationError(
            "unable to reconstruct externally anchored SARA audit prefix"
        )
    return {
        "current_records": current_records,
        "checkpointed_records": checkpointed_records,
        "uncheckpointed_records": current_records - checkpointed_records,
        "prefix_chain_head_sha256": prefix_head,
        "prefix_last_record_sha256": prefix_last_record,
    }


def verify_offline_export(
    *,
    audit_path: str | Path,
    checkpoint_ledger_path: str | Path,
    external_anchor_path: str | Path,
) -> dict[str, Any]:
    """Verify an exported SARA audit without loading any private signing key.

    The external anchor is the trust input. It must have been retained in a
    boundary independent of the SARA audit/checkpoint storage for rollback
    detection to have meaning. Verification is read-only and does not require
    a running SARA service or SARA signing-key configuration.
    """

    anchor = load_external_anchor(external_anchor_path)
    _validate_anchor_public_key(anchor)
    bundles = _load_checkpoint_ledger(checkpoint_ledger_path)
    try:
        chain = verify_checkpoint_chain(
            bundles,
            anchor["key_fingerprint_sha256"],
            expected_latest_checkpoint_sha256=anchor["checkpoint_sha256"],
        )
    except SaraAuditCheckpointVerificationError as exc:
        raise SaraAuditOfflineVerificationError(str(exc)) from exc

    if chain["last_sequence"] != anchor["checkpoint_sequence"]:
        raise SaraAuditOfflineVerificationError(
            "external anchor checkpoint sequence does not match signed ledger"
        )
    if chain["last_record_count"] != anchor["checkpoint_record_count"]:
        raise SaraAuditOfflineVerificationError(
            "external anchor record count does not match signed ledger"
        )
    if chain["key_id"] != anchor["key_id"]:
        raise SaraAuditOfflineVerificationError(
            "external anchor key ID does not match signed ledger"
        )

    latest_manifest = bundles[-1].get("manifest")
    if not isinstance(latest_manifest, dict):
        raise SaraAuditOfflineVerificationError(
            "latest checkpoint manifest is missing"
        )
    audit = _scan_audit(audit_path, anchor["checkpoint_record_count"])
    if audit["prefix_chain_head_sha256"] != latest_manifest.get(
        "audit_chain_head_sha256"
    ):
        raise SaraAuditOfflineVerificationError(
            "SARA audit checkpointed prefix integrity mismatch"
        )
    if audit["prefix_last_record_sha256"] != latest_manifest.get(
        "last_record_sha256"
    ):
        raise SaraAuditOfflineVerificationError(
            "SARA audit checkpointed last-record digest mismatch"
        )

    status = (
        "PASS"
        if audit["uncheckpointed_records"] == 0
        else "PASS_WITH_UNCHECKPOINTED_TAIL"
    )
    return {
        "schema": OFFLINE_VERIFICATION_SCHEMA,
        "status": status,
        "anchor_sha256": anchor["anchor_sha256"],
        "checkpoint_sha256": anchor["checkpoint_sha256"],
        "checkpoint_sequence": anchor["checkpoint_sequence"],
        "checkpointed_records": audit["checkpointed_records"],
        "current_records": audit["current_records"],
        "uncheckpointed_records": audit["uncheckpointed_records"],
        "key_id": anchor["key_id"],
        "key_fingerprint_sha256": anchor["key_fingerprint_sha256"],
        "private_key_required": False,
        "running_sara_required": False,
        "claims_boundary": (
            "PASS proves consistency of the supplied audit export and signed checkpoint ledger "
            "with the supplied external rollback pin. It does not prove WORM retention, "
            "third-party attestation, signer non-compromise, or authenticity of an anchor that "
            "was not itself retained in an independently trusted boundary."
        ),
    }
