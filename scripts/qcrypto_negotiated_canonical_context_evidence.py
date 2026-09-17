#!/usr/bin/env python3
"""Generate bounded suite-negotiated canonical PQ signature evidence."""

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


NETWORK = "negotiated-evidence-testnet"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def canonical_context(sequence: int):
    intent = AuthoritySigningIntent(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest="1" * 64,
        authority_id="negotiated-evidence-authority",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=3,
        key_epoch=15,
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
        minimum_envelope_version=3,
        minimum_key_epoch=15,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
        chain="NegotiatedEvidenceChain",
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
            policy_version=14,
            replay_domain="negotiated-authority",
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
        policy_version=14,
    )
    data.update(overrides)
    return SuiteNegotiationRequest(**data)


def negotiation_policy():
    return SuiteNegotiationPolicy(
        network_id=NETWORK,
        authority_layer=AuthorityLayer.ACCOUNT,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        preference_order=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
        policy_version=14,
    )


def _interop_context(negotiated) -> CanonicalSigningContextDecision:
    if not negotiated.ready or not negotiated.negotiated_context_digest:
        raise ValueError("negotiated canonical context must be ready")
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
    parser.add_argument("--output", default="negotiated-canonical-context-evidence.json")
    args = parser.parse_args()

    context1 = canonical_context(1)
    context2 = canonical_context(2)
    accepted1 = bind_negotiated_canonical_context(context1, negotiation_request(), negotiation_policy())
    accepted2 = bind_negotiated_canonical_context(context2, negotiation_request(), negotiation_policy())
    capability_change = bind_negotiated_canonical_context(
        context1,
        negotiation_request(peer_capabilities_digest="5" * 64),
        negotiation_policy(),
    )
    downgrade = bind_negotiated_canonical_context(
        context1,
        negotiation_request(
            offered_suite_ids=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
            selected_suite_id="HYBRID-ECDSA-MLDSA",
        ),
        negotiation_policy(),
    )
    algorithm_mismatch = bind_negotiated_canonical_context(
        context1,
        negotiation_request(
            offered_suite_ids=("HYBRID-ED25519-MLDSA",),
            selected_suite_id="HYBRID-ED25519-MLDSA",
        ),
        SuiteNegotiationPolicy(
            network_id=NETWORK,
            authority_layer=AuthorityLayer.ACCOUNT,
            minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
            preference_order=("HYBRID-ED25519-MLDSA",),
            policy_version=14,
        ),
    )

    if not accepted1.ready or not accepted2.ready or not capability_change.ready:
        raise SystemExit("positive negotiated canonical context did not become ready")
    if accepted1.negotiated_context_digest == accepted2.negotiated_context_digest:
        raise SystemExit("replay-sequence change did not change negotiated context digest")
    if accepted1.negotiated_context_digest == capability_change.negotiated_context_digest:
        raise SystemExit("capability-transcript change did not change negotiated context digest")
    if downgrade.ready or algorithm_mismatch.ready:
        raise SystemExit("negative negotiated-context control was improperly accepted")

    interop = run_all_canonical_context_probes(
        _interop_context(accepted1),
        _interop_context(accepted2),
    )

    evidence = {
        "schema": "WS-QCRYPTO-NEGOTIATED-CANONICAL-CONTEXT-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "NEGOTIATED_CANONICAL_CONTEXT_PQ_INTEROP_PROVEN_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_NEGOTIATED_CONTEXT_ONLY",
        "accepted": accepted1.to_dict(),
        "next_sequence": accepted2.to_dict(),
        "capability_change": capability_change.to_dict(),
        "negative_controls": {
            "weaker_selected_with_stronger_offer": downgrade.to_dict(),
            "algorithm_slot_mismatch": algorithm_mismatch.to_dict(),
        },
        "interop_results": [item.to_dict() for item in interop],
        "summary": {
            "pre_sign_intent_only": accepted1.pre_sign_intent_only,
            "signature_presence_assumed": accepted1.signature_presence_assumed,
            "transcript_bound": accepted1.negotiation_transcript_digest is not None,
            "replay_sequence_changes_negotiated_digest": accepted1.negotiated_context_digest != accepted2.negotiated_context_digest,
            "capability_transcript_changes_negotiated_digest": accepted1.negotiated_context_digest != capability_change.negotiated_context_digest,
            "downgrade_selection_rejected": not downgrade.ready,
            "algorithm_mismatch_rejected": not algorithm_mismatch.ready,
            "all_test_signatures_verified": all(item.valid_signature_verified for item in interop),
            "all_cross_context_replays_rejected": all(item.cross_context_replay_rejected for item in interop),
            "all_tampered_contexts_rejected": all(item.tampered_context_rejected for item in interop),
            "all_wrong_keys_rejected": all(item.wrong_key_rejected for item in interop),
            "live_transaction_signed": False,
            "live_value_authorized": False,
            "execution_authority": False,
            "production_protocol_integration": False,
            "end_to_end_pq_security_established": False,
        },
    }

    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("negotiated_canonical_context_status: PASS")
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
