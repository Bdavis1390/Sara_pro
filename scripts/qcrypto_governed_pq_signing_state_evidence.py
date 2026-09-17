#!/usr/bin/env python3
"""Generate zero-value governed PQ signing-state evidence with real PQ test probes."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_context_interop import run_all_canonical_context_probes
from security.qcrypto.canonical_pq_signing_context import (
    AuthoritySigningIntent,
    CanonicalSigningContextDecision,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.canonical_replay_freshness_guard import (
    ReplayCandidate,
    ReplayFreshnessPolicy,
    assess_replay_freshness,
)
from security.qcrypto.governed_pq_signing_state_machine import assess_governed_signing_readiness
from security.qcrypto.hybrid_authority_migration import (
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)
from security.qcrypto.negotiated_canonical_context import bind_negotiated_canonical_context
from security.qcrypto.pqc_suite_negotiation_guard import (
    SuiteNegotiationPolicy,
    SuiteNegotiationRequest,
)


NETWORK = "governed-signing-evidence-testnet"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def canonical_context(sequence: int):
    intent = AuthoritySigningIntent(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest="1" * 64,
        authority_id="governed-signing-authority",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=4,
        key_epoch=20,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    policy = AuthorityPolicy(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=4,
        minimum_key_epoch=20,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
        chain="GovernedSigningEvidenceChain",
        adapter_class="PROGRAMMABLE_AUTH",
        stable_authority_id=True,
        authenticator_versioned=True,
        authenticator_replaceable=True,
        policy_versioned=True,
        recovery_commitment_present=True,
        chain_binding_present=True,
        replay_domain_present=True,
        evidence_binding_present=True,
        explicit_human_approval_required=True,
        live_chain_support=False,
        independent_review_complete=False,
        consensus_layer_pq=False,
    )
    return build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent,
            authority_policy=policy,
            adapter=adapter,
            policy_version=15,
            replay_domain="governed-signing",
            replay_sequence=sequence,
            evidence_digest="2" * 64,
            recovery_commitment_digest="3" * 64,
        )
    )


def negotiation_request(**overrides):
    data = dict(
        network_id=NETWORK,
        authority_layer=AuthorityLayer.ACCOUNT,
        offered_suite_ids=("HYBRID-ECDSA-MLDSA",),
        selected_suite_id="HYBRID-ECDSA-MLDSA",
        peer_capabilities_digest="4" * 64,
        policy_version=15,
    )
    data.update(overrides)
    return SuiteNegotiationRequest(**data)


def negotiation_policy():
    return SuiteNegotiationPolicy(
        network_id=NETWORK,
        authority_layer=AuthorityLayer.ACCOUNT,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        preference_order=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
        policy_version=15,
    )


def interop_context(negotiated) -> CanonicalSigningContextDecision:
    if not negotiated.ready or not negotiated.negotiated_context_digest:
        raise ValueError("negotiated context must be ready before PQ test interop")
    return CanonicalSigningContextDecision(
        verdict="CANONICAL_SIGNING_CONTEXT_READY",
        ready=True,
        blockers=(),
        context_schema="WS-QCRYPTO-NEGOTIATED-CANONICAL-CONTEXT-V1",
        context_digest=negotiated.negotiated_context_digest,
        canonical_preimage_hex=None,
        canonical_fields={
            "binding_type": "NEGOTIATED_CANONICAL_CONTEXT",
            "selected_suite_id": negotiated.selected_suite_id or "",
            "effective_requirement": negotiated.effective_requirement or "",
        },
        pre_sign_intent_only=True,
        signature_presence_assumed=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="governed-pq-signing-state-evidence.json")
    args = parser.parse_args()

    canonical1 = canonical_context(1)
    canonical2 = canonical_context(2)
    if not canonical1.ready or not canonical2.ready:
        raise SystemExit("canonical pre-sign contexts were not ready")

    negotiated1 = bind_negotiated_canonical_context(
        canonical1, negotiation_request(), negotiation_policy()
    )
    negotiated2 = bind_negotiated_canonical_context(
        canonical2, negotiation_request(), negotiation_policy()
    )
    if not negotiated1.ready or not negotiated2.ready:
        raise SystemExit("negotiated canonical contexts were not ready")

    replay_policy = ReplayFreshnessPolicy(
        maximum_validity_seconds=900,
        maximum_clock_skew_seconds=30,
        require_strict_sequence_increment=True,
    )
    candidate1 = ReplayCandidate(
        context=canonical1,
        valid_from_epoch_seconds=1_000,
        valid_until_epoch_seconds=1_600,
        observed_at_epoch_seconds=1_200,
    )
    replay1 = assess_replay_freshness(candidate1, replay_policy)
    if not replay1.accepted or replay1.next_checkpoint is None:
        raise SystemExit("first replay/freshness candidate was not accepted")

    probes = run_all_canonical_context_probes(
        interop_context(negotiated1),
        interop_context(negotiated2),
    )
    complete = assess_governed_signing_readiness(
        canonical1, negotiated1, replay1, probes
    )

    duplicate_replay = assess_replay_freshness(
        candidate1, replay_policy, replay1.next_checkpoint
    )
    replay_blocked = assess_governed_signing_readiness(
        canonical1, negotiated1, duplicate_replay, probes
    )

    downgrade_negotiated = bind_negotiated_canonical_context(
        canonical1,
        negotiation_request(
            offered_suite_ids=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
            selected_suite_id="HYBRID-ECDSA-MLDSA",
        ),
        negotiation_policy(),
    )
    downgrade_blocked = assess_governed_signing_readiness(
        canonical1, downgrade_negotiated, replay1, probes
    )

    mismatched_probes = tuple(
        replace(probe, canonical_context_digest="f" * 64)
        if probe.scheme.startswith("ML-DSA-")
        else probe
        for probe in probes
    )
    digest_mismatch_blocked = assess_governed_signing_readiness(
        canonical1, negotiated1, replay1, mismatched_probes
    )

    incompatible_only = tuple(
        probe for probe in probes if probe.scheme.startswith("SLH-DSA-")
    )
    incompatible_family_blocked = assess_governed_signing_readiness(
        canonical1, negotiated1, replay1, incompatible_only
    )

    if not complete.ready_for_human_review:
        raise SystemExit("complete bounded evidence chain did not reach human review")
    if any(
        decision.ready_for_human_review
        for decision in (
            replay_blocked,
            downgrade_blocked,
            digest_mismatch_blocked,
            incompatible_family_blocked,
        )
    ):
        raise SystemExit("negative control improperly reached human review")

    evidence = {
        "schema": "WS-QCRYPTO-GOVERNED-PQ-SIGNING-STATE-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "GOVERNED_PQ_SIGNING_READINESS_PROVEN_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_PRE_APPROVAL_ONLY",
        "backend": {"package": "pqcrypto", "pinned_version": "1.0.0"},
        "complete_path": complete.to_dict(),
        "canonical": canonical1.to_dict(),
        "negotiated": negotiated1.to_dict(),
        "replay_freshness": replay1.to_dict(),
        "pq_probes": [probe.to_dict() for probe in probes],
        "negative_controls": {
            "duplicate_replay": replay_blocked.to_dict(),
            "suite_downgrade": downgrade_blocked.to_dict(),
            "signature_digest_mismatch": digest_mismatch_blocked.to_dict(),
            "incompatible_pq_family": incompatible_family_blocked.to_dict(),
        },
        "summary": {
            "terminal_state": complete.state,
            "ready_for_human_review": complete.ready_for_human_review,
            "human_approval_required": complete.human_approval_required,
            "human_approval_recorded": complete.human_approval_recorded,
            "replay_checkpoint_bound": complete.replay_checkpoint_bound,
            "compatible_probe_count": complete.compatible_probe_count,
            "verified_compatible_probe_count": complete.verified_compatible_probe_count,
            "duplicate_replay_blocked": not replay_blocked.ready_for_human_review,
            "suite_downgrade_blocked": not downgrade_blocked.ready_for_human_review,
            "signature_digest_mismatch_blocked": not digest_mismatch_blocked.ready_for_human_review,
            "incompatible_pq_family_blocked": not incompatible_family_blocked.ready_for_human_review,
            "execution_authority": False,
            "live_value_authorized": False,
            "live_transaction_signed": False,
            "production_protocol_integration": False,
            "end_to_end_pq_security_established": False,
        },
    }

    canonical_bytes = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print("governed_pq_signing_state_status: PASS")
    print("terminal_state:", complete.state)
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
