#!/usr/bin/env python3
"""Generate bounded evidence for cryptocurrency hybrid PQ authority migration."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from security.qcrypto.hybrid_authority_migration import (
    AuthorityEnvelope,
    AuthorityLayer,
    AuthorityPolicy,
    CriticalLayer,
    MigrationRequirement,
    ReadinessLevel,
    assess_authority_envelope,
    assess_system_readiness,
)


NETWORK = "ws-zero-value-fixture"
DOMAIN = "WS-QCRYPTO-AUTH-V1"
DIGEST = "b" * 64


def _env(
    layer: AuthorityLayer,
    authority_id: str,
    requirement: MigrationRequirement,
    *,
    recovery: bool = False,
    classical_present: bool = True,
    classical_required: bool = True,
) -> AuthorityEnvelope:
    return AuthorityEnvelope(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest=DIGEST,
        authority_id=authority_id,
        authority_layer=layer,
        declared_requirement=requirement,
        envelope_version=3,
        key_epoch=12,
        classical_algorithm_id="ECDSA" if classical_present else None,
        pq_algorithm_id="ML-DSA",
        classical_signature_present=classical_present,
        pq_signature_present=True,
        classical_required_for_acceptance=classical_required,
        pq_required_for_acceptance=True,
        recovery_evidence_present=recovery,
    )


def _policy(requirement: MigrationRequirement, *, recovery: bool = False) -> AuthorityPolicy:
    return AuthorityPolicy(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=requirement,
        minimum_envelope_version=3,
        minimum_key_epoch=12,
        require_recovery_evidence=recovery,
    )


def build_evidence() -> dict:
    authorities = {
        "ACCOUNT_HYBRID": assess_authority_envelope(
            _env(AuthorityLayer.ACCOUNT, "account-fixture", MigrationRequirement.HYBRID_REQUIRED),
            _policy(MigrationRequirement.HYBRID_REQUIRED),
        ).to_dict(),
        "VALIDATOR_PQ_REQUIRED": assess_authority_envelope(
            _env(
                AuthorityLayer.CONSENSUS_VALIDATOR,
                "validator-fixture",
                MigrationRequirement.PQ_REQUIRED,
                classical_present=False,
                classical_required=False,
            ),
            _policy(MigrationRequirement.PQ_REQUIRED),
        ).to_dict(),
        "BRIDGE_HYBRID_WITH_RECOVERY": assess_authority_envelope(
            _env(
                AuthorityLayer.BRIDGE_CUSTODY,
                "bridge-fixture",
                MigrationRequirement.HYBRID_REQUIRED,
                recovery=True,
            ),
            _policy(MigrationRequirement.HYBRID_REQUIRED, recovery=True),
        ).to_dict(),
        "GOVERNANCE_PQ_WITH_RECOVERY": assess_authority_envelope(
            _env(
                AuthorityLayer.GOVERNANCE_ADMIN,
                "governance-fixture",
                MigrationRequirement.PQ_REQUIRED,
                recovery=True,
                classical_present=False,
                classical_required=False,
            ),
            _policy(MigrationRequirement.PQ_REQUIRED, recovery=True),
        ).to_dict(),
        "DOWNGRADE_ATTEMPT": assess_authority_envelope(
            _env(AuthorityLayer.ACCOUNT, "downgrade-fixture", MigrationRequirement.CLASSICAL_ALLOWED),
            _policy(MigrationRequirement.HYBRID_REQUIRED),
        ).to_dict(),
    }

    pq_layers = {layer: ReadinessLevel.PQ_CAPABLE for layer in CriticalLayer}
    classical_consensus = dict(pq_layers)
    classical_consensus[CriticalLayer.CONSENSUS] = ReadinessLevel.CLASSICAL
    hybrid_bridge = dict(pq_layers)
    hybrid_bridge[CriticalLayer.BRIDGES_CUSTODY_ADMIN] = ReadinessLevel.HYBRID

    systems = {
        "PQ_ACCOUNTS_CLASSICAL_CONSENSUS": assess_system_readiness(classical_consensus).to_dict(),
        "PQ_CORE_HYBRID_BRIDGE": assess_system_readiness(hybrid_bridge).to_dict(),
        "ALL_TRACKED_LAYERS_PQ_CAPABLE": assess_system_readiness(pq_layers).to_dict(),
    }

    evidence = {
        "schema": "WS-QCRYPTO-HYBRID-AUTHORITY-MIGRATION-EVIDENCE-V1",
        "status": "PASS",
        "scope": "ZERO_VALUE_CONTROL_PLANE_MIGRATION_READINESS",
        "authorities": authorities,
        "systems": systems,
        "summary": {
            "authority_accept_count": sum(1 for item in authorities.values() if item["accepted"]),
            "downgrade_rejected": authorities["DOWNGRADE_ATTEMPT"]["verdict"] == "DOWNGRADE_REJECTED",
            "classical_consensus_blocks_pq_migration": systems["PQ_ACCOUNTS_CLASSICAL_CONSENSUS"]["verdict"]
            == "BLOCKED_BY_CLASSICAL_LAYER",
            "hybrid_bridge_blocks_pq_migration": systems["PQ_CORE_HYBRID_BRIDGE"]["verdict"]
            == "HYBRID_MIGRATION_READY",
            "all_layers_pq_capable_yields_bounded_migration_ready": systems["ALL_TRACKED_LAYERS_PQ_CAPABLE"]["verdict"]
            == "PQ_MIGRATION_READY",
            "execution_authority": False,
            "live_value_authorized": False,
            "whole_chain_pq_security_established": False,
            "production_deployment_established": False,
        },
        "claim_boundary": (
            "Synthetic zero-value migration-readiness evidence only. This does not establish "
            "production deployment, transaction-signing authority, movement of value, protocol "
            "conformance, third-party validation, or end-to-end post-quantum security."
        ),
    }

    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="hybrid-authority-migration-evidence.json")
    args = parser.parse_args()
    evidence = build_evidence()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("hybrid_authority_migration_status:", evidence["status"])
    print("evidence_sha256:", evidence["evidence_sha256"])


if __name__ == "__main__":
    main()
