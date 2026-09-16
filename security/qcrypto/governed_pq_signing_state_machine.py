"""Governed zero-value state machine for PQ signing-readiness evidence.

This module composes already-bounded QCRYPTO controls in lifecycle order:

    canonical pre-sign intent
      -> suite negotiation bound to that intent
      -> replay/freshness acceptance of the canonical action
      -> ephemeral PQ reference-signature verification of the negotiated digest
      -> human review required

It deliberately stops before human approval, transaction construction, wallet
signing, execution authority, or movement of value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from security.qcrypto.canonical_pq_context_interop import CanonicalPQInteropResult
from security.qcrypto.canonical_pq_signing_context import CanonicalSigningContextDecision
from security.qcrypto.canonical_replay_freshness_guard import ReplayFreshnessDecision
from security.qcrypto.negotiated_canonical_context import NegotiatedCanonicalContextDecision


class GovernedSigningState(StrEnum):
    BLOCKED = "BLOCKED"
    INTENT_CONTEXT_ACCEPTED = "INTENT_CONTEXT_ACCEPTED"
    SUITE_NEGOTIATION_BOUND = "SUITE_NEGOTIATION_BOUND"
    REPLAY_FRESHNESS_ACCEPTED = "REPLAY_FRESHNESS_ACCEPTED"
    PQ_REFERENCE_SIGNATURE_VERIFIED = "PQ_REFERENCE_SIGNATURE_VERIFIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


@dataclass(frozen=True)
class GovernedSigningDecision:
    verdict: str
    state: str
    ready_for_human_review: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    canonical_context_digest: str | None
    negotiated_context_digest: str | None
    negotiation_transcript_digest: str | None
    selected_suite_id: str | None
    pq_algorithm_id: str | None
    compatible_probe_count: int
    verified_compatible_probe_count: int
    replay_checkpoint_bound: bool
    human_approval_required: bool = True
    human_approval_recorded: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False
    live_transaction_signed: bool = False
    production_protocol_integration: bool = False
    end_to_end_pq_security_established: bool = False
    claim_boundary: str = (
        "Governed zero-value signing-readiness state only. HUMAN_REVIEW_REQUIRED means "
        "the bounded evidence chain reached its terminal pre-approval state; it does "
        "not grant human approval, execution authority, wallet authority, production "
        "protocol integration, or permission to move value."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


def _scheme_matches_algorithm(scheme: str, algorithm_id: str | None) -> bool:
    if algorithm_id == "ML-DSA":
        return scheme.startswith("ML-DSA-")
    if algorithm_id == "SLH-DSA":
        return scheme.startswith("SLH-DSA-")
    return False


def _blocked(
    blockers: list[str],
    warnings: list[str],
    canonical: CanonicalSigningContextDecision,
    negotiated: NegotiatedCanonicalContextDecision,
    *,
    compatible_probe_count: int = 0,
    verified_compatible_probe_count: int = 0,
    replay_checkpoint_bound: bool = False,
) -> GovernedSigningDecision:
    return GovernedSigningDecision(
        verdict="GOVERNED_PQ_SIGNING_BLOCKED",
        state=GovernedSigningState.BLOCKED.value,
        ready_for_human_review=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        canonical_context_digest=canonical.context_digest,
        negotiated_context_digest=negotiated.negotiated_context_digest,
        negotiation_transcript_digest=negotiated.negotiation_transcript_digest,
        selected_suite_id=negotiated.selected_suite_id,
        pq_algorithm_id=negotiated.pq_algorithm_id,
        compatible_probe_count=compatible_probe_count,
        verified_compatible_probe_count=verified_compatible_probe_count,
        replay_checkpoint_bound=replay_checkpoint_bound,
    )


def assess_governed_signing_readiness(
    canonical: CanonicalSigningContextDecision,
    negotiated: NegotiatedCanonicalContextDecision,
    replay: ReplayFreshnessDecision,
    pq_probes: tuple[CanonicalPQInteropResult, ...],
) -> GovernedSigningDecision:
    """Compose bounded controls without crossing into transaction authorization."""

    blockers: list[str] = []
    warnings: list[str] = []

    if not canonical.ready or not canonical.context_digest:
        blockers.append("Canonical pre-sign context is not ready.")
    if not canonical.pre_sign_intent_only or canonical.signature_presence_assumed:
        blockers.append("Canonical context does not preserve pre-sign intent semantics.")
    if any("signature_present" in key for key in canonical.canonical_fields):
        blockers.append("Canonical context contains preexisting signature-presence state.")
    if blockers:
        return _blocked(blockers, warnings, canonical, negotiated)

    if not negotiated.ready or not negotiated.negotiated_context_digest:
        blockers.append("Negotiated canonical context is not ready.")
    if negotiated.canonical_context_digest != canonical.context_digest:
        blockers.append("Negotiated context is not bound to the supplied canonical context.")
    if not negotiated.negotiation_transcript_digest:
        blockers.append("Negotiated context is missing its suite-negotiation transcript digest.")
    if not negotiated.pre_sign_intent_only or negotiated.signature_presence_assumed:
        blockers.append("Negotiated context does not preserve pre-sign intent semantics.")
    if negotiated.execution_authority or negotiated.live_value_authorized or negotiated.transaction_signed:
        blockers.append("Negotiated context improperly asserts execution or transaction authority.")
    if blockers:
        return _blocked(blockers, warnings, canonical, negotiated)

    replay_bound = False
    if not replay.accepted or replay.verdict != "REPLAY_FRESHNESS_ACCEPTED":
        blockers.append("Replay/freshness gate did not accept the canonical action.")
    if replay.next_checkpoint is None:
        blockers.append("Accepted replay/freshness result is missing its next checkpoint.")
    else:
        replay_bound = replay.next_checkpoint.last_context_digest == canonical.context_digest
        if not replay_bound:
            blockers.append("Replay checkpoint is not bound to the supplied canonical context digest.")
    if replay.execution_authority or replay.live_value_authorized or replay.transaction_authorized:
        blockers.append("Replay/freshness result improperly asserts transaction authority.")
    if blockers:
        return _blocked(
            blockers,
            warnings,
            canonical,
            negotiated,
            replay_checkpoint_bound=replay_bound,
        )

    compatible = tuple(
        probe for probe in pq_probes if _scheme_matches_algorithm(probe.scheme, negotiated.pq_algorithm_id)
    )
    if not compatible:
        blockers.append(
            "No PQ reference-signature probe is compatible with the negotiated PQ algorithm family."
        )

    verified = []
    for probe in compatible:
        if probe.canonical_context_digest != negotiated.negotiated_context_digest:
            blockers.append(
                f"PQ probe {probe.scheme} is not bound to the negotiated context digest."
            )
            continue
        if not (
            probe.valid_signature_verified
            and probe.tampered_context_rejected
            and probe.cross_context_replay_rejected
            and probe.wrong_key_rejected
            and probe.test_signature_generated
            and not probe.secret_material_retained
            and not probe.live_transaction_signed
            and not probe.live_value_authorized
            and not probe.execution_authority
        ):
            blockers.append(f"PQ probe {probe.scheme} did not satisfy fail-closed test controls.")
            continue
        verified.append(probe)

    incompatible_count = len(pq_probes) - len(compatible)
    if incompatible_count:
        warnings.append(
            f"{incompatible_count} probe(s) were outside the negotiated PQ algorithm family and were not used for readiness."
        )

    if blockers:
        return _blocked(
            blockers,
            warnings,
            canonical,
            negotiated,
            compatible_probe_count=len(compatible),
            verified_compatible_probe_count=len(verified),
            replay_checkpoint_bound=replay_bound,
        )

    return GovernedSigningDecision(
        verdict="GOVERNED_PQ_SIGNING_READY_FOR_HUMAN_REVIEW",
        state=GovernedSigningState.HUMAN_REVIEW_REQUIRED.value,
        ready_for_human_review=True,
        blockers=(),
        warnings=tuple(warnings),
        canonical_context_digest=canonical.context_digest,
        negotiated_context_digest=negotiated.negotiated_context_digest,
        negotiation_transcript_digest=negotiated.negotiation_transcript_digest,
        selected_suite_id=negotiated.selected_suite_id,
        pq_algorithm_id=negotiated.pq_algorithm_id,
        compatible_probe_count=len(compatible),
        verified_compatible_probe_count=len(verified),
        replay_checkpoint_bound=True,
    )
