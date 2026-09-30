"""Enforce transaction, witness, detached-signature, and authorization size budgets.

The goal is to turn size/fee benchmarking into a release control.  The estimates are
conservative for the explicitly supported common input types.  Unknown script spend
paths fail closed unless the caller supplies an explicit per-input weight override.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .crypto_agility import algorithm_spec, normalize_algorithm_id
from .psbt_guard import ParsedPsbt, PsbtAuditReport


class ResourceBudgetError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResourceBudgetPolicy:
    max_psbt_bytes: int = 1_000_000
    max_unsigned_vsize: int = 100_000
    max_projected_signed_vsize: int = 100_000
    max_projected_weight_wu: int = 400_000
    max_detached_pq_signature_bytes: int = 65_536
    max_total_authorization_bytes: int = 131_072
    allow_unknown_input_weight: bool = False

    def canonical_dict(self) -> dict:
        values = asdict(self)
        for key, value in values.items():
            if key == "allow_unknown_input_weight":
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ResourceBudgetError(f"{key} must be a positive integer")
        return values

    @property
    def policy_sha256(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-RESOURCE-POLICY-V1\x00" + body).hexdigest()


@dataclass(frozen=True)
class ResourceBudgetReport:
    psbt_bytes: int
    unsigned_vsize: int
    projected_signed_weight_wu: int
    projected_signed_vsize: int
    projected_detached_pq_signature_bytes: int
    projected_authorization_bytes: int
    input_script_types: tuple[str, ...]
    unknown_weight_input_indexes: tuple[int, ...]
    limits_exceeded: tuple[str, ...]
    satisfied: bool
    policy_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


# Conservative incremental weight relative to an unsigned input whose scriptSig is
# empty and whose witness is absent.  These are release-policy estimates, not
# consensus constants.
#   P2WPKH: witness stack ~109 bytes + shared marker/flag handled separately.
#   P2TR key path: 1 stack item + 64/65 byte Schnorr signature => <=67 bytes.
#   P2PKH: scriptSig push(sig) + push(pubkey) <=108 extra base bytes => 432 WU.
#   P2PK: scriptSig push(sig) <=74 extra base bytes => 296 WU.
_INPUT_INCREMENTAL_WEIGHT = {
    "P2WPKH": 109,
    "P2TR": 67,
    "P2PKH": 432,
    "P2PK": 296,
}
_SEGWIT_TYPES = {"P2WPKH", "P2WSH", "P2TR"}


def evaluate_resource_budget(
    raw_psbt: bytes,
    psbt: ParsedPsbt,
    audit: PsbtAuditReport,
    *,
    policy: ResourceBudgetPolicy,
    detached_pq_algorithms: Sequence[str] = (),
    authorization_overhead_bytes: int = 4096,
    unknown_input_weight_overrides: Mapping[int, int] | None = None,
) -> ResourceBudgetReport:
    cfg = policy.canonical_dict()
    if not isinstance(raw_psbt, (bytes, bytearray)):
        raise ResourceBudgetError("raw_psbt must be bytes")
    if authorization_overhead_bytes < 0:
        raise ResourceBudgetError("authorization_overhead_bytes must be non-negative")
    overrides = dict(unknown_input_weight_overrides or {})
    input_types = tuple(str(x) for x in audit.metadata_exposure.get("input_script_types", ()))
    if len(input_types) != len(psbt.transaction.inputs):
        raise ResourceBudgetError("PSBT audit did not expose every input script type")

    base_bytes = audit.minimum_unsigned_vsize
    weight = base_bytes * 4
    unknown: list[int] = []
    any_segwit = False
    for index, script_type in enumerate(input_types):
        if script_type in _SEGWIT_TYPES:
            any_segwit = True
        inc = _INPUT_INCREMENTAL_WEIGHT.get(script_type)
        if inc is None:
            inc = overrides.get(index)
            if inc is None:
                unknown.append(index)
                continue
            if not isinstance(inc, int) or isinstance(inc, bool) or inc <= 0:
                raise ResourceBudgetError("unknown input weight override must be a positive integer")
        weight += inc
    if any_segwit:
        # marker + flag are witness-serialized bytes and therefore one WU each.
        weight += 2

    pq_bytes = 0
    for alg in detached_pq_algorithms:
        spec = algorithm_spec(normalize_algorithm_id(alg))
        if spec.family.value == "CLASSICAL_ECC":
            continue
        pq_bytes += spec.signature_bytes
    projected_vsize = (weight + 3) // 4
    auth_bytes = pq_bytes + authorization_overhead_bytes

    exceeded: list[str] = []
    if len(raw_psbt) > cfg["max_psbt_bytes"]:
        exceeded.append("PSBT_BYTES")
    if base_bytes > cfg["max_unsigned_vsize"]:
        exceeded.append("UNSIGNED_VSIZE")
    if weight > cfg["max_projected_weight_wu"]:
        exceeded.append("PROJECTED_SIGNED_WEIGHT")
    if projected_vsize > cfg["max_projected_signed_vsize"]:
        exceeded.append("PROJECTED_SIGNED_VSIZE")
    if pq_bytes > cfg["max_detached_pq_signature_bytes"]:
        exceeded.append("DETACHED_PQ_SIGNATURE_BYTES")
    if auth_bytes > cfg["max_total_authorization_bytes"]:
        exceeded.append("TOTAL_AUTHORIZATION_BYTES")
    if unknown and not cfg["allow_unknown_input_weight"]:
        exceeded.append("UNKNOWN_INPUT_WEIGHT")
    return ResourceBudgetReport(
        psbt_bytes=len(raw_psbt),
        unsigned_vsize=base_bytes,
        projected_signed_weight_wu=weight,
        projected_signed_vsize=projected_vsize,
        projected_detached_pq_signature_bytes=pq_bytes,
        projected_authorization_bytes=auth_bytes,
        input_script_types=input_types,
        unknown_weight_input_indexes=tuple(unknown),
        limits_exceeded=tuple(exceeded),
        satisfied=not exceeded,
        policy_sha256=policy.policy_sha256,
    )
