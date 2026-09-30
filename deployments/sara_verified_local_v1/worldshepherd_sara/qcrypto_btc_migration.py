from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


QCRYPTO_BTC_SCHEMA = "WS-QCRYPTO-BTC-MIGRATION-V0.1"
QCRYPTO_BTC_DOMAIN = b"WS-QCRYPTO-BTC-MIGRATION-V0.1\x00"


class BitcoinOutputType(str, Enum):
    P2PK = "P2PK"
    P2PKH = "P2PKH"
    P2SH = "P2SH"
    P2WPKH = "P2WPKH"
    P2WSH = "P2WSH"
    P2TR = "P2TR"
    BARE_MULTISIG = "BARE_MULTISIG"
    UNKNOWN = "UNKNOWN"


class BitcoinExposureClass(str, Enum):
    PUBLIC_KEY_ON_CHAIN = "PUBLIC_KEY_ON_CHAIN"
    HASH_COMMITTED_KEY_NOT_OBSERVED = "HASH_COMMITTED_KEY_NOT_OBSERVED"
    SCRIPT_HASH_NOT_OBSERVED = "SCRIPT_HASH_NOT_OBSERVED"
    SPENT_OUTPUT_KEY_EXPOSURE_RELEVANT_ONLY_IF_REUSED = (
        "SPENT_OUTPUT_KEY_EXPOSURE_RELEVANT_ONLY_IF_REUSED"
    )
    INDETERMINATE = "INDETERMINATE"


class MigrationPriority(str, Enum):
    P0_EXPOSED_UNSPENT = "P0_EXPOSED_UNSPENT"
    P1_HASH_OR_SCRIPT_COMMITTED_UNSPENT = "P1_HASH_OR_SCRIPT_COMMITTED_UNSPENT"
    P2_REUSE_REVIEW = "P2_REUSE_REVIEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class TransitionState(str, Enum):
    INVENTORIED = "INVENTORIED"
    PLAN_APPROVED = "PLAN_APPROVED"
    HYBRID_TESTED = "HYBRID_TESTED"
    MIGRATION_READY = "MIGRATION_READY"
    MIGRATED = "MIGRATED"
    LEGACY_SUNSET_ELIGIBLE = "LEGACY_SUNSET_ELIGIBLE"


