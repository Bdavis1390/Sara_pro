"""Fail-closed validation for candidate-bound external PQ execution evidence.

This module validates execution receipts produced outside the local QCRYPTO runtime.
It does not treat those receipts as release signatures or certification.  The
validated receipt is a pre-authorization evidence gate: it proves that the exact
candidate challenge was exercised by the required PQ algorithm set in an external
runtime and then binds the resulting receipt hash into the local signing policy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from .crypto_agility import AlgorithmFamily, algorithm_spec, normalize_algorithm_id


class ExternalPqEvidenceError(RuntimeError):
    pass


def _hex32(value: object, *, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ExternalPqEvidenceError(f"{field} must be 32-byte lowercase hex")
    return text


def _nonempty(value: object, *, field: str, max_len: int = 256) -> str:
    text = str(value).strip()
    if not text or len(text) > max_len:
        raise ExternalPqEvidenceError(f"{field} is missing or invalid")
    return text


def _canonical_hash(domain: bytes, payload: object) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def build_external_pq_candidate_challenge(
    *,
    psbt_sha256: str,
    txid: str,
    fee_sat: int,
    external_parser_receipt_sha256: str | None,
    policy_epoch: str,
    algorithms: Sequence[str],
) -> str:
    """Build the exact external-execution challenge text for a signing candidate.

    The external execution challenge intentionally precedes the final release intent
    to avoid a circular dependency: its validated receipt hash is subsequently bound
    into the signing policy, which is itself bound into the final release intent.
    """
    psbt = _hex32(psbt_sha256, field="psbt_sha256")
    tx = _hex32(txid, field="txid")
    if not isinstance(fee_sat, int) or isinstance(fee_sat, bool) or fee_sat < 0:
        raise ExternalPqEvidenceError("fee_sat must be a non-negative integer")
    epoch = _nonempty(policy_epoch, field="policy_epoch", max_len=128)
    parser_hash = "NONE" if external_parser_receipt_sha256 in (None, "") else _hex32(
        external_parser_receipt_sha256, field="external_parser_receipt_sha256"
    )
    canonical_algorithms = tuple(normalize_algorithm_id(a) for a in algorithms)
    if not canonical_algorithms:
        raise ExternalPqEvidenceError("external PQ candidate challenge requires at least one algorithm")
    if len(set(canonical_algorithms)) != len(canonical_algorithms):
        raise ExternalPqEvidenceError("external PQ candidate challenge algorithms must be distinct")
    return "|".join(
        (
            "WS-QCRYPTO-EXTERNAL-PQ-CANDIDATE-V1",
            psbt,
            tx,
            str(fee_sat),
            parser_hash,
            epoch,
            ",".join(canonical_algorithms),
        )
    )


@dataclass(frozen=True)
class ExternalPqEvidenceBinding:
    receipt_sha256: str
    candidate_challenge_sha256: str
    psbt_sha256: str
    txid: str
    fee_sat: int
    algorithms: tuple[str, ...]
    execution_targets: tuple[str, ...]
    libraries: tuple[str, ...]
    pq_families: tuple[str, ...]
    parser_receipt_sha256: str | None

    def to_dict(self) -> dict:
        return {
            "schema": "WS-QCRYPTO-EXTERNAL-PQ-EVIDENCE-BINDING-V1",
            "receipt_sha256": self.receipt_sha256,
            "candidate_challenge_sha256": self.candidate_challenge_sha256,
            "psbt_sha256": self.psbt_sha256,
            "txid": self.txid,
            "fee_sat": self.fee_sat,
            "algorithms": list(self.algorithms),
            "execution_targets": list(self.execution_targets),
            "libraries": list(self.libraries),
            "pq_families": list(self.pq_families),
            "parser_receipt_sha256": self.parser_receipt_sha256,
            "certification_claim": "NONE",
            "bitcoin_consensus_pq_claim": False,
        }


def validate_external_pq_evidence_report(
    report: Mapping[str, object],
    *,
    expected_psbt_sha256: str,
    expected_txid: str,
    expected_fee_sat: int,
    expected_parser_receipt_sha256: str | None,
    policy_epoch: str,
    required_algorithms: Sequence[str],
    minimum_execution_targets: int = 1,
    require_family_diversity: bool = False,
) -> ExternalPqEvidenceBinding:
    """Validate candidate-bound hosted PQ execution receipts.

    Every required algorithm must have exactly one PASS execution row for the exact
    candidate challenge.  Signature/public-key sizes must match the local standards
    registry, sign/verify must have succeeded, and adversarial signature corruption
    must have been rejected.  This is execution evidence, not a release signature.
    """
    if not isinstance(report, Mapping):
        raise ExternalPqEvidenceError("external PQ evidence report must be a mapping")
    if report.get("schema") != "WS-QCRYPTO-EXTERNAL-PQ-EVIDENCE-QUORUM-V1":
        raise ExternalPqEvidenceError("unsupported external PQ evidence schema")
    if not isinstance(minimum_execution_targets, int) or minimum_execution_targets < 1:
        raise ExternalPqEvidenceError("minimum_execution_targets must be at least 1")

    psbt = _hex32(expected_psbt_sha256, field="expected_psbt_sha256")
    txid = _hex32(expected_txid, field="expected_txid")
    if not isinstance(expected_fee_sat, int) or isinstance(expected_fee_sat, bool) or expected_fee_sat < 0:
        raise ExternalPqEvidenceError("expected_fee_sat must be a non-negative integer")
    parser_hash = None
    if expected_parser_receipt_sha256 not in (None, ""):
        parser_hash = _hex32(expected_parser_receipt_sha256, field="expected_parser_receipt_sha256")

    required = tuple(normalize_algorithm_id(a) for a in required_algorithms)
    if not required or len(set(required)) != len(required):
        raise ExternalPqEvidenceError("required_algorithms must contain distinct PQ algorithms")
    for alg in required:
        if algorithm_spec(alg).family == AlgorithmFamily.CLASSICAL_ECC:
            raise ExternalPqEvidenceError("external PQ evidence cannot be satisfied by a classical algorithm")

    challenge_text = build_external_pq_candidate_challenge(
        psbt_sha256=psbt,
        txid=txid,
        fee_sat=expected_fee_sat,
        external_parser_receipt_sha256=parser_hash,
        policy_epoch=policy_epoch,
        algorithms=required,
    )
    expected_challenge_sha = hashlib.sha256(challenge_text.encode("utf-8")).hexdigest()
    remote_challenge_sha = _hex32(report.get("candidate_challenge_sha256", ""), field="candidate_challenge_sha256")
    if remote_challenge_sha != expected_challenge_sha:
        raise ExternalPqEvidenceError("external PQ evidence is bound to a different signing candidate")

    report_psbt = _hex32(report.get("psbt_sha256", ""), field="psbt_sha256")
    report_txid = _hex32(report.get("txid", ""), field="txid")
    if report_psbt != psbt or report_txid != txid:
        raise ExternalPqEvidenceError("external PQ evidence transaction identity does not match candidate")
    try:
        report_fee = int(str(report.get("fee_sat")), 10)
    except Exception as exc:
        raise ExternalPqEvidenceError("external PQ evidence fee is invalid") from exc
    if report_fee != expected_fee_sat:
        raise ExternalPqEvidenceError("external PQ evidence fee does not match candidate")

    remote_parser = report.get("external_parser_receipt_sha256")
    if parser_hash is None:
        if remote_parser not in (None, "", "NONE"):
            raise ExternalPqEvidenceError("unexpected parser receipt binding in external PQ evidence")
    else:
        if _hex32(remote_parser, field="external_parser_receipt_sha256") != parser_hash:
            raise ExternalPqEvidenceError("external PQ evidence parser receipt binding does not match candidate")

    executions = report.get("executions")
    if not isinstance(executions, Sequence) or isinstance(executions, (str, bytes, bytearray)):
        raise ExternalPqEvidenceError("external PQ evidence executions must be a sequence")
    rows_by_algorithm: dict[str, Mapping[str, object]] = {}
    targets: set[str] = set()
    libraries: set[str] = set()
    families: set[str] = set()
    for raw_row in executions:
        if not isinstance(raw_row, Mapping):
            raise ExternalPqEvidenceError("external PQ execution row must be a mapping")
        if raw_row.get("schema") != "WS-QCRYPTO-EXTERNAL-PQ-CANDIDATE-RECEIPT-V1":
            raise ExternalPqEvidenceError("unsupported external PQ execution row schema")
        alg = normalize_algorithm_id(_nonempty(raw_row.get("algorithm_id"), field="algorithm_id"))
        if alg not in required:
            raise ExternalPqEvidenceError(f"unexpected external PQ algorithm {alg}")
        if alg in rows_by_algorithm:
            raise ExternalPqEvidenceError(f"duplicate external PQ execution row for {alg}")
        if raw_row.get("status") != "PASS" or raw_row.get("sign_verify") is not True:
            raise ExternalPqEvidenceError(f"external PQ execution for {alg} did not PASS sign/verify")
        if raw_row.get("tampered_signature_rejected") is not True:
            raise ExternalPqEvidenceError(f"external PQ execution for {alg} did not reject signature corruption")
        if _hex32(raw_row.get("candidate_challenge_sha256", ""), field=f"{alg}.candidate_challenge_sha256") != expected_challenge_sha:
            raise ExternalPqEvidenceError(f"external PQ execution for {alg} used the wrong candidate challenge")
        spec = algorithm_spec(alg)
        try:
            signature_bytes = int(str(raw_row.get("signature_bytes")), 10)
            public_key_bytes = int(str(raw_row.get("public_key_bytes")), 10)
        except Exception as exc:
            raise ExternalPqEvidenceError(f"external PQ size evidence for {alg} is invalid") from exc
        if signature_bytes != spec.signature_bytes:
            raise ExternalPqEvidenceError(f"external PQ signature size for {alg} disagrees with standards registry")
        if spec.public_key_bytes is not None and public_key_bytes != spec.public_key_bytes:
            raise ExternalPqEvidenceError(f"external PQ public-key size for {alg} disagrees with standards registry")
        _hex32(raw_row.get("signature_sha256", ""), field=f"{alg}.signature_sha256")
        target = _nonempty(raw_row.get("execution_target"), field=f"{alg}.execution_target")
        library = _nonempty(raw_row.get("library"), field=f"{alg}.library")
        targets.add(target)
        libraries.add(library)
        families.add(spec.family.value)
        rows_by_algorithm[alg] = raw_row

    missing = sorted(set(required) - set(rows_by_algorithm))
    if missing:
        raise ExternalPqEvidenceError(f"external PQ evidence is missing required algorithms: {', '.join(missing)}")
    if len(targets) < minimum_execution_targets:
        raise ExternalPqEvidenceError("external PQ evidence does not contain enough distinct execution targets")
    if require_family_diversity and len(families) < 2:
        raise ExternalPqEvidenceError("external PQ evidence does not contain multiple PQ algorithm families")

    return ExternalPqEvidenceBinding(
        receipt_sha256=_canonical_hash(b"WS-QCRYPTO-EXTERNAL-PQ-EVIDENCE-QUORUM-V1", report),
        candidate_challenge_sha256=expected_challenge_sha,
        psbt_sha256=psbt,
        txid=txid,
        fee_sat=expected_fee_sat,
        algorithms=required,
        execution_targets=tuple(sorted(targets)),
        libraries=tuple(sorted(libraries)),
        pq_families=tuple(sorted(families)),
        parser_receipt_sha256=parser_hash,
    )
