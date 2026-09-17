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


DIGEST = "a" * 64
DOMAIN = "WS-QCRYPTO-AUTH-V1"
NETWORK = "testnet-fixture"


def envelope(**overrides):
    data = dict(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest=DIGEST,
        authority_id="acct-fixture-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=2,
        key_epoch=7,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_signature_present=True,
        pq_signature_present=True,
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=False,
    )
    data.update(overrides)
    return AuthorityEnvelope(**data)


def policy(**overrides):
    data = dict(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=2,
        minimum_key_epoch=7,
        require_recovery_evidence=False,
    )
    data.update(overrides)
    return AuthorityPolicy(**data)


def full_layers(level=ReadinessLevel.PQ_CAPABLE):
    return {layer: level for layer in CriticalLayer}


def test_hybrid_account_envelope_passes_with_both_signature_classes():
    result = assess_authority_envelope(envelope(), policy())
    assert result.accepted is True
    assert result.verdict == "HYBRID_AUTHORITY_MIGRATION_ACCEPTED"
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.end_to_end_pq_security_established is False


def test_classical_policy_downgrade_is_rejected_even_if_signatures_are_present():
    result = assess_authority_envelope(
        envelope(declared_requirement=MigrationRequirement.CLASSICAL_ALLOWED),
        policy(minimum_requirement=MigrationRequirement.HYBRID_REQUIRED),
    )
    assert result.accepted is False
    assert result.verdict == "DOWNGRADE_REJECTED"


def test_hybrid_policy_requires_both_signature_classes_and_acceptance_dependencies():
    result = assess_authority_envelope(
        envelope(
            pq_algorithm_id=None,
            pq_signature_present=False,
            pq_required_for_acceptance=False,
        ),
        policy(),
    )
    assert result.accepted is False
    assert any("both classical and PQ" in blocker for blocker in result.blockers)


def test_pq_required_accepts_final_fips_pq_without_classical_dependency():
    result = assess_authority_envelope(
        envelope(
            declared_requirement=MigrationRequirement.PQ_REQUIRED,
            classical_algorithm_id=None,
            classical_signature_present=False,
            classical_required_for_acceptance=False,
            pq_algorithm_id="ML-DSA",
            pq_signature_present=True,
            pq_required_for_acceptance=True,
        ),
        policy(minimum_requirement=MigrationRequirement.PQ_REQUIRED),
    )
    assert result.accepted is True
    assert result.verdict == "PQ_AUTHORITY_MIGRATION_ACCEPTED"
    assert result.end_to_end_pq_security_established is False


def test_stronger_declared_requirement_becomes_effective_floor():
    result = assess_authority_envelope(
        envelope(
            declared_requirement=MigrationRequirement.PQ_REQUIRED,
            classical_required_for_acceptance=True,
            pq_required_for_acceptance=True,
        ),
        policy(minimum_requirement=MigrationRequirement.HYBRID_REQUIRED),
    )
    assert result.accepted is False
    assert any("continued classical acceptance dependency" in blocker for blocker in result.blockers)


def test_pq_required_rejects_continued_classical_acceptance_dependency():
    result = assess_authority_envelope(
        envelope(
            declared_requirement=MigrationRequirement.PQ_REQUIRED,
            classical_required_for_acceptance=True,
            pq_required_for_acceptance=True,
        ),
        policy(minimum_requirement=MigrationRequirement.PQ_REQUIRED),
    )
    assert result.accepted is False
    assert any("continued classical acceptance dependency" in blocker for blocker in result.blockers)


def test_algorithm_family_confusion_is_fail_closed():
    result = assess_authority_envelope(
        envelope(pq_algorithm_id="ECDSA"),
        policy(),
    )
    assert result.accepted is False
    assert result.verdict == "ALGORITHM_CONFUSION_REJECTED"


def test_not_finalized_pq_signature_is_not_promoted():
    result = assess_authority_envelope(
        envelope(pq_algorithm_id="FN-DSA"),
        policy(),
    )
    assert result.accepted is False
    assert any("finalized-FIPS" in blocker for blocker in result.blockers)


