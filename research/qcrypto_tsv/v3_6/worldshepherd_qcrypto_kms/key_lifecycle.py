"""Key lifecycle, rotation, and rollback-resistance controls for QCRYPTO."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable, Mapping

from .crypto_agility import CryptoAgilityError, normalize_algorithm_id


class KeyLifecycleError(RuntimeError):
    pass


class KeyState(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"


def _time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise KeyLifecycleError("key lifecycle timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise KeyLifecycleError("key lifecycle timestamp must include an offset")
    return parsed.astimezone(dt.timezone.utc)


@dataclass(frozen=True)
class KeyRecord:
    provider_id: str
    key_fingerprint_sha256: str
    algorithm_id: str
    generation: int
    state: KeyState
    not_before: str
    not_after: str | None = None
    predecessor_fingerprint_sha256: str | None = None

    def canonical_dict(self) -> dict:
        if not self.provider_id or len(self.provider_id) > 128:
            raise KeyLifecycleError("provider_id is required and limited to 128 characters")
        fp = self.key_fingerprint_sha256.lower()
        if len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
            raise KeyLifecycleError("key fingerprint must be 32-byte hex")
        try:
            alg = normalize_algorithm_id(self.algorithm_id)
        except CryptoAgilityError as exc:
            raise KeyLifecycleError(str(exc)) from exc
        if self.generation < 1:
            raise KeyLifecycleError("key generation must be >= 1")
        start = _time(self.not_before)
        end = _time(self.not_after) if self.not_after else None
        if end is not None and end <= start:
            raise KeyLifecycleError("not_after must be after not_before")
        pred = self.predecessor_fingerprint_sha256
        if pred is not None:
            pred = pred.lower()
            if len(pred) != 64 or any(c not in "0123456789abcdef" for c in pred):
                raise KeyLifecycleError("predecessor fingerprint must be 32-byte hex")
            if pred == fp:
                raise KeyLifecycleError("a key cannot name itself as predecessor")
        return {
            "provider_id": self.provider_id,
            "key_fingerprint_sha256": fp,
            "algorithm_id": alg,
            "generation": self.generation,
            "state": self.state.value,
            "not_before": start.isoformat().replace("+00:00", "Z"),
            "not_after": None if end is None else end.isoformat().replace("+00:00", "Z"),
            "predecessor_fingerprint_sha256": pred,
        }

    @property
    def record_sha256(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-KEY-RECORD-V1\x00" + body).hexdigest()


@dataclass(frozen=True)
class KeyRegistry:
    records: tuple[KeyRecord, ...]

    def __post_init__(self) -> None:
        seen_fp: set[str] = set()
        by_provider_alg: dict[tuple[str, str], list[KeyRecord]] = {}
        for record in self.records:
            data = record.canonical_dict()
            fp = data["key_fingerprint_sha256"]
            if fp in seen_fp:
                raise KeyLifecycleError("duplicate key fingerprint in registry")
            seen_fp.add(fp)
            key = (data["provider_id"], data["algorithm_id"])
            by_provider_alg.setdefault(key, []).append(record)
        for key, rows in by_provider_alg.items():
            generations = [r.generation for r in rows]
            if len(set(generations)) != len(generations):
                raise KeyLifecycleError(f"duplicate key generation for provider/algorithm {key}")
            ordered = sorted(rows, key=lambda r: r.generation)
            for prev, current in zip(ordered, ordered[1:]):
                pred = current.canonical_dict()["predecessor_fingerprint_sha256"]
                if pred != prev.canonical_dict()["key_fingerprint_sha256"]:
                    raise KeyLifecycleError("rotation chain must point to the immediately previous generation")

    @property
    def registry_sha256(self) -> str:
        payload = sorted((r.canonical_dict() for r in self.records), key=lambda x: (x["provider_id"], x["algorithm_id"], x["generation"]))
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def lookup(self, provider_id: str, fingerprint_sha256: str) -> KeyRecord:
        fp = fingerprint_sha256.lower()
        matches = [r for r in self.records if r.provider_id == provider_id and r.canonical_dict()["key_fingerprint_sha256"] == fp]
        if len(matches) != 1:
            raise KeyLifecycleError("provider/key fingerprint is not uniquely registered")
        return matches[0]

    def authorize_key(
        self,
        *,
        provider_id: str,
        fingerprint_sha256: str,
        algorithm_id: str,
        now: dt.datetime | None = None,
        allow_deprecated: bool = False,
        minimum_generation: int | None = None,
    ) -> dict:
        record = self.lookup(provider_id, fingerprint_sha256)
        data = record.canonical_dict()
        alg = normalize_algorithm_id(algorithm_id)
        if data["algorithm_id"] != alg:
            raise KeyLifecycleError("registered key algorithm does not match attestation algorithm")
        if record.state == KeyState.REVOKED:
            raise KeyLifecycleError("revoked key cannot authorize a release")
        if record.state == KeyState.DEPRECATED and not allow_deprecated:
            raise KeyLifecycleError("deprecated key is blocked by current policy")
        current = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
        if current < _time(record.not_before):
            raise KeyLifecycleError("key is not active yet")
        if record.not_after and current >= _time(record.not_after):
            raise KeyLifecycleError("key has expired")
        if minimum_generation is not None and record.generation < minimum_generation:
            raise KeyLifecycleError("key generation is below anti-rollback floor")
        # Anti-rollback: if a newer ACTIVE generation exists for the same provider and
        # algorithm, an older generation cannot be silently reintroduced.
        newer_active = [
            r for r in self.records
            if r.provider_id == record.provider_id
            and normalize_algorithm_id(r.algorithm_id) == alg
            and r.generation > record.generation
            and r.state == KeyState.ACTIVE
            and current >= _time(r.not_before)
            and (not r.not_after or current < _time(r.not_after))
        ]
        if newer_active:
            raise KeyLifecycleError("older key generation is blocked after a newer active rotation")
        return {
            "provider_id": provider_id,
            "key_fingerprint_sha256": data["key_fingerprint_sha256"],
            "algorithm_id": alg,
            "generation": record.generation,
            "state": record.state.value,
            "registry_sha256": self.registry_sha256,
            "authorized": True,
        }


def registry_from_records(records: Iterable[KeyRecord]) -> KeyRegistry:
    return KeyRegistry(tuple(records))
