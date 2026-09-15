#!/usr/bin/env python3
"""Generate machine-readable WS-QPOS family-preservation proof evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.pos_family_preservation import PROFILES, run_family_preservation_proof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_family_preservation_proof()
    payload = {
        "schema": "WS-QPOS-FAMILY-PRESERVATION-PROOF-V1",
        "proof_scope": "BOUNDED_MULTI_POS_ADAPTER_MODEL_ONLY",
        "report": report.to_dict(),
        "profiles": {
            key: {
                "network": profile.network,
                "consensus_family": profile.consensus_family,
                "weight_semantics": profile.weight_semantics,
                "classical_consensus_credentials": list(profile.classical_consensus_credentials),
                "protected_fields": list(profile.protected_fields),
                "identity_coupling": profile.identity_coupling,
                "reviewed_pq_status": profile.reviewed_pq_status,
                "source_urls": list(profile.source_urls),
            }
            for key, profile in sorted(PROFILES.items())
        },
        "concrete_pq_profile": "ML-DSA-65 is used as the migration credential label; cryptographic round-trip evidence is produced by the separate WS-QPOS-2 interop gate.",
        "production_chain_security": "NOT_PROVEN_HERE",
        "live_network_actions": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_sha256"] = sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
