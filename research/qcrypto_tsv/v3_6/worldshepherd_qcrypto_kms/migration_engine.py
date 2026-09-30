"""Deterministic, durable Bitcoin quantum-risk wallet migration controls.

The earlier manifest ranked UTXOs.  This module turns that inventory into bounded
migration batches that can be reserved, bound to a signing intent, and completed
without stale-writer or silent-substitution behavior.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .bitcoin_quantum_policy import UtxoRecord, assess_utxo
from .bitcoin_tx import BitcoinTransaction
from .psbt_guard import PsbtAuditReport


class MigrationEngineError(RuntimeError):
    pass


def _hex32(name: str, value: str) -> str:
    text = value.lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise MigrationEngineError(f"{name} must be 32-byte hex")
    return text


def _parse_time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise MigrationEngineError("migration timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MigrationEngineError("migration timestamp must include timezone offset")
    return parsed.astimezone(dt.timezone.utc)


@dataclass(frozen=True)
class MigrationBatchBinding:
    batch_id: str
    network: str
    manifest_sha256: str
    outpoints: tuple[str, ...]
    allowed_destination_script_types: tuple[str, ...]
    max_fee_sat: int
    reservation_nonce: str
    expires_at: str
    generation: int

    def canonical_dict(self) -> dict:
        network = self.network.strip().upper()
        if network not in {"SIGNET", "REGTEST", "TESTNET4"}:
            raise MigrationEngineError("migration binding network must be a permitted non-mainnet network")
        if not self.batch_id or len(self.batch_id) > 128:
            raise MigrationEngineError("invalid migration batch_id")
        if len(self.reservation_nonce) < 16 or len(self.reservation_nonce) > 128:
            raise MigrationEngineError("migration reservation nonce must be 16..128 characters")
        if self.max_fee_sat < 0 or self.generation < 1:
            raise MigrationEngineError("migration max_fee_sat/generation are invalid")
        expiry = _parse_time(self.expires_at)
        outpoints = []
        for op in self.outpoints:
            try:
                txid, vout = op.split(":", 1)
                _hex32("migration txid", txid)
                vout_int = int(vout)
            except Exception as exc:
                raise MigrationEngineError("migration outpoint must be txid:vout") from exc
            if vout_int < 0:
                raise MigrationEngineError("migration vout must be non-negative")
            outpoints.append(f"{txid.lower()}:{vout_int}")
        if len(set(outpoints)) != len(outpoints) or not outpoints:
            raise MigrationEngineError("migration binding requires unique non-empty outpoints")
        dest = tuple(sorted(set(s.strip().upper() for s in self.allowed_destination_script_types if s.strip())))
        if not dest:
            raise MigrationEngineError("migration binding requires destination script policy")
        return {
            "schema": "WS-QCRYPTO-MIGRATION-BINDING-V1",
            "batch_id": self.batch_id,
            "network": network,
            "manifest_sha256": _hex32("manifest_sha256", self.manifest_sha256),
            "outpoints": sorted(outpoints),
            "allowed_destination_script_types": list(dest),
            "max_fee_sat": self.max_fee_sat,
            "reservation_nonce": self.reservation_nonce,
            "expires_at": expiry.isoformat().replace("+00:00", "Z"),
            "generation": self.generation,
        }

    @property
    def binding_sha256(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-MIGRATION-BINDING-V1\x00" + body).hexdigest()

    def validate_prepared_transaction(self, tx: BitcoinTransaction, audit: PsbtAuditReport, *, now: dt.datetime | None = None) -> dict:
        data = self.canonical_dict()
        current = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
        if current >= _parse_time(self.expires_at):
            raise MigrationEngineError("migration reservation has expired")
        actual = sorted(f"{i.prev_txid.lower()}:{i.vout}" for i in tx.inputs)
        if actual != data["outpoints"]:
            raise MigrationEngineError("transaction inputs do not exactly match reserved migration outpoints")
        if audit.fee_sat > self.max_fee_sat:
            raise MigrationEngineError("migration transaction fee exceeds migration-specific cap")
        allowed_types = set(data["allowed_destination_script_types"])
        bad = [d["index"] for d in audit.output_decisions if str(d["script_type"]).upper() not in allowed_types]
        if bad:
            raise MigrationEngineError(f"migration transaction creates disallowed destination script types at outputs {bad}")
        return {
            "batch_id": self.batch_id,
            "binding_sha256": self.binding_sha256,
            "input_count": len(actual),
            "fee_sat": audit.fee_sat,
            "destination_script_types": sorted({str(d["script_type"]).upper() for d in audit.output_decisions}),
            "satisfied": True,
        }


def build_migration_batches(
    records: Iterable[UtxoRecord],
    *,
    network: str,
    manifest_sha256: str,
    max_inputs_per_batch: int,
    max_value_sat_per_batch: int,
    max_fee_sat_per_batch: int,
    allowed_destination_script_types: Sequence[str] = ("P2WPKH", "P2WSH"),
) -> tuple[dict, ...]:
    if max_inputs_per_batch <= 0 or max_value_sat_per_batch <= 0 or max_fee_sat_per_batch < 0:
        raise MigrationEngineError("migration batch limits must be positive/non-negative")
    ranked = sorted((assess_utxo(r) for r in records), key=lambda a: (-a.priority, -a.amount_sat, a.txid, a.vout))
    batches: list[dict] = []
    current: list = []
    value = 0
    for assessment in ranked:
        if current and (len(current) >= max_inputs_per_batch or value + assessment.amount_sat > max_value_sat_per_batch):
            batches.append(_batch_dict(len(batches) + 1, current, network, manifest_sha256, max_fee_sat_per_batch, allowed_destination_script_types))
            current, value = [], 0
        current.append(assessment)
        value += assessment.amount_sat
    if current:
        batches.append(_batch_dict(len(batches) + 1, current, network, manifest_sha256, max_fee_sat_per_batch, allowed_destination_script_types))
    return tuple(batches)


def _batch_dict(index: int, rows: list, network: str, manifest_sha256: str, max_fee: int, dest: Sequence[str]) -> dict:
    content = {
        "index": index,
        "network": network.strip().upper(),
        "manifest_sha256": _hex32("manifest_sha256", manifest_sha256),
        "outpoints": [f"{r.txid}:{r.vout}" for r in rows],
        "total_value_sat": sum(r.amount_sat for r in rows),
        "max_priority": max(r.priority for r in rows),
        "max_fee_sat": max_fee,
        "allowed_destination_script_types": sorted(set(x.strip().upper() for x in dest)),
    }
    content["batch_id"] = "WS-MIG-" + hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:32]
    return content


class MigrationStateStore:
    """Durable batch state with generation-based stale-writer protection."""

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise MigrationEngineError("migration state path/parent must not be a symlink")

    def _lock(self):
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def _read_unlocked(self) -> dict:
        if not self.path.exists():
            return {"schema": "WS-QCRYPTO-MIGRATION-STATE-V1", "generation": 0, "batches": {}}
        st = self.path.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
            raise MigrationEngineError("migration state file must be a private regular file")
        try:
            return json.loads(self.path.read_text())
        except Exception as exc:
            raise MigrationEngineError("migration state file is invalid") from exc

    def _write_unlocked(self, state: dict) -> None:
        temp = self.path.with_name(self.path.name + ".tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temp, flags, 0o600)
        try:
            payload = json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n"
            os.write(fd, payload.encode())
            os.fsync(fd)
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        os.replace(temp, self.path)
        dfd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def initialize(self, batches: Sequence[dict]) -> dict:
        lock = self._lock()
        try:
            state = self._read_unlocked()
            if state.get("generation", 0) != 0 or state.get("batches"):
                raise MigrationEngineError("migration store is already initialized")
            rows = {}
            for b in batches:
                bid = b.get("batch_id")
                if not bid or bid in rows:
                    raise MigrationEngineError("migration batches require unique batch_id")
                rows[bid] = {"definition": b, "status": "PENDING", "reservation": None, "completion_txid": None}
            state = {"schema": "WS-QCRYPTO-MIGRATION-STATE-V1", "generation": 1, "batches": rows}
            self._write_unlocked(state)
            return state
        finally:
            os.close(lock)

    def snapshot(self) -> dict:
        lock = self._lock()
        try:
            return self._read_unlocked()
        finally:
            os.close(lock)

    def reserve(
        self,
        batch_id: str,
        *,
        expected_generation: int,
        reservation_nonce: str,
        expires_at: str,
    ) -> MigrationBatchBinding:
        if len(reservation_nonce) < 16:
            raise MigrationEngineError("reservation nonce is too short")
        _parse_time(expires_at)
        lock = self._lock()
        try:
            state = self._read_unlocked()
            if state.get("generation") != expected_generation:
                raise MigrationEngineError("stale migration writer generation")
            row = state.get("batches", {}).get(batch_id)
            if not row:
                raise MigrationEngineError("unknown migration batch")
            if row.get("status") != "PENDING":
                raise MigrationEngineError("migration batch is not pending")
            new_generation = expected_generation + 1
            definition = row["definition"]
            binding = MigrationBatchBinding(
                batch_id=batch_id,
                network=definition["network"],
                manifest_sha256=definition["manifest_sha256"],
                outpoints=tuple(definition["outpoints"]),
                allowed_destination_script_types=tuple(definition["allowed_destination_script_types"]),
                max_fee_sat=int(definition["max_fee_sat"]),
                reservation_nonce=reservation_nonce,
                expires_at=expires_at,
                generation=new_generation,
            )
            row["status"] = "RESERVED"
            row["reservation"] = binding.canonical_dict()
            state["generation"] = new_generation
            self._write_unlocked(state)
            return binding
        finally:
            os.close(lock)

    def complete(self, batch_id: str, *, expected_generation: int, txid: str, binding_sha256: str) -> dict:
        _hex32("txid", txid)
        _hex32("binding_sha256", binding_sha256)
        lock = self._lock()
        try:
            state = self._read_unlocked()
            if state.get("generation") != expected_generation:
                raise MigrationEngineError("stale migration writer generation")
            row = state.get("batches", {}).get(batch_id)
            if not row or row.get("status") != "RESERVED":
                raise MigrationEngineError("migration batch is not reserved")
            reservation = row.get("reservation") or {}
            rebuilt = MigrationBatchBinding(
                batch_id=reservation["batch_id"], network=reservation["network"], manifest_sha256=reservation["manifest_sha256"],
                outpoints=tuple(reservation["outpoints"]), allowed_destination_script_types=tuple(reservation["allowed_destination_script_types"]),
                max_fee_sat=reservation["max_fee_sat"], reservation_nonce=reservation["reservation_nonce"], expires_at=reservation["expires_at"], generation=reservation["generation"],
            )
            if rebuilt.binding_sha256 != binding_sha256:
                raise MigrationEngineError("migration completion binding does not match reservation")
            row["status"] = "COMPLETED"
            row["completion_txid"] = txid.lower()
            state["generation"] = expected_generation + 1
            self._write_unlocked(state)
            return state
        finally:
            os.close(lock)
