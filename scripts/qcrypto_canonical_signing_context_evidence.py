#!/usr/bin/env python3
"""Generate zero-value evidence for the canonical PQ pre-signing context."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
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


PAYLOAD = "a" * 64
EVIDENCE = "b" * 64
RECOVERY = "c" * 64


def intent(**overrides):
    data = dict(
        network_id="evidence-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        payload_digest=PAYLOAD,
        authority_id="evidence-authority-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=4,
        key_epoch=21,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    data.update(overrides)
    return AuthoritySigningIntent(**data)


def policy(**overrides):
    data = dict(
        network_id="evidence-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=4,
        minimum_key_epoch=21,
        require_recovery_evidence=True,
    )
    data.update(overrides)
    return AuthorityPolicy(**data)


def adapter():
    return CanonicalAuthorityEnvelope(
        chain="EvidenceChain",
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


def request(**overrides):
    data = dict(
        intent=intent(),
        authority_policy=policy(),
        adapter=adapter(),
        policy_version=7,
        replay_domain="authority-action",
        replay_sequence=100,
        evidence_digest=EVIDENCE,
        recovery_commitment_digest=RECOVERY,
    )
    data.update(overrides)
    return CanonicalSigningContextRequest(**data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="canonical-signing-context-evidence.json")
    args = parser.parse_args()

    baseline = build_canonical_signing_context(request())
    cross_network = build_canonical_signing_context(
        request(
            intent=replace(intent(), network_id="other-testnet"),
            authority_policy=replace(policy(), network_id="other-testnet"),
        )
    )
    authority_domain = build_canonical_signing_context(
        request(
            intent=replace(intent(), domain_separator="WS-QCRYPTO-AUTH-V2"),
            authority_policy=replace(policy(), domain_separator="WS-QCRYPTO-AUTH-V2"),
        )
    )
    role_change = build_canonical_signing_context(
        request(intent=replace(intent(), authority_layer=AuthorityLayer.CONSENSUS_VALIDATOR))
    )
    algorithm_change = build_canonical_signing_context(
        request(intent=replace(intent(), pq_algorithm_id="SLH-DSA"))
    )
    policy_floor_change = build_canonical_signing_context(
        request(
            authority_policy=policy(
                minimum_envelope_version=3,
                minimum_key_epoch=20,
                require_recovery_evidence=False,
            )
        )
    )
    epoch_change = build_canonical_signing_context(
        request(intent=replace(intent(), key_epoch=22))
    )
    replay_change = build_canonical_signing_context(request(replay_sequence=101))
    downgrade = build_canonical_signing_context(
        request(intent=replace(intent(), declared_requirement=MigrationRequirement.CLASSICAL_ALLOWED))
    )
    self_authorize = build_canonical_signing_context(
        request(intent=replace(intent(), live_value_authorized=True))
    )

    distinct = {
        baseline.context_digest,
        cross_network.context_digest,
        authority_domain.context_digest,
        role_change.context_digest,
        algorithm_change.context_digest,
        policy_floor_change.context_digest,
        epoch_change.context_digest,
        replay_change.context_digest,
    }

    evidence = {
        "schema": "WS-QCRYPTO-CANONICAL-SIGNING-CONTEXT-EVIDENCE-V1",
        "status": "PASS",
        "baseline": baseline.to_dict(),
        "binding_variants": {
            "cross_network": cross_network.to_dict(),
            "authority_domain": authority_domain.to_dict(),
            "authority_role": role_change.to_dict(),
            "pq_algorithm": algorithm_change.to_dict(),
            "policy_floor": policy_floor_change.to_dict(),
            "key_epoch": epoch_change.to_dict(),
            "replay_sequence": replay_change.to_dict(),
        },
        "negative_controls": {
            "migration_downgrade": downgrade.to_dict(),
            "self_asserted_live_value": self_authorize.to_dict(),
        },
        "summary": {
            "distinct_context_digest_count": len(distinct),
            "expected_distinct_context_digest_count": 8,
            "pre_sign_intent_only": baseline.pre_sign_intent_only,
            "signature_presence_assumed": baseline.signature_presence_assumed,
            "authority_domain_bound": authority_domain.context_digest != baseline.context_digest,
            "policy_floor_bound": policy_floor_change.context_digest != baseline.context_digest,
            "downgrade_blocked": not downgrade.ready,
            "self_authorization_blocked": not self_authorize.ready,
            "execution_authority": False,
            "live_value_authorized": False,
            "transaction_signed": False,
            "production_deployment_established": False,
            "end_to_end_pq_security_established": False,
        },
    }

    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()

    if not baseline.ready:
        raise SystemExit("baseline canonical context did not become ready")
    if not baseline.pre_sign_intent_only or baseline.signature_presence_assumed:
        raise SystemExit("pre-sign lifecycle boundary was not preserved")
    if any("signature_present" in key for key in baseline.canonical_fields):
        raise SystemExit("canonical preimage improperly contains signature-presence state")
    if len(distinct) != 8:
        raise SystemExit("one or more governed field changes failed to change the context digest")
    if downgrade.ready or self_authorize.ready:
        raise SystemExit("negative control was improperly accepted")

    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"canonical_signing_context_status: {evidence['status']}")
    print(f"evidence_sha256: {evidence['evidence_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
