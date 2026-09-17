from security.qcrypto.chain_pq_readiness_profiles import (
    ALGORAND,
    BITCOIN,
    ETHEREUM,
    ChainProfile,
    LayerObservation,
    ObservedReadiness,
    ProfileLayer,
    assess_chain_profile,
)


def test_bitcoin_profile_is_not_promoted_from_draft_migration_proposals():
    result = assess_chain_profile(BITCOIN)
    assert result.verdict == "INCOMPLETE_EVIDENCE_WITH_KNOWN_BLOCKERS"
    assert result.migration_target_reached is False
    assert "ACCOUNTS" in result.known_blocking_layers
    assert "CONSENSUS" in result.unknown_layers
    assert result.whole_chain_pq_security_established is False


def test_ethereum_profile_exposes_multiple_classical_protocol_layers():
    result = assess_chain_profile(ETHEREUM)
    assert result.verdict == "INCOMPLETE_EVIDENCE_WITH_KNOWN_BLOCKERS"
    assert set(result.known_blocking_layers) >= {
        "ACCOUNTS",
        "CONSENSUS",
        "COMMITMENTS_ZK",
    }
    assert "TOOLING_INTEROP" in result.hybrid_layers
    assert result.migration_target_reached is False


def test_algorand_native_pq_accounts_do_not_mask_classical_consensus():
    result = assess_chain_profile(ALGORAND)
    assert result.verdict == "INCOMPLETE_EVIDENCE_WITH_KNOWN_BLOCKERS"
    assert "ACCOUNTS" in result.pq_capable_layers
    assert "CONSENSUS" in result.known_blocking_layers
    assert "TOOLING_INTEROP" in result.hybrid_layers
    assert result.migration_target_reached is False
    assert result.whole_chain_pq_security_established is False


def test_no_current_profile_is_labeled_whole_chain_pq_secure():
    for profile in (BITCOIN, ETHEREUM, ALGORAND):
        result = assess_chain_profile(profile)
        assert result.whole_chain_pq_security_established is False
        assert result.production_deployment_established is False
        assert result.live_value_authorized is False
        assert result.execution_authority is False


def test_profile_schema_missing_layer_fails_closed():
    observations = tuple(
        observation
        for observation in ALGORAND.observations
        if observation.layer is not ProfileLayer.RECOVERY
    )
    incomplete = ChainProfile(
        chain_id="ALG_INCOMPLETE_FIXTURE",
        evidence_as_of="2026-09-15",
        observations=observations,
    )
    result = assess_chain_profile(incomplete)
    assert result.verdict == "PROFILE_SCHEMA_INCOMPLETE"
    assert result.migration_target_reached is False
    assert result.unknown_layers == ("RECOVERY",)


def test_unknown_evidence_is_never_silently_promoted():
    observations = tuple(
        LayerObservation(
            layer=layer,
            readiness=(ObservedReadiness.UNKNOWN if layer is ProfileLayer.RECOVERY else ObservedReadiness.PQ_CAPABLE),
            statement="fixture",
            source_urls=("https://example.invalid/fixture",),
        )
        for layer in ProfileLayer
    )
    profile = ChainProfile(
        chain_id="UNKNOWN_RECOVERY_FIXTURE",
        evidence_as_of="2026-09-15",
        observations=observations,
    )
    result = assess_chain_profile(profile)
    assert result.verdict == "INCOMPLETE_EVIDENCE"
    assert result.migration_target_reached is False
    assert result.unknown_layers == ("RECOVERY",)


def test_fully_pq_capable_fixture_yields_migration_ready_but_not_security_claim():
    observations = tuple(
        LayerObservation(
            layer=layer,
            readiness=ObservedReadiness.PQ_CAPABLE,
            statement="synthetic readiness fixture",
            source_urls=("https://example.invalid/fixture",),
        )
        for layer in ProfileLayer
    )
    profile = ChainProfile(
        chain_id="ALL_PQ_FIXTURE",
        evidence_as_of="2026-09-15",
        observations=observations,
    )
    result = assess_chain_profile(profile)
    assert result.verdict == "PQ_MIGRATION_READY"
    assert result.migration_target_reached is True
    assert result.known_blocking_layers == ()
    assert result.unknown_layers == ()
    assert result.whole_chain_pq_security_established is False