def test_envelope_version_rollback_is_rejected():
    result = assess_authority_envelope(
        envelope(envelope_version=1),
        policy(minimum_envelope_version=2),
    )
    assert result.accepted is False
    assert result.verdict == "VERSION_OR_EPOCH_ROLLBACK_REJECTED"


def test_key_epoch_rollback_is_rejected():
    result = assess_authority_envelope(
        envelope(key_epoch=6),
        policy(minimum_key_epoch=7),
    )
    assert result.accepted is False
    assert result.verdict == "VERSION_OR_EPOCH_ROLLBACK_REJECTED"


def test_bridge_custody_authority_requires_recovery_evidence():
    result = assess_authority_envelope(
        envelope(
            authority_layer=AuthorityLayer.BRIDGE_CUSTODY,
            authority_id="bridge-fixture-1",
            recovery_evidence_present=False,
        ),
        policy(),
    )
    assert result.accepted is False
    assert result.verdict == "RECOVERY_EVIDENCE_REQUIRED"


def test_governance_authority_with_recovery_can_use_hybrid_transition():
    result = assess_authority_envelope(
        envelope(
            authority_layer=AuthorityLayer.GOVERNANCE_ADMIN,
            authority_id="governance-fixture-1",
            recovery_evidence_present=True,
        ),
        policy(),
    )
    assert result.accepted is True
    assert result.verdict == "HYBRID_AUTHORITY_MIGRATION_ACCEPTED"


def test_envelope_cannot_self_assert_execution_or_live_value_authority():
    result = assess_authority_envelope(
        envelope(execution_authority=True, live_value_authorized=True),
        policy(),
    )
    assert result.accepted is False
    assert "Envelope cannot self-assert execution authority." in result.blockers
    assert "Envelope cannot self-assert live-value authorization." in result.blockers
    assert result.execution_authority is False
    assert result.live_value_authorized is False


def test_pq_accounts_do_not_mask_classical_consensus():
    layers = full_layers(ReadinessLevel.PQ_CAPABLE)
    layers[CriticalLayer.CONSENSUS] = ReadinessLevel.CLASSICAL
    result = assess_system_readiness(layers)
    assert result.verdict == "BLOCKED_BY_CLASSICAL_LAYER"
    assert result.weakest_level == "CLASSICAL"
    assert result.migration_target_reached is False
    assert result.weakest_layers == ("CONSENSUS",)
    assert result.blocking_layers == ("CONSENSUS",)
    assert result.whole_chain_pq_security_established is False


def test_unresolved_bridge_layer_blocks_whole_system_pq_migration_readiness():
    layers = full_layers(ReadinessLevel.PQ_CAPABLE)
    layers[CriticalLayer.BRIDGES_CUSTODY_ADMIN] = ReadinessLevel.HYBRID
    result = assess_system_readiness(layers)
    assert result.verdict == "HYBRID_MIGRATION_READY"
    assert result.migration_target_reached is False
    assert result.weakest_layers == ("BRIDGES_CUSTODY_ADMIN",)
    assert result.blocking_layers == ("BRIDGES_CUSTODY_ADMIN",)


def test_all_critical_layers_at_pq_capable_floor_yield_bounded_migration_readiness_only():
    result = assess_system_readiness(full_layers(ReadinessLevel.PQ_CAPABLE))
    assert result.verdict == "PQ_MIGRATION_READY"
    assert result.weakest_level == "PQ_CAPABLE"
    assert result.migration_target_reached is True
    assert set(result.weakest_layers) == {layer.value for layer in CriticalLayer}
    assert result.blocking_layers == ()
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.whole_chain_pq_security_established is False


def test_missing_critical_layer_evidence_fails_closed():
    layers = full_layers(ReadinessLevel.PQ_CAPABLE)
    del layers[CriticalLayer.RECOVERY]
    result = assess_system_readiness(layers)
    assert result.verdict == "BLOCKED_INCOMPLETE_LAYER_EVIDENCE"
    assert result.migration_target_reached is False
    assert result.weakest_layers == ()
    assert result.blocking_layers == ("RECOVERY",)
