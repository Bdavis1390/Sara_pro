"""Durable Q-day / emergency signing-state control.

PRIME's emergency mode is a policy value; this ledger makes mode changes durable,
hash-chained and stale-writer resistant.  Escalation into MIGRATION_ONLY/FREEZE is
always permitted.  De-escalation requires an explicit recovery authorization digest,
so a restart or configuration rollback cannot silently reopen signing.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path

from .governance_plane import EmergencyMode


class EmergencyStateError(RuntimeError):
    pass


_SEVERITY={EmergencyMode.NORMAL:0,EmergencyMode.MIGRATION_ONLY:1,EmergencyMode.FREEZE:2}


def _hex32(name:str,value:str)->str:
    text=value.lower()
    if len(text)!=64 or any(c not in "0123456789abcdef" for c in text):
        raise EmergencyStateError(f"{name} must be 32-byte hex")
    return text


class EmergencyStateLedger:
    def __init__(self,path:str|os.PathLike)->None:
        self.path=Path(path)
        self.lock_path=self.path.with_suffix(self.path.suffix+".lock")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise EmergencyStateError("emergency ledger path/parent must not be a symlink")

    def _lock(self):
        flags=os.O_RDWR|os.O_CREAT
        if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
        fd=os.open(self.lock_path,flags,0o600)
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd); raise EmergencyStateError("emergency ledger lock must be regular file")
        os.fchmod(fd,0o600); fcntl.flock(fd,fcntl.LOCK_EX); return fd

    def _read(self)->list[dict]:
        if not self.path.exists(): return []
        if self.path.is_symlink(): raise EmergencyStateError("emergency ledger must not be a symlink")
        st=self.path.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
            raise EmergencyStateError("emergency ledger must be private regular file")
        rows=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip(): rows.append(json.loads(line))
        prev="0"*64
        for i,row in enumerate(rows,1):
            if row.get("sequence")!=i or row.get("previous_sha256")!=prev:
                raise EmergencyStateError("emergency ledger chain/sequence is invalid")
            body=dict(row); got=body.pop("record_sha256",None)
            calc=hashlib.sha256(b"WS-QCRYPTO-EMERGENCY-STATE-V1\x00"+json.dumps(body,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
            if got!=calc: raise EmergencyStateError("emergency ledger record hash is invalid")
            prev=calc
        return rows

    def transition(self,mode:EmergencyMode,*,reason:str,expected_sequence:int,recovery_authorization_sha256:str|None=None)->dict:
        if not reason or len(reason)>512: raise EmergencyStateError("emergency transition reason is required")
        fd=self._lock()
        try:
            rows=self._read()
            if len(rows)!=expected_sequence: raise EmergencyStateError("stale emergency-state writer sequence")
            prior=EmergencyMode(rows[-1]["mode"]) if rows else EmergencyMode.NORMAL
            if _SEVERITY[mode] < _SEVERITY[prior]:
                if recovery_authorization_sha256 is None:
                    raise EmergencyStateError("emergency de-escalation requires explicit recovery authorization")
                recovery_authorization_sha256=_hex32("recovery_authorization_sha256",recovery_authorization_sha256)
            elif recovery_authorization_sha256 is not None:
                recovery_authorization_sha256=_hex32("recovery_authorization_sha256",recovery_authorization_sha256)
            body={
                "schema":"WS-QCRYPTO-EMERGENCY-STATE-V1",
                "sequence":len(rows)+1,
                "previous_sha256":rows[-1]["record_sha256"] if rows else "0"*64,
                "mode":mode.value,
                "previous_mode":prior.value,
                "reason":reason,
                "recovery_authorization_sha256":recovery_authorization_sha256,
            }
            body["record_sha256"]=hashlib.sha256(b"WS-QCRYPTO-EMERGENCY-STATE-V1\x00"+json.dumps(body,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
            flags=os.O_WRONLY|os.O_CREAT|os.O_APPEND
            if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
            out=os.open(self.path,flags,0o600)
            try:
                os.fchmod(out,0o600); os.write(out,(json.dumps(body,sort_keys=True,separators=(",", ":"))+"\n").encode()); os.fsync(out)
            finally: os.close(out)
            dfd=os.open(self.path.parent,os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
            return body
        finally: os.close(fd)

    def assert_current(self,mode:EmergencyMode)->dict:
        fd=self._lock()
        try:
            rows=self._read()
            current=EmergencyMode(rows[-1]["mode"]) if rows else EmergencyMode.NORMAL
            if current!=mode:
                raise EmergencyStateError(f"PRIME emergency mode {mode.value} does not match durable state {current.value}")
            return {"anchored":True,"mode":current.value,"sequence":len(rows),"tip_sha256":rows[-1]["record_sha256"] if rows else "0"*64}
        finally: os.close(fd)
