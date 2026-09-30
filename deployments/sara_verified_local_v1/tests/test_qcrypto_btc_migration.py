import hashlib

import pytest
from pydantic import ValidationError

from worldshepherd_sara.qcrypto_btc_migration import (
    BitcoinExposureClass,
    BitcoinKeyExposureRecord,
    BitcoinMigrationPlan,
    BitcoinOutputType,
    MigrationGateEvidence,
    MigrationPriority,
    TransitionState,
    classify_bitcoin_quantum_exposure,
    record_digest_sha256,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_p2tr_requires_explicit_public_key_observation_flag():
    with pytest.raises(ValidationError):
        BitcoinKeyExposureRecord(
            record_id="btc:p2tr:1",
            network="mainnet",
            output_type=BitcoinOutputType.P2TR,
            is_unspent=True,
            public_key_observed_on_chain=False,
        )


@pytest.mark.parametrize(
    "output_type",
    [BitcoinOutputType.P2PK, BitcoinOutputType.P2TR, BitcoinOutputType.BARE_MULTISIG],
)
def test_inherently_exposed_unspent_outputs_are_p0(output_type):
    record = BitcoinKeyExposureRecord(
        record_id=f"btc:{output_type.value}:1",
        network="mainnet",
        output_type=output_type,
        is_unspent=True,
        public_key_observed_on_chain=True,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert assessment.exposure_class == BitcoinExposureClass.PUBLIC_KEY_ON_CHAIN
    assert assessment.migration_priority == MigrationPriority.P0_EXPOSED_UNSPENT
    assert assessment.quantum_capability_assumption == "NO_CRQC_ASSUMED_PRESENT"


@pytest.mark.parametrize(
    "output_type",
    [BitcoinOutputType.P2PKH, BitcoinOutputType.P2WPKH],
)
def test_hash_committed_unspent_outputs_are_distinct_from_exposed_keys(output_type):
    record = BitcoinKeyExposureRecord(
        record_id=f"btc:{output_type.value}:1",
        network="mainnet",
        output_type=output_type,
        is_unspent=True,
        public_key_observed_on_chain=False,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert (
        assessment.exposure_class
        == BitcoinExposureClass.HASH_COMMITTED_KEY_NOT_OBSERVED
    )
    assert (
        assessment.migration_priority
        == MigrationPriority.P1_HASH_OR_SCRIPT_COMMITTED_UNSPENT
    )


@pytest.mark.parametrize(
    "output_type",
    [BitcoinOutputType.P2SH, BitcoinOutputType.P2WSH],
)
def test_script_hash_only_unspent_outputs_remain_structurally_unknown(output_type):
    record = BitcoinKeyExposureRecord(
        record_id=f"btc:{output_type.value}:1",
        network="mainnet",
        output_type=output_type,
        is_unspent=True,
        public_key_observed_on_chain=False,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert assessment.exposure_class == BitcoinExposureClass.SCRIPT_HASH_NOT_OBSERVED
    assert "SCRIPT_HASH_ONLY" in assessment.reason_codes


def test_explicit_chain_observation_overrides_hash_output_shape():
    record = BitcoinKeyExposureRecord(
        record_id="btc:p2wpkh:reused",
        network="mainnet",
        output_type=BitcoinOutputType.P2WPKH,
        is_unspent=True,
        public_key_observed_on_chain=True,
        address_or_key_reused=True,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert assessment.exposure_class == BitcoinExposureClass.PUBLIC_KEY_ON_CHAIN
    assert assessment.migration_priority == MigrationPriority.P0_EXPOSED_UNSPENT


def test_spent_revealed_key_without_known_reuse_is_not_called_unspent_exposure():
    record = BitcoinKeyExposureRecord(
        record_id="btc:p2wpkh:spent",
        network="mainnet",
        output_type=BitcoinOutputType.P2WPKH,
        is_unspent=False,
        public_key_observed_on_chain=True,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert (
        assessment.exposure_class
        == BitcoinExposureClass.SPENT_OUTPUT_KEY_EXPOSURE_RELEVANT_ONLY_IF_REUSED
    )
    assert assessment.migration_priority == MigrationPriority.P2_REUSE_REVIEW


def test_reused_revealed_key_with_other_unspent_outputs_is_p0():
    record = BitcoinKeyExposureRecord(
        record_id="btc:p2pkh:reuse",
        network="mainnet",
        output_type=BitcoinOutputType.P2PKH,
        is_unspent=False,
        public_key_observed_on_chain=True,
        address_or_key_reused=True,
        same_key_controls_other_unspent_outputs=True,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert assessment.migration_priority == MigrationPriority.P0_EXPOSED_UNSPENT
    assert "SAME_KEY_CONTROLS_OTHER_UNSPENT_OUTPUTS" in assessment.reason_codes


def test_reused_unspent_semantics_fail_closed_when_reuse_flag_is_missing():
    with pytest.raises(ValidationError):
        BitcoinKeyExposureRecord(
            record_id="btc:bad-reuse",
            network="mainnet",
            output_type=BitcoinOutputType.P2PKH,
            is_unspent=False,
            public_key_observed_on_chain=True,
            same_key_controls_other_unspent_outputs=True,
            address_or_key_reused=False,
        )


def test_unknown_output_type_fails_to_review_required():
    record = BitcoinKeyExposureRecord(
        record_id="btc:unknown",
        network="mainnet",
        output_type=BitcoinOutputType.UNKNOWN,
        is_unspent=True,
        public_key_observed_on_chain=False,
    )
    assessment = classify_bitcoin_quantum_exposure(record)
    assert assessment.exposure_class == BitcoinExposureClass.INDETERMINATE
    assert assessment.migration_priority == MigrationPriority.REVIEW_REQUIRED


def test_digest_is_stable_and_mutation_sensitive():
    original = BitcoinKeyExposureRecord(
        record_id="btc:digest",
        network="mainnet",
        output_type=BitcoinOutputType.P2WPKH,
        is_unspent=True,
        public_key_observed_on_chain=False,
        evidence_refs=["chain:fixture:1"],
    )
    same = original.model_copy(deep=True)
    mutated = original.model_copy(update={"address_or_key_reused": True})
    assert record_digest_sha256(original) == record_digest_sha256(same)
    assert record_digest_sha256(original) != record_digest_sha256(mutated)


def test_plan_approval_is_required_beyond_inventory():
    with pytest.raises(ValidationError):
        BitcoinMigrationPlan(
            plan_id="plan:1",
            current_state=TransitionState.PLAN_APPROVED,
        )


def test_hybrid_tested_requires_test_evidence():
    with pytest.raises(ValidationError):
        BitcoinMigrationPlan(
            plan_id="plan:2",
            current_state=TransitionState.HYBRID_TESTED,
            human_approval_id="approval:1",
        )


def test_migration_ready_requires_test_and_rollback_drill():
    test_evidence = MigrationGateEvidence(
        evidence_id="test:1",
        evidence_type="TEST",
        passed=True,
        digest_sha256=_digest("test"),
    )
    with pytest.raises(ValidationError):
        BitcoinMigrationPlan(
            plan_id="plan:3",
            current_state=TransitionState.MIGRATION_READY,
            human_approval_id="approval:1",
            evidence=[test_evidence],
        )


def test_legacy_sunset_requires_external_validation():
    evidence = [
        MigrationGateEvidence(
            evidence_id="test:1",
            evidence_type="TEST",
            passed=True,
            digest_sha256=_digest("test"),
        ),
        MigrationGateEvidence(
            evidence_id="rollback:1",
            evidence_type="ROLLBACK_DRILL",
            passed=True,
            digest_sha256=_digest("rollback"),
        ),
    ]
    with pytest.raises(ValidationError):
        BitcoinMigrationPlan(
            plan_id="plan:4",
            current_state=TransitionState.LEGACY_SUNSET_ELIGIBLE,
            human_approval_id="approval:1",
            target_output_type="FUTURE_PQ_OUTPUT_TYPE",
            evidence=evidence,
        )


def test_legacy_sunset_accepts_full_gate_evidence():
    evidence = [
        MigrationGateEvidence(
            evidence_id="test:1",
            evidence_type="TEST",
            passed=True,
            digest_sha256=_digest("test"),
        ),
        MigrationGateEvidence(
            evidence_id="rollback:1",
            evidence_type="ROLLBACK_DRILL",
            passed=True,
            digest_sha256=_digest("rollback"),
        ),
        MigrationGateEvidence(
            evidence_id="external:1",
            evidence_type="EXTERNAL_VALIDATION",
            passed=True,
            digest_sha256=_digest("external"),
        ),
    ]
    plan = BitcoinMigrationPlan(
        plan_id="plan:5",
        current_state=TransitionState.LEGACY_SUNSET_ELIGIBLE,
        human_approval_id="approval:1",
        target_output_type="FUTURE_PQ_OUTPUT_TYPE",
        legacy_signatures_disabled=True,
        evidence=evidence,
    )
    assert plan.current_state == TransitionState.LEGACY_SUNSET_ELIGIBLE
