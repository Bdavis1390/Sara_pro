"""Bind downgrade-resistant PQC suite negotiation to a canonical pre-sign context.

The canonical context commits the authority action and migration policy.  Suite
negotiation separately commits what cryptographic suites a peer offered and which
strongest governed suite was selected.  This module requires those two views to
agree before deriving a negotiated signing commitment.

It performs no networking, key generation, signing, transaction construction,
or live-value authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import struct

from security.qcrypto.canonical_pq_signing_context import CanonicalSigningContextDecision
from security.qcrypto.pqc_suite_negotiation_guard import (
    SuiteNegotiationPolicy,
    SuiteNegotiationRequest,
    assess_suite_negotiation,
)


NEGOTIATED_SCHEMA = "WS-QCRYPTO-NEGOTIATED-CANONICAL-CONTEXT-V1"
DOMAIN_TAG = b"WS-QCRYPTO-NEGOTIATED-CONTEXT-V1\x00"


@dataclass(frozen=True)
class NegotiatedCanonicalContextDecision:
    verdict: str
    ready: bool
    blockers: tuple[str, ...]
    canonical_context_digest: str | None
    negotiation_transcript_digest: str | None
    negotiated_context_digest: str | None
    selected_suite_id: str | None
    effective_requirement: str | None
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None
    pre_sign_intent_only: bool = True
    signature_presence_assumed: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False
    transaction_signed: bool = False
    claim_boundary: str = (
        "Negotiated pre-sign commitment only. This binds an accepted suite-negotiation "
        "transcript to a canonical authority context but does not authenticate the peer, "
        "generate a signature, authorize execution, or move value."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


def _frame(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded


def _derive_digest(
    canonical_context_digest: str,
    negotiation_transcript_digest: str,
    selected_suite_id: str,
    effective_requirement: str,
) -> str:
    fields = (
        ("schema", NEGOTIATED_SCHEMA),
        ("canonical_context_digest", canonical_context_digest),
        ("negotiation_transcript_digest", negotiation_transcript_digest),
        ("selected_suite_id", selected_suite_id),
        ("effective_requirement", effective_requirement),
    )
    preimage = bytearray(DOMAIN_TAG)
    preimage.extend(struct.pack(">H", len(fields)))
    for name, value in fields:
        preimage.extend(_frame(name))
        preimage.extend(_frame(value))
    return sha256(bytes(preimage)).hexdigest()


def bind_negotiated_canonical_context(
    context: CanonicalSigningContextDecision,
    request: SuiteNegotiationRequest,
    policy: SuiteNegotiationPolicy,
) -> NegotiatedCanonicalContextDecision:
    """Require canonical intent and negotiated suite semantics to agree exactly."""

    blockers: list[str] = []
    if not context.ready or not context.context_digest or not context.canonical_fields:
        blockers.append("Canonical pre-sign context is not ready.")
    if not context.pre_sign_intent_only or context.signature_presence_assumed:
        blockers.append("Canonical context does not preserve the pre-sign intent lifecycle.")
    if any("signature_present" in key for key in context.canonical_fields):
        blockers.append("Canonical context contains preexisting signature-presence state.")

    negotiation = assess_suite_negotiation(request, policy)
    if not negotiation.accepted:
        blockers.append("PQC suite negotiation was not accepted by the governed policy.")
        blockers.extend(negotiation.blockers)

    fields = context.canonical_fields
    if fields:
        if request.network_id != fields.get("network_id"):
            blockers.append("Negotiation network id does not match canonical context.")
        if request.authority_layer.value != fields.get("authority_layer"):
            blockers.append("Negotiation authority layer does not match canonical context.")
        if str(request.policy_version) != fields.get("policy_version"):
            blockers.append("Negotiation policy version does not match canonical context.")
        if policy.minimum_requirement.name != fields.get("policy_minimum_requirement"):
            blockers.append("Negotiation minimum requirement does not match canonical policy floor.")

        canonical_classical = fields.get("classical_algorithm_id")
        canonical_pq = fields.get("pq_algorithm_id")
        canonical_effective = fields.get("effective_migration_requirement")
        decision_classical = negotiation.classical_algorithm_id or "NONE"
        decision_pq = negotiation.pq_algorithm_id or "NONE"
        if decision_classical != canonical_classical:
            blockers.append("Negotiated classical algorithm does not match canonical intent.")
        if decision_pq != canonical_pq:
            blockers.append("Negotiated PQ algorithm does not match canonical intent.")
        if negotiation.effective_requirement != canonical_effective:
            blockers.append("Negotiated migration requirement does not match canonical intent.")

    if blockers or not negotiation.negotiation_transcript_digest:
        if not negotiation.negotiation_transcript_digest and negotiation.accepted:
            blockers.append("Accepted suite negotiation is missing its transcript digest.")
        return NegotiatedCanonicalContextDecision(
            verdict="NEGOTIATED_CANONICAL_CONTEXT_BLOCKED",
            ready=False,
            blockers=tuple(blockers),
            canonical_context_digest=context.context_digest,
            negotiation_transcript_digest=negotiation.negotiation_transcript_digest,
            negotiated_context_digest=None,
            selected_suite_id=negotiation.selected_suite_id,
            effective_requirement=negotiation.effective_requirement,
            classical_algorithm_id=negotiation.classical_algorithm_id,
            pq_algorithm_id=negotiation.pq_algorithm_id,
        )

    assert context.context_digest is not None
    assert negotiation.negotiation_transcript_digest is not None
    assert negotiation.selected_suite_id is not None
    assert negotiation.effective_requirement is not None
    digest = _derive_digest(
        context.context_digest,
        negotiation.negotiation_transcript_digest,
        negotiation.selected_suite_id,
        negotiation.effective_requirement,
    )
    return NegotiatedCanonicalContextDecision(
        verdict="NEGOTIATED_CANONICAL_CONTEXT_READY",
        ready=True,
        blockers=(),
        canonical_context_digest=context.context_digest,
        negotiation_transcript_digest=negotiation.negotiation_transcript_digest,
        negotiated_context_digest=digest,
        selected_suite_id=negotiation.selected_suite_id,
        effective_requirement=negotiation.effective_requirement,
        classical_algorithm_id=negotiation.classical_algorithm_id,
        pq_algorithm_id=negotiation.pq_algorithm_id,
    )
