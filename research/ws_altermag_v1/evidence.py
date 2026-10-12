from __future__ import annotations

from .schema import EvidenceDecision, InferenceResult


CANONICAL_PHYSICAL_PROMOTIONS = {
    "EXPERIMENTALLY VALIDATED",
    "LAB VALIDATED",
    "DEVICE QUALIFIED",
    "PRODUCTION READY",
}


def decide(
    *,
    inference: InferenceResult,
    hypothesis_decisive: bool,
    execution_mode: str,
    test_passed: bool,
) -> EvidenceDecision:
    allowed: list[str] = []
    blocked = sorted(CANONICAL_PHYSICAL_PROMOTIONS)

    if test_passed:
        allowed.append("IMPLEMENTED IN SOFTWARE")

    if (
        execution_mode == "synthetic"
        and test_passed
        and inference.identifiable
        and hypothesis_decisive
    ):
        # Bounded strictly to the tested synthetic software invariant.
        allowed.append("PROVEN INTERNALLY")

    allowed.extend(
        [
            "SUPPORTED BY LITERATURE",
            "SIMULATED ONLY",
            "REQUIRES LAB VALIDATION",
        ]
    )

    next_gate = (
        "Replace the analytic synthetic forward model with a versioned CrSb "
        "reference-data adapter and reproduce B000 against published observables."
    )

    return EvidenceDecision(
        allowed_claims=tuple(dict.fromkeys(allowed)),
        blocked_promotions=tuple(blocked),
        next_gate=next_gate,
    )
