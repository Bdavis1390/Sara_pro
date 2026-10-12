"""Read-only exposure of the frozen UC06-P1 D6-E convergence contract."""

from fastapi import APIRouter

from .em_convergence import (
    COMPLEX_S11_THRESHOLD,
    D6E_CONTRACT_ID,
    ENERGY_CLOSURE_THRESHOLD,
    EXPECTED_ANCHORS,
    EXPECTED_MEDIUM_FINE_PAIRS,
    RESONANCE_SHIFT_FRACTION_THRESHOLD,
)


router = APIRouter(prefix="/v1/em/uc06/convergence", tags=["em-convergence"])


@router.get("/contract")
def convergence_contract() -> dict[str, object]:
    return {
        "analysis_contract_id": D6E_CONTRACT_ID,
        "read_only": True,
        "current_result_ingested": False,
        "overall_convergence": "NOT_ADJUDICATED",
        "expected_anchor_count": EXPECTED_ANCHORS,
        "expected_medium_fine_pair_count": EXPECTED_MEDIUM_FINE_PAIRS,
        "frozen_thresholds": {
            "complex_s11_max_delta": COMPLEX_S11_THRESHOLD,
            "resonance_shift_fraction": RESONANCE_SHIFT_FRACTION_THRESHOLD,
            "resonance_shift_percent": 100.0 * RESONANCE_SHIFT_FRACTION_THRESHOLD,
            "energy_closure_fraction": ENERGY_CLOSURE_THRESHOLD,
        },
        "rules": [
            "ALL_54_ANCHORS_REQUIRE_ZERO_EXIT_PARSEABLE_RETAINED_OUTPUT",
            "FAILURES_MUST_REMAIN_VISIBLE",
            "NO_UNREGISTERED_RETRIES",
            "18_MEDIUM_FINE_COMPLEX_S11_PAIRS_REQUIRED",
            "BOUNDARY_RESONANCE_IS_NOT_EVALUABLE",
            "MISSING_ENERGY_CLOSURE_IS_NOT_EVALUABLE",
            "NO_THRESHOLD_RELAXATION",
        ],
        "claims_boundary": [
            "CONTRACT_ONLY_NO_CURRENT_FINE_RESULT_VALUES",
            "NOT_ADJUDICATED_IS_NOT_PASS_OR_FAIL",
            "SOFTWARE_CI_IS_NOT_CONVERGENCE_EVIDENCE",
            "NO_HARDWARE_AUTHORITY",
        ],
    }
