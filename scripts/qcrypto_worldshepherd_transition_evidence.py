#!/usr/bin/env python3
"""Generate component-level Worldshepherd PQ transition evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from security.qcrypto.pqc_algorithm_policy import Environment
from security.qcrypto.worldshepherd_pqc_transition_profile import (
    assess_all,
    assert_no_self_promotion,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assert_no_self_promotion()
    environments = {
        environment.value: {
            component_id: plan.to_dict()
            for component_id, plan in assess_all(environment=environment).items()
        }
        for environment in Environment
    }

    echo_lab = environments["LAB"]["ECHO_CHECKPOINT_SIGNATURE"]
    transport_lab = environments["LAB"]["SARA_ECHO_TRANSPORT_KEY_ESTABLISHMENT"]
    validator_testnet = environments["TESTNET"]["POS_VALIDATOR_AUTH_REFERENCE"]

    if echo_lab["transition_phase"] != "TARGET_SELECTED_IMPLEMENTATION_BLOCKED":
        raise SystemExit("ECHO checkpoint unexpectedly advanced beyond implementation-blocked")
    if echo_lab["current_algorithm"] != "ED25519":
        raise SystemExit("ECHO checkpoint current algorithm inventory changed unexpectedly")
    if echo_lab["target_algorithm"] != "ML-DSA":
        raise SystemExit("ECHO checkpoint target algorithm changed unexpectedly")
    if transport_lab["transition_phase"] != "INVENTORY_REQUIRED":
        raise SystemExit("SARA/ECHO transport unexpectedly bypassed inventory")
    if validator_testnet["transition_phase"] != "PUBLIC_TESTNET_CANDIDATE":
        raise SystemExit("PoS validator reference did not preserve public-testnet-only posture")

    flattened = [
        plan
        for environment in environments.values()
        for plan in environment.values()
    ]
    if any(plan["production_pq_ready"] for plan in flattened):
        raise SystemExit("component self-promoted to production PQ ready")
    if any(plan["end_to_end_pq_security_established"] for plan in flattened):
        raise SystemExit("component self-promoted to end-to-end PQ security")
    if any(plan["execution_authority"] for plan in flattened):
        raise SystemExit("component self-promoted execution authority")

    evidence = {
        "schema": "WS-COMPONENT-PQC-TRANSITION-EVIDENCE-V1",
        "status": "PASS",
        "environments": environments,
        "summary": {
            "component_count": len(environments["LAB"]),
            "echo_checkpoint_current_algorithm": echo_lab["current_algorithm"],
            "echo_checkpoint_target_algorithm": echo_lab["target_algorithm"],
            "echo_checkpoint_transition_phase": echo_lab["transition_phase"],
            "sara_echo_transport_transition_phase": transport_lab["transition_phase"],
            "pos_validator_reference_testnet_phase": validator_testnet["transition_phase"],
            "production_pq_ready_component_count": 0,
            "end_to_end_pq_security_component_count": 0,
            "execution_authority_component_count": 0,
            "human_approval_required_for_all": all(
                plan["human_approval_required"] for plan in flattened
            ),
            "rollback_evidence_required_for_all": all(
                plan["rollback_evidence_required"] for plan in flattened
            ),
        },
        "claim_boundary": (
            "Component transition planning and evidence classification only. Current ECHO checkpoint "
            "signing remains Ed25519; ML-DSA/SLH-DSA checkpoint runtime signing is not yet implemented. "
            "Unknown component primitives remain inventory-blocked. No production PQ readiness, key "
            "rotation, live-value authority, Federal compliance, or end-to-end PQ security is established."
        ),
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    args.output.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
