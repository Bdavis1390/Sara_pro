"""UC06-P1 A027-A054 power-recovery evidence contract.

Execution recovery is intentionally separate from scientific convergence.  A complete
recovery receipt can establish 54-anchor execution coverage but never upgrades the
frozen convergence, energy, laboratory, or hardware-validation gates by itself.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator


RECOVERY_CONTRACT_VERSION = "worldshepherd.uc06-p1.recovery.v0.1"
P1_PREREG_ID = "r2r-a-r1-p1-20260928T173032Z"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RecoveryStatus(str, Enum):
    NOT_INGESTED = "NOT_INGESTED"
    INCOMPLETE = "INCOMPLETE"
    FAIL = "FAIL"
    EXECUTION_COMPLETE = "EXECUTION_COMPLETE"


class RecoveryReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[RECOVERY_CONTRACT_VERSION] = RECOVERY_CONTRACT_VERSION
    preregistration_id: Literal[P1_PREREG_ID] = P1_PREREG_ID
    source_receipt: str = Field(min_length=1, max_length=512)
    source_receipt_sha256: str
    segment: Literal["A027-A054"] = "A027-A054"
    planned_job_count: Literal[28] = 28
    completed_job_count: int = Field(ge=0, le=28)
    exit_zero_count: int = Field(ge=0, le=28)
    nonzero_exit_count: int = Field(ge=0, le=28)
    durable_checkpoint_count: int = Field(ge=0, le=28)
    replacement_a027_fresh_output: bool
    original_a027_partial_output_reused: Literal[False] = False
    automatic_retry_count: Literal[0] = 0
    direct_mpi_binary_topology: bool
    mpi_stdin_none: bool
    palace_stdin_dev_null: bool
    sleep_inhibitor_used: bool
    scientific_gate_change: Literal[False] = False

    @model_validator(mode="after")
    def validate_counts_and_hash(self) -> "RecoveryReceipt":
        if not _SHA256_RE.fullmatch(self.source_receipt_sha256):
            raise ValueError("source_receipt_sha256 must be lowercase SHA-256 hex")
        if self.exit_zero_count + self.nonzero_exit_count != self.completed_job_count:
            raise ValueError("zero + nonzero exits must equal completed_job_count")
        if self.durable_checkpoint_count > self.completed_job_count:
            raise ValueError("durable checkpoints cannot exceed completed jobs")
        return self


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RecoveryStatus
    combined_anchor_coverage: int = Field(ge=26, le=54)
    scientific_convergence: Literal["NOT_ADJUDICATED"] = "NOT_ADJUDICATED"
    hardware_action_authorized: Literal[False] = False
    unresolved_protocol_requirements: list[str]
    rationale_codes: list[str]


def evaluate_recovery_receipt(receipt: RecoveryReceipt) -> RecoveryDecision:
    """Evaluate preregistered execution recovery without making a physics claim."""

    combined = 26 + receipt.completed_job_count
    unresolved: list[str] = []

    if not receipt.replacement_a027_fresh_output:
        unresolved.append("FRESH_A027_REPLACEMENT")
    if not receipt.direct_mpi_binary_topology:
        unresolved.append("DIRECT_MPI_BINARY_TOPOLOGY")
    if not receipt.mpi_stdin_none:
        unresolved.append("MPI_STDIN_NONE")
    if not receipt.palace_stdin_dev_null:
        unresolved.append("PALACE_STDIN_DEV_NULL")
    if not receipt.sleep_inhibitor_used:
        unresolved.append("SLEEP_INHIBITOR")
    if receipt.durable_checkpoint_count != receipt.completed_job_count:
        unresolved.append("DURABLE_CHECKPOINT_COVERAGE")

    if receipt.completed_job_count < receipt.planned_job_count:
        status = RecoveryStatus.INCOMPLETE
        unresolved.append("A027_A054_COMPLETION")
    elif receipt.nonzero_exit_count > 0:
        status = RecoveryStatus.FAIL
        unresolved.append("ZERO_EXIT_ALL_RECOVERY_JOBS")
    elif unresolved:
        status = RecoveryStatus.FAIL
    else:
        status = RecoveryStatus.EXECUTION_COMPLETE

    rationale = [
        "POWER_RECOVERY_EXECUTION_ONLY",
        "ORIGINAL_A027_PARTIAL_HAS_NO_SCIENTIFIC_COMPLETION_CREDIT",
        "NO_PARTIAL_OUTPUT_REUSE",
        "NO_AUTOMATIC_RETRY",
        "CONVERGENCE_REMAINS_SEPARATE",
    ]
    if status == RecoveryStatus.EXECUTION_COMPLETE:
        rationale.append("COMBINED_A001_A054_EXECUTION_COVERAGE_ESTABLISHED")
    elif status == RecoveryStatus.INCOMPLETE:
        rationale.append("RECOVERY_SEGMENT_NOT_COMPLETE")
    else:
        rationale.append("RECOVERY_PROTOCOL_OR_EXIT_FAILURE")

    return RecoveryDecision(
        status=status,
        combined_anchor_coverage=combined,
        unresolved_protocol_requirements=sorted(set(unresolved)),
        rationale_codes=rationale,
    )


def current_recovery_status() -> dict[str, object]:
    return {
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "preregistration_id": P1_PREREG_ID,
        "status": RecoveryStatus.NOT_INGESTED.value,
        "sealed_completion_receipt_ingested": False,
        "combined_anchor_coverage_claim": "NOT_ESTABLISHED_IN_REPOSITORY",
        "scientific_convergence": "NOT_ADJUDICATED",
        "hardware_actions": False,
        "claims_boundary": [
            "A001_A026_PREFIX_PREVIOUSLY_ESTABLISHED",
            "A027_ORIGINAL_INTERRUPTED_NO_COMPLETION_CREDIT",
            "A027_A054_COMPLETION_RECEIPT_NOT_INGESTED",
            "RECOVERY_COMPLETION_IS_NOT_CONVERGENCE",
            "NO_HARDWARE_AUTHORITY",
        ],
    }


router = APIRouter(prefix="/v1/em/uc06/recovery", tags=["em-recovery"])


@router.get("/status")
def recovery_status() -> dict[str, object]:
    return current_recovery_status()


@router.get("/contract")
def recovery_contract() -> dict[str, object]:
    return {
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "preregistration_id": P1_PREREG_ID,
        "segment": "A027-A054",
        "planned_job_count": 28,
        "fresh_A027_replacement_required": True,
        "original_A027_partial_reuse_allowed": False,
        "automatic_retries_allowed": 0,
        "direct_mpi_binary_topology_required": True,
        "mpi_stdin_none_required": True,
        "palace_stdin_dev_null_required": True,
        "sleep_inhibitor_required": True,
        "durable_checkpoint_each_completed_job_required": True,
        "read_only": True,
        "hardware_actions": False,
    }
