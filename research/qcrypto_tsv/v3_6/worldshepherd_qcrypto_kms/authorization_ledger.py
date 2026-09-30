"""Append-only, hash-chained local authorization receipts.

v3 adds an exclusive advisory lock around verify+append so two local writers cannot
both observe the same tip and create a forked sequence.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any


class AuthorizationLedgerError(RuntimeError):
    pass


_GENESIS = "0" * 64
_DOMAIN = b"WS-BITCOIN-AUTHORIZATION-LEDGER-V1\x00"


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash_record(base: dict) -> str:
    return hashlib.sha256(_DOMAIN + _canonical(base)).hexdigest()


def _safe_existing(path: Path) -> None:
    if path.is_symlink():
        raise AuthorizationLedgerError("authorization ledger path must not be a symlink")
    if path.exists():
        st = path.stat()
        if not stat.S_ISREG(st.st_mode):
            raise AuthorizationLedgerError("authorization ledger must be a regular file")
        if st.st_mode & 0o077:
            raise AuthorizationLedgerError("authorization ledger permissions must not grant group/other access")


def _verify_unlocked(p: Path) -> dict:
    if not p.exists():
        return {"valid": True, "records": 0, "tip_hash": _GENESIS}
    _safe_existing(p)
    previous = _GENESIS
    count = 0
    with p.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.endswith("\n"):
                raise AuthorizationLedgerError(f"ledger line {line_no} is not newline-terminated")
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuthorizationLedgerError(f"ledger line {line_no} is invalid JSON") from exc
            claimed = rec.pop("record_hash", None)
            if rec.get("sequence") != count + 1 or rec.get("previous_hash") != previous:
                raise AuthorizationLedgerError(f"ledger chain break at line {line_no}")
            expected = _hash_record(rec)
            if claimed != expected:
                raise AuthorizationLedgerError(f"ledger record hash mismatch at line {line_no}")
            previous = expected
            count += 1
    return {"valid": True, "records": count, "tip_hash": previous}


def _lock_fd(p: Path, *, exclusive: bool):
    lock = p.with_suffix(p.suffix + ".lock")
    if lock.is_symlink():
        raise AuthorizationLedgerError("authorization ledger lock path must not be a symlink")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock, flags, 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        os.close(fd)
        raise AuthorizationLedgerError("authorization ledger lock must be a regular file")
    os.fchmod(fd, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    return fd


def verify_authorization_ledger(path: str | os.PathLike) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.parent.is_symlink():
        raise AuthorizationLedgerError("authorization ledger parent must not be a symlink")
    fd = _lock_fd(p, exclusive=False)
    try:
        return _verify_unlocked(p)
    finally:
        os.close(fd)


def append_authorization_receipt(path: str | os.PathLike, payload: dict) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.parent.is_symlink():
        raise AuthorizationLedgerError("authorization ledger parent must not be a symlink")
    fd_lock = _lock_fd(p, exclusive=True)
    try:
        if p.exists():
            _safe_existing(p)
        state = _verify_unlocked(p)
        base = {
            "schema": "WS-BITCOIN-AUTHORIZATION-LEDGER-RECORD-V1",
            "sequence": state["records"] + 1,
            "previous_hash": state["tip_hash"],
            "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
            "payload": payload,
        }
        record = {**base, "record_hash": _hash_record(base)}
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(p, flags, 0o600)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise AuthorizationLedgerError("authorization ledger is not a regular file")
            os.fchmod(fd, 0o600)
            os.write(fd, _canonical(record) + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
        return record
    finally:
        os.close(fd_lock)
