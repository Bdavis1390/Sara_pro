"""Read-only contract for evidence-driven UC06-P1 maturity reduction."""

from fastapi import APIRouter

from .em_maturity_reducer import MATURITY_REDUCER_VERSION
from .em_sealed_receipts import SEALED_RECEIPT_SCHEMA_VERSION


router = APIRouter(prefix="/v1/em/uc06/maturity", tags=["em-maturity-reducer"])


@router.get("/reducer-contract")
def maturity_reducer_contract() -> dict[str, object]:
    return {
        "reducer_version": MATURITY_REDUCER_VERSION,
        "sealed_receipt_schema_version": SEALED_RECEIPT_SCHEMA_VERSION,
        "read_only": True,
        "persisted_state_mutation": False,
        "hardware_actions": False,
        "verified_source_bytes_required": True,
        "currently_reducible_evidence": [
            "D5_DIAGNOSTIC",
            "POWER_RECOVERY",
        ],
        "evidence_that_remains_separate": [
            "FROZEN_MEDIUM_FINE_CONVERGENCE",
            "FROZEN_ENERGY_CLOSURE",
            "PHYSICAL_VNA_VALIDATION",
            "REPEATABILITY_AND_UNCERTAINTY_VALIDATION",
            "VALIDATED_OPERATING_ENVELOPE",
            "PRIME_HARDWARE_RELEASE",
        ],
        "claims_boundary": [
            "HASH_VERIFICATION_IS_INTEGRITY_NOT_PHYSICS_VALIDATION",
            "D5_INGESTION_IS_DIAGNOSTIC_ONLY",
            "RECOVERY_EXECUTION_COMPLETE_IS_NOT_CONVERGENCE",
            "NO_H2_PROMOTION",
            "NO_FULL_CAMPAIGN_AUTHORIZATION",
            "NO_HARDWARE_ACTION",
        ],
    }
