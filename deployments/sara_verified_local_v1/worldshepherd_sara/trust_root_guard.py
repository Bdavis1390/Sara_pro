from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
from typing import Any

from .models import AuditRecord
from .storage import DurableStore


PRIME_TRUST_ROOT_STATE_KEY = "PRIME_TRUST_ROOT_STATE"
PRIME_TRUST_ROOT_SCHEMA = "WS-PRIME-TRUST-ROOT-V1"
PRIME_TRUST_ROOT_EPOCH_ENV = "PRIME_SENTINEL_TRUST_EPOCH"

_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")


class PrimeTrustRootError(RuntimeError):
    pass


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PrimeTrustRootError("PRIME trust-root state is not canonical JSON") from exc


def _decode_public_key(value: str, *, key_id: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(
            padded,
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise PrimeTrustRootError(
            f"PRIME public key {key_id} is not valid base64url"
        ) from exc
    if len(decoded) != 32:
        raise PrimeTrustRootError(
            f"PRIME public key {key_id} must decode to 32 bytes"
        )
    return decoded


def _safe_id(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not _COMPONENT.fullmatch(value):
        raise PrimeTrustRootError(f"{label} is invalid")
    return value


def _parse_public_keys(raw: str) -> dict[str, str]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise PrimeTrustRootError(
            "PRIME_SENTINEL_PUBLIC_KEYS_JSON is invalid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise PrimeTrustRootError(
            "PRIME_SENTINEL_PUBLIC_KEYS_JSON must be a JSON object"
        )

    fingerprints: dict[str, str] = {}
    for raw_id, encoded in parsed.items():
        if not isinstance(raw_id, str) or not isinstance(encoded, str):
            raise PrimeTrustRootError(
                "PRIME public-key configuration must map string IDs to strings"
            )
        key_id = _safe_id(raw_id, label="PRIME signing key ID")
        key_bytes = _decode_public_key(encoded, key_id=key_id)
        fingerprints[key_id] = hashlib.sha256(key_bytes).hexdigest()
    return dict(sorted(fingerprints.items()))


def _parse_revocations(raw: str) -> list[str]:
    values = {
        _safe_id(item.strip(), label="revoked PRIME signing key ID")
        for item in raw.split(",")
        if item.strip()
    }
    return sorted(values)


def trust_root_state_from_environment(
    environ: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    values = os.environ if environ is None else environ
    public_fingerprints = _parse_public_keys(
        str(values.get("PRIME_SENTINEL_PUBLIC_KEYS_JSON", "{}")).strip() or "{}"
    )
    revoked = _parse_revocations(
        str(values.get("PRIME_SENTINEL_REVOKED_KEY_IDS", ""))
    )
    raw_epoch = str(values.get(PRIME_TRUST_ROOT_EPOCH_ENV, "")).strip()

    if not public_fingerprints and not revoked and not raw_epoch:
        return None

    if not raw_epoch:
        raise PrimeTrustRootError(
            f"{PRIME_TRUST_ROOT_EPOCH_ENV} is required when PRIME trust roots are configured"
        )
    try:
        epoch = int(raw_epoch, 10)
    except ValueError as exc:
        raise PrimeTrustRootError(
            f"{PRIME_TRUST_ROOT_EPOCH_ENV} must be a positive integer"
        ) from exc
    if epoch < 1:
        raise PrimeTrustRootError(
            f"{PRIME_TRUST_ROOT_EPOCH_ENV} must be a positive integer"
        )

    material = {
        "key_fingerprints_sha256": public_fingerprints,
        "revoked_key_ids": revoked,
    }
    digest = hashlib.sha256(_canonical_json(material)).hexdigest()
    return {
        "schema": PRIME_TRUST_ROOT_SCHEMA,
        "epoch": epoch,
        "material_sha256": digest,
        **material,
    }


def _validated_stored_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PrimeTrustRootError("stored PRIME trust-root state is not an object")
    expected_keys = {
        "schema",
        "epoch",
        "material_sha256",
        "key_fingerprints_sha256",
        "revoked_key_ids",
    }
    if set(value) != expected_keys:
        raise PrimeTrustRootError(
            "stored PRIME trust-root state contains unexpected fields"
        )
    if value.get("schema") != PRIME_TRUST_ROOT_SCHEMA:
        raise PrimeTrustRootError("stored PRIME trust-root schema mismatch")

    epoch = value.get("epoch")
    digest = value.get("material_sha256")
    keys = value.get("key_fingerprints_sha256")
    revoked = value.get("revoked_key_ids")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise PrimeTrustRootError("stored PRIME trust-root epoch is invalid")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise PrimeTrustRootError("stored PRIME trust-root digest is invalid")
    if not isinstance(keys, dict) or not all(
        isinstance(key_id, str)
        and _COMPONENT.fullmatch(key_id)
        and isinstance(fingerprint, str)
        and len(fingerprint) == 64
        and all(ch in "0123456789abcdef" for ch in fingerprint)
        for key_id, fingerprint in keys.items()
    ):
        raise PrimeTrustRootError("stored PRIME key fingerprints are invalid")
    if not isinstance(revoked, list) or not all(
        isinstance(item, str) and _COMPONENT.fullmatch(item) for item in revoked
    ):
        raise PrimeTrustRootError("stored PRIME revocation list is invalid")
    if revoked != sorted(set(revoked)):
        raise PrimeTrustRootError("stored PRIME revocation list is not canonical")

    material = {
        "key_fingerprints_sha256": dict(sorted(keys.items())),
        "revoked_key_ids": sorted(set(revoked)),
    }
    expected_digest = hashlib.sha256(_canonical_json(material)).hexdigest()
    if digest != expected_digest:
        raise PrimeTrustRootError("stored PRIME trust-root digest does not match material")
    return {
        "schema": PRIME_TRUST_ROOT_SCHEMA,
        "epoch": epoch,
        "material_sha256": digest,
        **material,
    }


def reconcile_prime_trust_root(
    registry: dict[str, Any],
    current: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    stored_raw = registry.get(PRIME_TRUST_ROOT_STATE_KEY)

    if stored_raw is None:
        if current is None:
            return None, {
                "status": "UNCONFIGURED",
                "epoch": None,
                "material_sha256": None,
            }
        state = _validated_stored_state(current)
        return {PRIME_TRUST_ROOT_STATE_KEY: state}, {
            "status": "INITIALIZED",
            "epoch": state["epoch"],
            "material_sha256": state["material_sha256"],
        }

    stored = _validated_stored_state(stored_raw)
    if current is None:
        raise PrimeTrustRootError(
            "PRIME trust-root configuration is missing after prior initialization"
        )
    candidate = _validated_stored_state(current)

    if candidate["epoch"] < stored["epoch"]:
        raise PrimeTrustRootError("PRIME trust-root epoch rollback detected")

    if candidate["epoch"] == stored["epoch"]:
        if candidate["material_sha256"] != stored["material_sha256"]:
            raise PrimeTrustRootError(
                "PRIME trust-root material changed without epoch advance"
            )
        return None, {
            "status": "MATCHED",
            "epoch": stored["epoch"],
            "material_sha256": stored["material_sha256"],
        }

    old_keys = stored["key_fingerprints_sha256"]
    new_keys = candidate["key_fingerprints_sha256"]
    old_revoked = set(stored["revoked_key_ids"])
    new_revoked = set(candidate["revoked_key_ids"])

    if not old_revoked.issubset(new_revoked):
        raise PrimeTrustRootError("PRIME signing-key revocation rollback detected")

    for key_id in sorted(set(old_keys).intersection(new_keys)):
        if old_keys[key_id] != new_keys[key_id]:
            raise PrimeTrustRootError(
                f"PRIME signing key ID {key_id} cannot be rebound to new key material"
            )

    removed_keys = set(old_keys) - set(new_keys)
    if not removed_keys.issubset(new_revoked):
        raise PrimeTrustRootError(
            "removed PRIME signing keys must remain explicitly revoked"
        )

    return {PRIME_TRUST_ROOT_STATE_KEY: candidate}, {
        "status": "ADVANCED",
        "epoch": candidate["epoch"],
        "previous_epoch": stored["epoch"],
        "material_sha256": candidate["material_sha256"],
        "previous_material_sha256": stored["material_sha256"],
    }


def guard_prime_trust_root(
    store: DurableStore,
    *,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    current = trust_root_state_from_environment(environ)

    def operation(
        registry: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        return reconcile_prime_trust_root(registry, current)

    result = store.transact_registry(operation)
    store.append_audit(
        AuditRecord.create(
            event="prime_trust_root_guard_evaluated",
            actor="system",
            payload=result,
        )
    )
    return result
