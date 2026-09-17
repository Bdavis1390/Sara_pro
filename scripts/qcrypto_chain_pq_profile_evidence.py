#!/usr/bin/env python3
"""Generate bounded source-backed cryptocurrency PQ readiness evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from security.qcrypto.chain_pq_readiness_profiles import (
    ALGORAND,
    BITCOIN,
    ETHEREUM,
    assess_chain_profile,
)


def _profile_record(profile):
    return {
        "chain_id": profile.chain_id,
        "evidence_as_of": profile.evidence_as_of,
        "source_class": profile.source_class,
        "observations": [
            {
                "layer": item.layer.value,
                "readiness": item.readiness.name,
                "statement": item.statement,
                "source_urls": list(item.source_urls),
            }
            for item in profile.observations
        ],
        "decision": assess_chain_profile(profile).to_dict(),
    }


def build_evidence() -> dict:
    profiles = {
        profile.chain_id: _profile_record(profile)
        for profile in (BITCOIN, ETHEREUM, ALGORAND)
    }
    evidence = {
        "schema": "WS-QCRYPTO-CHAIN-PQ-READINESS-PROFILES-V1",
        "status": "PASS",
        "scope": "PUBLIC_SOURCE_MIGRATION_READINESS_ONLY",
        "profiles": profiles,
        "summary": {
            "profile_count": len(profiles),
            "migration_ready_chain_count": sum(
                1
                for record in profiles.values()
                if record["decision"]["migration_target_reached"]
            ),
            "whole_chain_pq_security_established_count": 0,
            "production_deployment_established_count": 0,
            "live_value_authorized": False,
            "execution_authority": False,
        },
        "claim_boundary": (
            "Dated public-source readiness profiles only. These records do not establish "
            "protocol conformance, comprehensive ecosystem coverage, production migration, "
            "third-party validation, or end-to-end post-quantum security."
        ),
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="chain-pq-readiness-profiles.json")
    args = parser.parse_args()
    evidence = build_evidence()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("chain_pq_profile_status:", evidence["status"])
    print("evidence_sha256:", evidence["evidence_sha256"])


if __name__ == "__main__":
    main()
