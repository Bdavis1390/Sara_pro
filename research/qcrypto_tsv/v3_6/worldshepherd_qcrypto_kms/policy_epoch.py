"""Durable anti-rollback ledger for Bitcoin quantum-policy states."""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path

from .bitcoin_quantum_policy import CryptoPolicyState


class PolicyEpochError(RuntimeError):
    pass


_ORDER = {
    CryptoPolicyState.ECDSA_ALLOWED: 0,
    CryptoPolicyState.HYBRID_REQUIRED: 1,
    CryptoPolicyState.PQ_REQUIRED: 2,
    CryptoPolicyState.CLASSICAL_REJECTED: 3,
}
_GENESIS = "0" * 64
_DOMAIN = b"WS-QCRYPTO-POLICY-EPOCH-V1\x00"


def _time(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise PolicyEpochError("effective_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PolicyEpochError("effective_at requires timezone offset")
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


class QuantumPolicyLedger:
    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        if self.path.is_symlink() or self.path.parent.is_symlink() or self.lock_path.is_symlink():
            raise PolicyEpochError("policy ledger path/parent/lock must not be a symlink")

    def _lock(self, exclusive: bool):
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.lock_path, flags, 0o600)
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        return fd

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        st = self.path.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
            raise PolicyEpochError("policy ledger must be a private regular file")
        rows: list[dict] = []
        prev = _GENESIS
        for line_no, line in enumerate(self.path.read_text().splitlines(), 1):
            try:
                row = json.loads(line)
            except Exception as exc:
                raise PolicyEpochError(f"policy ledger line {line_no} is invalid JSON") from exc
            claimed = row.pop("record_hash", None)
            if row.get("sequence") != line_no or row.get("previous_hash") != prev:
                raise PolicyEpochError(f"policy ledger chain break at line {line_no}")
            expected = hashlib.sha256(_DOMAIN + json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if claimed != expected:
                raise PolicyEpochError(f"policy ledger record hash mismatch at line {line_no}")
            try:
                state = CryptoPolicyState(row["policy_state"])
            except Exception as exc:
                raise PolicyEpochError(f"invalid policy state at line {line_no}") from exc
            if rows:
                prev_state = CryptoPolicyState(rows[-1]["policy_state"])
                if _ORDER[state] < _ORDER[prev_state]:
                    raise PolicyEpochError("policy ledger contains a downgrade")
            row["record_hash"] = claimed
            rows.append(row)
            prev = claimed
        return rows

    def transition(self, *, policy_state: CryptoPolicyState, policy_epoch: str, effective_at: str, reason: str, expected_sequence: int) -> dict:
        if not policy_epoch.strip() or len(policy_epoch) > 128:
            raise PolicyEpochError("policy_epoch must be non-empty and <=128 characters")
        if not reason.strip() or len(reason) > 2048:
            raise PolicyEpochError("transition reason is required and <=2048 characters")
        lock = self._lock(True)
        try:
            rows = self._read()
            if len(rows) != expected_sequence:
                raise PolicyEpochError("stale policy-ledger writer sequence")
            if rows:
                current = CryptoPolicyState(rows[-1]["policy_state"])
                if _ORDER[policy_state] < _ORDER[current]:
                    raise PolicyEpochError("quantum policy downgrade is forbidden")
                if rows[-1]["policy_epoch"] == policy_epoch and current != policy_state:
                    raise PolicyEpochError("one policy epoch cannot name two different states")
            base = {
                "schema": "WS-QCRYPTO-POLICY-EPOCH-RECORD-V1",
                "sequence": len(rows) + 1,
                "previous_hash": rows[-1]["record_hash"] if rows else _GENESIS,
                "policy_state": policy_state.value,
                "policy_epoch": policy_epoch.strip(),
                "effective_at": _time(effective_at),
                "reason_sha256": hashlib.sha256(reason.encode()).hexdigest(),
            }
            record = {**base, "record_hash": hashlib.sha256(_DOMAIN + json.dumps(base, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(self.path, flags, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            return record
        finally:
            os.close(lock)

    def current(self) -> dict | None:
        lock = self._lock(False)
        try:
            rows = self._read()
            return None if not rows else dict(rows[-1])
        finally:
            os.close(lock)

    def assert_current(self, *, policy_state: CryptoPolicyState, policy_epoch: str) -> dict:
        current = self.current()
        if current is None:
            raise PolicyEpochError("quantum policy ledger has no anchored state")
        if current["policy_state"] != policy_state.value or current["policy_epoch"] != policy_epoch:
            raise PolicyEpochError("requested signing policy state/epoch does not match durable anti-rollback anchor")
        return {
            "policy_state": current["policy_state"],
            "policy_epoch": current["policy_epoch"],
            "record_hash": current["record_hash"],
            "sequence": current["sequence"],
            "anchored": True,
        }
