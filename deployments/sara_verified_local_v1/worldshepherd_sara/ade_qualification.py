from __future__ import annotations

from typing import Any

from .ade import discover_expression
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_discovery(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    search = fixture["search"]
    result = discover_expression(
        fixture["problem"]["samples"],
        constants=tuple(int(value) for value in search["constants"]),
        max_depth=int(search["max_depth"]),
        beam_width=int(search["beam_width"]),
    )
    expected = fixture["expected"]
    improved = result.mse < result.baseline_mse
    passed = (
        result.mse <= float(expected["mse_max"])
        and result.human_interpretable is bool(expected["human_interpretable"])
        and (improved if expected["must_improve_over_baseline"] else True)
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-4001",
        requirement_id=requirement.requirement_delta_id,
        test_id="ade_symbolic_discovery_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest(fixture["search"]),
        inputs=[{"samples": fixture["problem"]["samples"]}],
        outputs=[
            {
                "expression": result.expression.text(),
                "mse": result.mse,
                "baseline_mse": result.baseline_mse,
                "improvement_ratio": result.improvement_ratio,
                "human_interpretable": result.human_interpretable,
                "evaluated_candidates": result.evaluated_candidates,
            }
        ],
        metrics=[
            {"name": "mse", "value": result.mse, "target_max": expected["mse_max"]},
            {"name": "baseline_mse", "value": result.baseline_mse},
            {"name": "improved_over_baseline", "value": improved},
            {"name": "human_interpretable", "value": result.human_interpretable},
            {"name": "evaluated_candidates", "value": result.evaluated_candidates},
        ],
        uncertainty=[
            {
                "name": "generalization_to_real_engineering_discovery",
                "state": "NOT_EVALUATED",
            },
            {
                "name": "state_of_the_art_comparison",
                "state": "NOT_EVALUATED",
            },
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Bounded symbolic search discovered an interpretable zero-error rule that improved over the frozen baseline"
            if passed
            else "Bounded symbolic search did not satisfy the frozen synthetic discovery target"
        ),
        negative_evidence=[] if passed else [{"observed_mse": result.mse, "baseline_mse": result.baseline_mse}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic interpretable algorithm-discovery evidence only; no SOTA, novelty, scientific-discovery, or DARPA SPEED DIAL D2P2 eligibility claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
