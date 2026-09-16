#!/usr/bin/env python3
"""Generate zero-value PQ signature evidence after canonical pre-sign intent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_context_interop import run_all_canonical_context_probes
from security.qcrypto.canonical_pq_signing_context import (
    AuthoritySigningIntent,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.hybrid_authority_migration import (
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)
from security.qcrypto.pq_signature_interop import SCHEMES


PAYLOAD = "1" * 64
EVIDENCE = "2" * 64
RECOVERY = "3" * 64


def intent() -> AuthoritySigningIntent:
    return AuthoritySigningIntent(
        network_id="canonical-interop-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        payload_digest=PAYLOAD,
        authority_id="canonical-interop-authority",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=6,
        key_epoch=40,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )


def policy() -> AuthorityPolicy:
    return AuthorityPolicy(
        network_id="canonical-interop-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=6,
        minimum_key_epoch=40,
        require_recovery_evidence=True,
    )


def adapter() -> CanonicalAuthorityEnvelope:
    return CanonicalAuthorityEnvelope(
        chain="CanonicalInteropChain",
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


def signing_context(sequence: int):
    return build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent(),
            authority_policy=policy(),
            adapter=adapter(),
            policy_version=10,
            replay_domain="canonical-context-interop",
            replay_sequence=sequence,
            evidence_digest=EVIDENCE,
            recovery_commitment_digest=RECOVERY,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="canonical-pq-context-interop-evidence.json")
    args = parser.parse_args()

    primary = signing_context(700)
    alternate = signing_context(701)
    if not primary.ready or not alternate.ready:
        raise SystemExit("canonical pre-sign contexts were not ready")
    if not primary.pre_sign_intent_only or primary.signature_presence_assumed:
        raise SystemExit("pre-sign lifecycle boundary was not preserved")
    if primary.context_digest == alternate.context_digest:
        raise SystemExit("replay negative control did not produce a distinct commitment")

    results = run_all_canonical_context_probes(primary, alternate)
    for result in results:
        if not (
            result.valid_signature_verified
            and result.tampered_context_rejected
            and result.cross_context_replay_rejected
            and result.wrong_key_rejected
            and result.test_signature_generated
            and not result.secret_material_retained
            and not result.live_transaction_signed
            and not result.live_value_authorized
            and not result.execution_authority
        ):
            raise SystemExit(f"canonical PQ interop negative control failed for {result.scheme}")

    evidence = {
        "schema": "WS-QCRYPTO-CANONICAL-PQ-CONTEXT-INTEROP-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "CANONICAL_CONTEXT_PQ_SIGNATURE_INTEROPERABILITY_PROVEN_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_CANONICAL_CONTEXT_ONLY",
        "backend": {"package": "pqcrypto", "pinned_version": "1.0.0"},
        "pre_sign_intent_only": primary.pre_sign_intent_only,
        "signature_presence_assumed": primary.signature_presence_assumed,
        "primary_context_digest": primary.context_digest,
        "alternate_context_digest": alternate.context_digest,
        "scheme_count": len(SCHEMES),
        "schemes": list(SCHEMES),
        "results": [result.to_dict() for result in results],
        "summary": {
            "intent_before_signature_generation": True,
            "all_valid_signatures_verified": all(r.valid_signature_verified for r in results),
            "all_tampered_contexts_rejected": all(r.tampered_context_rejected for r in results),
            "all_cross_context_replays_rejected": all(r.cross_context_replay_rejected for r in results),
            "all_wrong_keys_rejected": all(r.wrong_key_rejected for r in results),
            "secret_material_in_evidence": False,
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

    print("canonical_pq_context_interop_status: PASS")
    print("scheme_count:", evidence["scheme_count"])
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