class BitcoinKeyExposureRecord(BaseModel):
    """Evidence-bounded Bitcoin key/output exposure record.

    This model does not infer that a cryptographically relevant quantum computer
    exists. It only classifies whether public-key material is already observable
    on chain and whether unspent value remains attached to the record.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[QCRYPTO_BTC_SCHEMA] = QCRYPTO_BTC_SCHEMA
    record_id: str = Field(min_length=1, max_length=160)
    network: Literal["mainnet", "testnet", "signet", "regtest"]
    output_type: BitcoinOutputType
    is_unspent: bool
    public_key_observed_on_chain: bool = False
    same_key_controls_other_unspent_outputs: bool = False
    address_or_key_reused: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_semantics(self) -> "BitcoinKeyExposureRecord":
        inherently_exposed = {
            BitcoinOutputType.P2PK,
            BitcoinOutputType.P2TR,
            BitcoinOutputType.BARE_MULTISIG,
        }
        if self.output_type in inherently_exposed and not self.public_key_observed_on_chain:
            raise ValueError(
                f"{self.output_type.value} exposes public-key material in the output; "
                "public_key_observed_on_chain must be true"
            )
        if self.same_key_controls_other_unspent_outputs and not self.address_or_key_reused:
            raise ValueError(
                "same_key_controls_other_unspent_outputs requires address_or_key_reused"
            )
        return self


class BitcoinQuantumExposureAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[QCRYPTO_BTC_SCHEMA] = QCRYPTO_BTC_SCHEMA
    record_id: str
    exposure_class: BitcoinExposureClass
    migration_priority: MigrationPriority
    reason_codes: list[str]
    recommended_action: str
    quantum_capability_assumption: Literal[
        "NO_CRQC_ASSUMED_PRESENT"
    ] = "NO_CRQC_ASSUMED_PRESENT"
    claims_boundary: str = (
        "Exposure classification only; no claim that a cryptographically relevant "
        "quantum computer exists or that theft is imminent."
    )


class MigrationGateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=160)
    evidence_type: Literal[
        "TEST",
        "REVIEW",
        "EXTERNAL_VALIDATION",
        "HUMAN_APPROVAL",
        "ROLLBACK_DRILL",
        "INTEROP_FIXTURE",
    ]
    passed: bool
    digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BitcoinMigrationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[QCRYPTO_BTC_SCHEMA] = QCRYPTO_BTC_SCHEMA
    plan_id: str = Field(min_length=1, max_length=160)
    current_state: TransitionState = TransitionState.INVENTORIED
    target_output_type: str | None = Field(default=None, max_length=128)
    legacy_signatures_disabled: bool = False
    human_approval_id: str | None = Field(default=None, max_length=160)
    evidence: list[MigrationGateEvidence] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validate_state_claim(self) -> "BitcoinMigrationPlan":
        if self.current_state == TransitionState.INVENTORIED:
            return self
        if not self.human_approval_id:
            raise ValueError("states beyond INVENTORIED require human approval")
        if self.current_state in {
            TransitionState.HYBRID_TESTED,
            TransitionState.MIGRATION_READY,
            TransitionState.MIGRATED,
            TransitionState.LEGACY_SUNSET_ELIGIBLE,
        } and not _has_passed(self.evidence, "TEST"):
            raise ValueError(f"{self.current_state.value} requires passing TEST evidence")
        if self.current_state in {
            TransitionState.MIGRATION_READY,
            TransitionState.MIGRATED,
            TransitionState.LEGACY_SUNSET_ELIGIBLE,
        } and not _has_passed(self.evidence, "ROLLBACK_DRILL"):
            raise ValueError(
                f"{self.current_state.value} requires passing ROLLBACK_DRILL evidence"
            )
        if self.current_state in {
            TransitionState.MIGRATED,
            TransitionState.LEGACY_SUNSET_ELIGIBLE,
        } and not self.target_output_type:
            raise ValueError(f"{self.current_state.value} requires target_output_type")
        if (
            self.current_state == TransitionState.LEGACY_SUNSET_ELIGIBLE
            and not _has_passed(self.evidence, "EXTERNAL_VALIDATION")
        ):
            raise ValueError(
                "LEGACY_SUNSET_ELIGIBLE requires passing EXTERNAL_VALIDATION evidence"
            )
        if self.legacy_signatures_disabled and (
            self.current_state != TransitionState.LEGACY_SUNSET_ELIGIBLE
        ):
            raise ValueError(
                "legacy signatures may be disabled only at LEGACY_SUNSET_ELIGIBLE"
            )
        return self


def _has_passed(evidence: list[MigrationGateEvidence], evidence_type: str) -> bool:
    return any(item.evidence_type == evidence_type and item.passed for item in evidence)


def classify_bitcoin_quantum_exposure(
    record: BitcoinKeyExposureRecord,
) -> BitcoinQuantumExposureAssessment:
    """Classify on-chain key visibility without predicting quantum capability."""

    if record.public_key_observed_on_chain:
        if record.is_unspent:
            return BitcoinQuantumExposureAssessment(
                record_id=record.record_id,
                exposure_class=BitcoinExposureClass.PUBLIC_KEY_ON_CHAIN,
                migration_priority=MigrationPriority.P0_EXPOSED_UNSPENT,
                reason_codes=["PUBLIC_KEY_OBSERVED", "UNSPENT_VALUE"],
                recommended_action=(
                    "Prioritize migration planning for this key/output cohort once a "
                    "reviewed Bitcoin-compatible post-quantum path exists."
                ),
            )
        if record.same_key_controls_other_unspent_outputs:
            return BitcoinQuantumExposureAssessment(
                record_id=record.record_id,
                exposure_class=BitcoinExposureClass.PUBLIC_KEY_ON_CHAIN,
                migration_priority=MigrationPriority.P0_EXPOSED_UNSPENT,
                reason_codes=[
                    "PUBLIC_KEY_OBSERVED",
                    "SPENT_OUTPUT",
                    "SAME_KEY_CONTROLS_OTHER_UNSPENT_OUTPUTS",
                ],
                recommended_action=(
                    "Treat the reused key as exposed and prioritize the remaining "
                    "unspent outputs for migration planning."
                ),
            )
        return BitcoinQuantumExposureAssessment(
            record_id=record.record_id,
            exposure_class=(
                BitcoinExposureClass.SPENT_OUTPUT_KEY_EXPOSURE_RELEVANT_ONLY_IF_REUSED
            ),
            migration_priority=MigrationPriority.P2_REUSE_REVIEW,
            reason_codes=["PUBLIC_KEY_OBSERVED", "OUTPUT_SPENT"],
            recommended_action=(
                "Check for key/address reuse before assigning custody migration work."
            ),
        )

    if record.output_type in {
        BitcoinOutputType.P2PKH,
        BitcoinOutputType.P2WPKH,
    }:
        if record.is_unspent:
            return BitcoinQuantumExposureAssessment(
                record_id=record.record_id,
                exposure_class=BitcoinExposureClass.HASH_COMMITTED_KEY_NOT_OBSERVED,
                migration_priority=MigrationPriority.P1_HASH_OR_SCRIPT_COMMITTED_UNSPENT,
                reason_codes=[
                    "HASH_COMMITMENT_ONLY",
                    "PUBLIC_KEY_NOT_OBSERVED",
                    "UNSPENT_VALUE",
                ],
                recommended_action=(
                    "Inventory and preserve key custody; do not treat the hash "
                    "commitment as a permanent post-quantum solution."
                ),
            )
        return BitcoinQuantumExposureAssessment(
            record_id=record.record_id,
            exposure_class=BitcoinExposureClass.INDETERMINATE,
            migration_priority=MigrationPriority.P2_REUSE_REVIEW,
            reason_codes=["OUTPUT_SPENT", "PUBLIC_KEY_NOT_RECORDED_IN_THIS_EVIDENCE"],
            recommended_action=(
                "Reconcile spend data and reuse history before assigning migration priority."
            ),
        )

    if record.output_type in {BitcoinOutputType.P2SH, BitcoinOutputType.P2WSH}:
        if record.is_unspent:
            return BitcoinQuantumExposureAssessment(
                record_id=record.record_id,
                exposure_class=BitcoinExposureClass.SCRIPT_HASH_NOT_OBSERVED,
                migration_priority=MigrationPriority.P1_HASH_OR_SCRIPT_COMMITTED_UNSPENT,
                reason_codes=[
                    "SCRIPT_HASH_ONLY",
                    "PUBLIC_KEY_NOT_OBSERVED",
                    "UNSPENT_VALUE",
                ],
                recommended_action=(
                    "Inventory redeem/witness-script custody and migration dependencies; "
                    "the script hash alone does not establish the key structure."
                ),
            )
        return BitcoinQuantumExposureAssessment(
            record_id=record.record_id,
            exposure_class=BitcoinExposureClass.INDETERMINATE,
            migration_priority=MigrationPriority.P2_REUSE_REVIEW,
            reason_codes=["OUTPUT_SPENT", "SCRIPT_STRUCTURE_NOT_RECONCILED"],
            recommended_action=(
                "Reconcile revealed script/key data and reuse history before migration."
            ),
        )

    return BitcoinQuantumExposureAssessment(
        record_id=record.record_id,
        exposure_class=BitcoinExposureClass.INDETERMINATE,
        migration_priority=MigrationPriority.REVIEW_REQUIRED,
        reason_codes=["INSUFFICIENT_OR_UNKNOWN_OUTPUT_EVIDENCE"],
        recommended_action="Require additional chain/script evidence; fail closed on priority.",
    )


def canonical_record_bytes(record: BitcoinKeyExposureRecord) -> bytes:
    payload = record.model_dump(mode="json")
    return QCRYPTO_BTC_DOMAIN + json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def record_digest_sha256(record: BitcoinKeyExposureRecord) -> str:
    return hashlib.sha256(canonical_record_bytes(record)).hexdigest()
