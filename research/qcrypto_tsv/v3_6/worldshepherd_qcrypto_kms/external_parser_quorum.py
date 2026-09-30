"""Fail-closed validation for independently executed Bitcoin PSBT parser quorum receipts.

This module does not call external services. It validates a previously obtained
receipt from an independent execution environment and binds that exact receipt to
the local signing policy. The intended use is to require independent parser
agreement before local authorization can advance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ExternalParserQuorumError(RuntimeError):
    pass


def _sha256_hex(value: str, *, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ExternalParserQuorumError(f"{field} must be 32-byte lowercase hex")
    return text


def _int_text(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise ExternalParserQuorumError(f"{field} must be an integer")
    try:
        n = int(str(value), 10)
    except Exception as exc:
        raise ExternalParserQuorumError(f"{field} must be an integer") from exc
    if n < 0:
        raise ExternalParserQuorumError(f"{field} must be non-negative")
    return n


def _canonical_receipt_hash(report: Mapping[str, object]) -> str:
    body = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(b"WS-QCRYPTO-EXTERNAL-PARSER-RECEIPT-V1\x00" + body).hexdigest()


@dataclass(frozen=True)
class ExternalParserQuorumBinding:
    receipt_sha256: str
    psbt_sha256: str
    txid: str
    fee_sat: int
    libraries: tuple[str, ...]
    execution_location: str
    remote_verdict_sha256: str | None = None

    def to_dict(self) -> dict:
        return {
            "schema": "WS-QCRYPTO-EXTERNAL-PARSER-BINDING-V1",
            "receipt_sha256": self.receipt_sha256,
            "psbt_sha256": self.psbt_sha256,
            "txid": self.txid,
            "fee_sat": self.fee_sat,
            "libraries": list(self.libraries),
            "execution_location": self.execution_location,
            "remote_verdict_sha256": self.remote_verdict_sha256,
        }


def validate_external_parser_quorum_report(
    report: Mapping[str, object],
    *,
    expected_psbt_sha256: str,
    expected_txid: str,
    expected_fee_sat: int,
    minimum_libraries: int = 2,
) -> ExternalParserQuorumBinding:
    """Validate an independent parser-quorum receipt against the exact local candidate.

    The current external receipt schema contains two independently implemented
    parsers (bitcoinjs-lib and @scure/btc-signer). Both must agree with one another
    and with the exact PSBT/txid/fee computed locally.
    """
    if not isinstance(report, Mapping):
        raise ExternalParserQuorumError("external parser quorum report must be a mapping")
    if minimum_libraries < 2:
        raise ExternalParserQuorumError("minimum_libraries must be at least 2")
    if report.get("schema") != "WS-QCRYPTO-EXTERNAL-BITCOIN-PARSER-QUORUM-V1":
        raise ExternalParserQuorumError("unsupported external parser quorum schema")
    if report.get("agreement") is not True or report.get("release_allowed") is not True:
        raise ExternalParserQuorumError("external parser quorum did not authorize release")

    psbt_sha = _sha256_hex(str(report.get("psbt_sha256", "")), field="psbt_sha256")
    expected_psbt = _sha256_hex(expected_psbt_sha256, field="expected_psbt_sha256")
    if psbt_sha != expected_psbt:
        raise ExternalParserQuorumError("external parser quorum PSBT hash does not match exact candidate")

    libraries_obj = report.get("libraries")
    if not isinstance(libraries_obj, Sequence) or isinstance(libraries_obj, (str, bytes, bytearray)):
        raise ExternalParserQuorumError("external parser quorum libraries must be a sequence")
    libraries = tuple(str(x).strip() for x in libraries_obj if str(x).strip())
    if len(libraries) < minimum_libraries or len(set(libraries)) != len(libraries):
        raise ExternalParserQuorumError("external parser quorum does not contain enough distinct libraries")

    left = report.get("bitcoinjs")
    right = report.get("scure")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise ExternalParserQuorumError("external parser quorum is missing parser result objects")

    expected_txid_text = _sha256_hex(expected_txid, field="expected_txid")
    expected_fee = _int_text(expected_fee_sat, field="expected_fee_sat")
    parser_rows = (("bitcoinjs", left), ("scure", right))
    for name, row in parser_rows:
        txid = _sha256_hex(str(row.get("txid", "")), field=f"{name}.txid")
        fee = _int_text(row.get("fee_sat"), field=f"{name}.fee_sat")
        if txid != expected_txid_text:
            raise ExternalParserQuorumError(f"{name} txid disagrees with local candidate")
        if fee != expected_fee:
            raise ExternalParserQuorumError(f"{name} fee disagrees with local candidate")

    if str(left.get("txid")) != str(right.get("txid")) or str(left.get("fee_sat")) != str(right.get("fee_sat")):
        raise ExternalParserQuorumError("external parser implementations disagree")

    remote_verdict = report.get("verdict_sha256")
    remote_verdict_sha256 = None
    if remote_verdict not in (None, ""):
        remote_verdict_sha256 = _sha256_hex(str(remote_verdict), field="verdict_sha256")

    execution_location = str(report.get("execution_location", "")).strip()
    if not execution_location:
        raise ExternalParserQuorumError("external parser quorum execution location is missing")

    return ExternalParserQuorumBinding(
        receipt_sha256=_canonical_receipt_hash(report),
        psbt_sha256=psbt_sha,
        txid=expected_txid_text,
        fee_sat=expected_fee,
        libraries=libraries,
        execution_location=execution_location,
        remote_verdict_sha256=remote_verdict_sha256,
    )
