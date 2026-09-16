#!/usr/bin/env python3
"""Generate zero-value PQ interop evidence for source-backed chain vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from security.qcrypto.canonical_pq_context_interop import run_all_canonical_context_probes
from security.qcrypto.canonical_pq_signing_context import (
    CONTEXT_SCHEMA,
    CanonicalSigningContextDecision,
)
from security.qcrypto.chain_canonical_test_vectors import (
    SPECS,
    build_all_chain_canonical_vectors,
)
from security.qcrypto.pq_signature_interop import SCHEMES


def _as_context(vector) -> CanonicalSigningContextDecision:
    if not vector.canonical_context_ready:
        raise ValueError(f"chain vector is not canonical-context ready: {vector.chain_id}")
    return CanonicalSigningContextDecision(
        verdict="CANONICAL_SIGNING_CONTEXT_READY",
        ready=True,
        blockers=(),
        context_schema=CONTEXT_SCHEMA,
        context_digest=vector.canonical_context_digest,
        canonical_preimage_hex=vector.canonical_preimage_hex,
        canonical_fields=vector.canonical_fields,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="chain-canonical-vector-interop-evidence.json")
    args = parser.parse_args()

    primary = {item.chain_id: item for item in build_all_chain_canonical_vectors(0)}
    alternate = {item.chain_id: item for item in build_all_chain_canonical_vectors(1)}
    if set(primary) != set(SPECS) or set(alternate) != set(SPECS):
        raise SystemExit("chain vector set does not match controlled specification set")

    interop_results = []
    for chain_id in SPECS:
        left = primary[chain_id]
        right = alternate[chain_id]
        if left.canonical_context_digest == right.canonical_context_digest:
            raise SystemExit(f"replay sequence did not alter canonical commitment for {chain_id}")
        for result in run_all_canonical_context_probes(
            _as_context(left),
            _as_context(right),
        ):
            row = result.to_dict()
            row["chain_id"] = chain_id
            row["vector_id"] = left.vector_id
            row["vector_class"] = left.vector_class
            row["native_pq_algorithm"] = left.native_pq_algorithm
            row["ws_reference_pq_algorithm"] = left.ws_reference_pq_algorithm
            row["native_signature_generated"] = False
            interop_results.append(row)

    algorand = primary["ALGORAND"]
    bitcoin = primary["BITCOIN"]
    ethereum = primary["ETHEREUM"]

    evidence = {
        "schema": "WS-QCRYPTO-CHAIN-CANONICAL-VECTOR-INTEROP-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "THREE_CHAIN_CANONICAL_REFERENCE_PQ_INTEROP_PROVEN_IN_CI",
        "proof_scope": "SOURCE_BACKED_ZERO_VALUE_REFERENCE_VECTORS_ONLY",
        "backend": {"package": "pqcrypto", "pinned_version": "1.0.0"},
        "chain_count": len(primary),
        "scheme_count": len(SCHEMES),
        "probe_count": len(interop_results),
        "primary_vectors": {key: value.to_dict() for key, value in primary.items()},
        "alternate_vectors": {key: value.to_dict() for key, value in alternate.items()},
        "interop_results": interop_results,
        "summary": {
            "bitcoin_vector_class": bitcoin.vector_class,
            "bitcoin_native_pq_algorithm": bitcoin.native_pq_algorithm,
            "ethereum_vector_class": ethereum.vector_class,
            "ethereum_native_pq_algorithm": ethereum.native_pq_algorithm,
            "algorand_account_readiness": algorand.account_readiness,
            "algorand_consensus_readiness": algorand.consensus_readiness,
            "algorand_native_pq_algorithm": algorand.native_pq_algorithm,
            "algorand_ws_reference_pq_algorithm": algorand.ws_reference_pq_algorithm,
            "algorand_native_and_reference_algorithm_same": algorand.native_and_reference_algorithm_same,
            "all_test_signatures_verified": all(row["valid_signature_verified"] for row in interop_results),
            "all_tampered_contexts_rejected": all(row["tampered_context_rejected"] for row in interop_results),
            "all_cross_sequence_replays_rejected": all(row["cross_context_replay_rejected"] for row in interop_results),
            "all_wrong_keys_rejected": all(row["wrong_key_rejected"] for row in interop_results),
            "native_signature_generated": False,
            "native_transaction_format_implemented": False,
            "live_value_authorized": False,
            "execution_authority": False,
            "production_protocol_integration": False,
            "whole_chain_pq_security_established": False,
        },
    }

    expected_probes = len(SPECS) * len(SCHEMES)
    if len(interop_results) != expected_probes:
        raise SystemExit(f"expected {expected_probes} interop probes, got {len(interop_results)}")
    if bitcoin.native_pq_algorithm is not None:
        raise SystemExit("Bitcoin draft vector improperly claims a native PQ signature algorithm")
    if ethereum.native_pq_algorithm is not None:
        raise SystemExit("Ethereum roadmap vector improperly claims a native PQ account algorithm")
    if not (
        algorand.account_readiness == "PQ_CAPABLE"
        and algorand.consensus_readiness == "CLASSICAL"
        and algorand.native_pq_algorithm == "FALCON-1024"
        and algorand.ws_reference_pq_algorithm == "ML-DSA"
        and not algorand.native_and_reference_algorithm_same
    ):
        raise SystemExit("Algorand native/reference claims boundary drifted")
    if not all(
        row["valid_signature_verified"]
        and row["tampered_context_rejected"]
        and row["cross_context_replay_rejected"]
        and row["wrong_key_rejected"]
        and not row["secret_material_retained"]
        and not row["native_signature_generated"]
        and not row["live_transaction_signed"]
        and not row["live_value_authorized"]
        and not row["execution_authority"]
        for row in interop_results
    ):
        raise SystemExit("one or more chain canonical reference probes failed")

    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("chain_canonical_vector_interop_status: PASS")
    print("probe_count:", evidence["probe_count"])
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
