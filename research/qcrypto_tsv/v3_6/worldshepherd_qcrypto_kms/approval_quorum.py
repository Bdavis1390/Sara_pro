"""Detached Ed25519 human/operator approval quorum bound to a release intent.

These signatures authorize a Worldshepherd workflow; they are not Bitcoin
transaction signatures and do not alter Bitcoin consensus rules.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class ApprovalQuorumError(RuntimeError):
    pass


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    try:
        raw = text.encode("ascii")
        return base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise ApprovalQuorumError("invalid base64url") from exc


def _parse_time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalQuorumError("approval time must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ApprovalQuorumError("approval time must include an offset")
    return parsed.astimezone(dt.timezone.utc)


@dataclass(frozen=True)
class ApprovalStatement:
    intent_sha256: str
    approver_id: str
    role: str
    issued_at: str
    expires_at: str
    nonce: str
    decision: str = "APPROVE"

    def canonical_bytes(self) -> bytes:
        if len(self.intent_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in self.intent_sha256):
            raise ApprovalQuorumError("intent_sha256 must be 32-byte hex")
        if not self.approver_id or len(self.approver_id) > 128:
            raise ApprovalQuorumError("invalid approver_id")
        if not self.role or len(self.role) > 128:
            raise ApprovalQuorumError("invalid approval role")
        if not self.nonce or len(self.nonce) > 128:
            raise ApprovalQuorumError("invalid approval nonce")
        if self.decision != "APPROVE":
            raise ApprovalQuorumError("only explicit APPROVE statements satisfy the quorum")
        issued, expires = _parse_time(self.issued_at), _parse_time(self.expires_at)
        if expires <= issued:
            raise ApprovalQuorumError("approval expiry must be after issue time")
        payload = {
            "schema": "WS-BITCOIN-OPERATOR-APPROVAL-V1",
            "intent_sha256": self.intent_sha256.lower(),
            "approver_id": self.approver_id,
            "role": self.role,
            "issued_at": issued.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "nonce": self.nonce,
            "decision": self.decision,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class SignedApproval:
    statement: ApprovalStatement
    public_key_b64url: str
    signature_b64url: str

    def to_dict(self) -> dict:
        return {"statement": asdict(self.statement), "public_key_b64url": self.public_key_b64url, "signature_b64url": self.signature_b64url}


def sign_approval(statement: ApprovalStatement, private_key: Ed25519PrivateKey) -> SignedApproval:
    from cryptography.hazmat.primitives import serialization
    pub = private_key.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    sig = private_key.sign(statement.canonical_bytes())
    return SignedApproval(statement=statement, public_key_b64url=_b64u(pub), signature_b64url=_b64u(sig))


def verify_approval_quorum(
    *,
    intent_sha256: str,
    approvals: Sequence[SignedApproval],
    trusted_approvers: Mapping[str, bytes],
    required_count: int,
    required_roles: Sequence[str] = (),
    now: dt.datetime | None = None,
) -> dict:
    if required_count < 0:
        raise ApprovalQuorumError("required_count must be non-negative")
    if required_count == 0:
        return {"required_count": 0, "verified_count": 0, "verified_approvers": [], "roles": [], "satisfied": True}
    current = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    verified: list[str] = []
    roles: list[str] = []
    seen: set[str] = set()
    nonces: set[str] = set()
    for approval in approvals:
        st = approval.statement
        if st.intent_sha256.lower() != intent_sha256.lower():
            raise ApprovalQuorumError("approval is bound to a different release intent")
        if st.approver_id in seen:
            raise ApprovalQuorumError("duplicate approver cannot satisfy quorum twice")
        if st.nonce in nonces:
            raise ApprovalQuorumError("approval nonce replay detected")
        issued, expires = _parse_time(st.issued_at), _parse_time(st.expires_at)
        if current < issued or current >= expires:
            raise ApprovalQuorumError("approval is not currently valid")
        expected_key = trusted_approvers.get(st.approver_id)
        if expected_key is None:
            raise ApprovalQuorumError("approval signer is not in the trusted approver registry")
        supplied_key = _b64u_decode(approval.public_key_b64url)
        if supplied_key != bytes(expected_key):
            raise ApprovalQuorumError("approval public key does not match trusted registry")
        try:
            Ed25519PublicKey.from_public_bytes(supplied_key).verify(_b64u_decode(approval.signature_b64url), st.canonical_bytes())
        except (ValueError, InvalidSignature) as exc:
            raise ApprovalQuorumError("operator approval signature verification failed") from exc
        seen.add(st.approver_id)
        nonces.add(st.nonce)
        verified.append(st.approver_id)
        roles.append(st.role)
    missing_roles = sorted(set(required_roles) - set(roles))
    satisfied = len(verified) >= required_count and not missing_roles
    return {
        "required_count": required_count,
        "verified_count": len(verified),
        "verified_approvers": verified,
        "roles": sorted(set(roles)),
        "missing_roles": missing_roles,
        "satisfied": satisfied,
        "registry_sha256": hashlib.sha256(json.dumps(sorted((k, bytes(v).hex()) for k, v in trusted_approvers.items()), separators=(",", ":")).encode()).hexdigest(),
    }
