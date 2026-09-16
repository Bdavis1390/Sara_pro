from security.qcrypto.chain_canonical_test_vectors import (
    VectorClass,
    build_all_chain_canonical_vectors,
    build_chain_canonical_vector,
)


def test_all_tracked_chain_vectors_build_unique_canonical_contexts():
    vectors = build_all_chain_canonical_vectors()
    assert len(vectors) == 3
    assert {v.chain_id for v in vectors} == {"BITCOIN", "ETHEREUM", "ALGORAND"}
    assert all(v.canonical_context_ready for v in vectors)
    digests = {v.canonical_context_digest for v in vectors}
    assert None not in digests
    assert len(digests) == 3


def test_bitcoin_vector_remains_design_only_and_does_not_claim_native_pq():
    vector = build_chain_canonical_vector("BITCOIN")
    assert vector.vector_class == VectorClass.DESIGN_ONLY.value
    assert vector.account_readiness == "CLASSICAL"
    assert vector.native_classical_algorithm == "ECDSA"
    assert vector.native_pq_algorithm is None
    assert vector.ws_reference_pq_algorithm == "ML-DSA"
    assert vector.live_native_pq_account_support is False
    assert vector.native_and_reference_algorithm_same is False
    assert vector.native_transaction_format_implemented is False
    assert vector.native_signature_generated is False
    assert vector.production_protocol_integration is False
    assert vector.whole_chain_pq_security_established is False
    assert any("classical blocking layers" in blocker for blocker in vector.blockers)


def test_ethereum_vector_is_roadmap_reference_with_classical_mainnet_blockers():
    vector = build_chain_canonical_vector("ETHEREUM")
    assert vector.vector_class == VectorClass.ROADMAP_INTEROP.value
    assert vector.account_readiness == "CLASSICAL"
    assert vector.consensus_readiness == "CLASSICAL"
    assert vector.native_classical_algorithm == "ECDSA"
    assert vector.native_pq_algorithm is None
    assert vector.ws_reference_pq_algorithm == "ML-DSA"
    assert vector.live_native_pq_account_support is False
    assert vector.native_transaction_format_implemented is False
    assert vector.live_value_authorized is False
    assert vector.execution_authority is False


def test_algorand_credits_live_falcon_accounts_without_relabeling_them_mldsa():
    vector = build_chain_canonical_vector("ALGORAND")
    assert vector.vector_class == VectorClass.LIVE_ACCOUNT_REFERENCE.value
    assert vector.account_readiness == "PQ_CAPABLE"
    assert vector.consensus_readiness == "CLASSICAL"
    assert vector.native_classical_algorithm == "ED25519"
    assert vector.native_pq_algorithm == "FALCON-1024"
    assert vector.ws_reference_pq_algorithm == "ML-DSA"
    assert vector.native_and_reference_algorithm_same is False
    assert vector.live_native_pq_account_support is True
    assert vector.canonical_fields["classical_algorithm_id"] == "ED25519"
    assert vector.canonical_fields["pq_algorithm_id"] == "ML-DSA"
    assert vector.native_signature_generated is False
    assert vector.native_transaction_format_implemented is False
    assert vector.production_protocol_integration is False
    assert vector.whole_chain_pq_security_established is False
    assert any("distinct" in blocker for blocker in vector.blockers)


def test_all_vectors_preserve_source_provenance_and_zero_value_boundary():
    for vector in build_all_chain_canonical_vectors():
        assert vector.profile_evidence_as_of == "2026-09-15"
        assert vector.source_urls
        assert all(url.startswith("https://") for url in vector.source_urls)
        assert vector.canonical_context_digest is not None
        assert len(vector.canonical_context_digest) == 64
        assert vector.canonical_preimage_hex is not None
        assert vector.live_value_authorized is False
        assert vector.execution_authority is False
        assert vector.native_transaction_format_implemented is False
        assert vector.native_signature_generated is False


def test_unknown_chain_vector_is_rejected():
    try:
        build_chain_canonical_vector("UNKNOWN")
    except ValueError as exc:
        assert "unsupported chain vector" in str(exc)
    else:
        raise AssertionError("unknown chain vector was improperly accepted")
