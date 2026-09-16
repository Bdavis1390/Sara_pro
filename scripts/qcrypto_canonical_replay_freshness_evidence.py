#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_signing_context import (
    AuthoritySigningIntent,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.canonical_replay_freshness_guard import (
    ReplayCandidate,
    ReplayFreshnessPolicy,
    assess_replay_freshness,
)
from security.qcrypto.hybrid_authority_migration import AuthorityLayer, AuthorityPolicy, MigrationRequirement


NETWORK = "evidence-fixture"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def context(sequence: int, *, key_epoch: int = 4, policy_version: int = 7, envelope_version: int = 3):
    intent = AuthoritySigningIntent(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest="a" * 64,
        authority_id="authority-evidence-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=envelope_version,
        key_epoch=key_epoch,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    authority_policy = AuthorityPolicy(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=1,
        minimum_key_epoch=0,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
        chain="FixtureChain",
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
    decision = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent,
            authority_policy=authority_policy,
            adapter=adapter,
            policy_version=policy_version,
            replay_domain="tx-auth",
            replay_sequence=sequence,
            evidence_digest="b" * 64,
            recovery_commitment_digest="c" * 64,
        )
    )
    if not decision.ready:
        raise RuntimeError(decision.blockers)
    return decision


def candidate(decision, observed=1_200, valid_from=1_000, valid_until=1_600):
    return ReplayCandidate(
        context=decision,
        valid_from_epoch_seconds=valid_from,
        valid_until_epoch_seconds=valid_until,
        observed_at_epoch_seconds=observed,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = ReplayFreshnessPolicy()
    first = assess_replay_freshness(candidate(context(1)), policy)
    if not first.accepted or first.next_checkpoint is None:
        raise RuntimeError(first.blockers)

    second = assess_replay_freshness(candidate(context(2)), policy, first.next_checkpoint)
    duplicate = assess_replay_freshness(candidate(context(1)), policy, first.next_checkpoint)
    expired = assess_replay_freshness(
        candidate(context(2), observed=2_000, valid_from=1_000, valid_until=1_100),
        replace(policy, maximum_clock_skew_seconds=0),
        first.next_checkpoint,
    )
    key_rollback = assess_replay_freshness(
        candidate(context(2, key_epoch=3)), policy, first.next_checkpoint
    )

    evidence = {
        "schema": "WS-QCRYPTO-CANONICAL-REPLAY-FRESHNESS-EVIDENCE-V1",
        "status": "PASS",
        "results": {
            "FIRST_ACCEPT": first.to_dict(),
            "SECOND_ACCEPT": second.to_dict(),
            "DUPLICATE_REJECT": duplicate.to_dict(),
            "EXPIRED_REJECT": expired.to_dict(),
            "KEY_EPOCH_ROLLBACK_REJECT": key_rollback.to_dict(),
        },
        "summary": {
            "monotonic_checkpoint_established": first.next_checkpoint is not None,
            "second_sequence_accepted": second.accepted,
            "duplicate_rejected": duplicate.verdict == "REPLAY_DUPLICATE_REJECTED",
            "expired_rejected": expired.verdict == "FRESHNESS_REJECTED",
            "key_epoch_rollback_rejected": key_rollback.verdict == "MONOTONIC_STATE_ROLLBACK_REJECTED",
            "execution_authority": False,
            "live_value_authorized": False,
            "transaction_authorized": False,
            "production_deployment_established": False,
        },
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
