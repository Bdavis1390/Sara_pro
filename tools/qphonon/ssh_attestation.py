#!/usr/bin/env python3
"""OpenSSH detached-signature verification for human QPHONON approvals.

The private signing key is deliberately outside this component. Verification
uses ssh-keygen -Y verify and an administrator-managed allowed-signers file.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from security_controls import canonical_json_bytes, sha256_json

NAMESPACE = "worldshepherd-qphonon-approval"
PRINCIPAL_RE = re.compile(r"^[A-Za-z0-9._@+-]{1,128}$")


@dataclass(frozen=True)
class AttestationDecision:
    verified: bool
    principal: str
    payload_digest: str
    reason: str


def approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "approved",
        "approval_id",
        "approver",
        "experiment_digest",
        "config_digest",
        "issued_at_utc",
        "expires_at_utc",
    )
    return {field: approval.get(field) for field in fields}


def verify_approval_signature(
    approval: dict[str, Any],
    *,
    signature_path: str | Path,
    allowed_signers_path: str | Path,
    principal: str,
) -> AttestationDecision:
    payload = approval_payload(approval)
    payload_digest = sha256_json(payload)

    if not PRINCIPAL_RE.fullmatch(principal):
        return AttestationDecision(False, principal, payload_digest, "PRINCIPAL_INVALID")
    if shutil.which("ssh-keygen") is None:
        return AttestationDecision(False, principal, payload_digest, "SSH_KEYGEN_UNAVAILABLE")

    signature = Path(signature_path)
    signers = Path(allowed_signers_path)
    if not signature.is_file():
        return AttestationDecision(False, principal, payload_digest, "SIGNATURE_FILE_MISSING")
    if not signers.is_file():
        return AttestationDecision(False, principal, payload_digest, "APPROVED_SIGNERS_FILE_MISSING")

    result = subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "verify",
            "-f",
            str(signers),
            "-I",
            principal,
            "-n",
            NAMESPACE,
            "-s",
            str(signature),
        ],
        input=canonical_json_bytes(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return AttestationDecision(False, principal, payload_digest, "SIGNATURE_VERIFICATION_FAILED")

    return AttestationDecision(True, principal, payload_digest, "SIGNATURE_VERIFIED")
