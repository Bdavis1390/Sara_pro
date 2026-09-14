from __future__ import annotations

import argparse
import json
from typing import Any

from pydantic import ValidationError

from .programmable_boundary_benchmark import run_programmable_boundary_benchmark
from .qualification import EvidenceScope
from .sovereign_boundary_kernel import (
    BoundaryContext,
    BoundaryDisposition,
    BoundaryEnvironment,
    BoundaryPolicyDecision,
    BoundaryProvenance,
    ExecutionResultStatus,
    build_programmable_boundary_simulation_action,
    create_boundary_envelope,
    record_execution,
    verify_boundary_envelope,
)


def run_demo(*, scenario_id: str = "coherent_target") -> dict[str, Any]:
    report = run_programmable_boundary_benchmark()
    action = build_programmable_boundary_simulation_action(
        report,
        scenario_id=scenario_id,
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(
            environment=BoundaryEnvironment.SIMULATION,
            mission_id="WS-SBK-DEMO",
            network_state="LOCAL",
        ),
        provenance=BoundaryProvenance(
            agent_version="ws-sovereign-boundary-kernel-v0.1",
            source_evidence_refs=(report.qualification_id,),
        ),
        policy=BoundaryPolicyDecision(
            disposition=BoundaryDisposition.ALLOW,
            policy_revision="WS-SBK-DEMO-POLICY-0.1",
            decided_by="LOCAL_DEMO_PDP",
            human_approval_required=False,
            reasons=(
                "Synthetic benchmark is limited to SIMULATION effect scope.",
            ),
        ),
        envelope_id="WS-SBK-DEMO-ENVELOPE-001",
    )
    completed = record_execution(
        envelope,
        runtime_action=action,
        status=ExecutionResultStatus.SUCCEEDED,
        outcome_ref=f"benchmark:{report.report_digest}",
        evidence_refs=(report.qualification_id,),
    )

    physical_promotion_blocked = False
    physical_promotion_error = None
    promoted = action.model_copy(update={"effect_scope": EvidenceScope.PHYSICAL})
    try:
        create_boundary_envelope(
            actor="SSPADAWANZZ",
            action=promoted,
            context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
            provenance=BoundaryProvenance(
                agent_version="ws-sovereign-boundary-kernel-v0.1",
                source_evidence_refs=(report.qualification_id,),
            ),
            policy=BoundaryPolicyDecision(
                disposition=BoundaryDisposition.ALLOW,
                policy_revision="WS-SBK-DEMO-POLICY-0.1",
                decided_by="LOCAL_DEMO_PDP",
                human_approval_required=True,
            ),
        )
    except ValidationError as exc:
        physical_promotion_blocked = True
        physical_promotion_error = str(exc.errors()[0].get("msg", "validation error"))

    return {
        "demo": "Worldshepherd Sovereign Boundary Kernel v0.1",
        "benchmark_qualification_id": report.qualification_id,
        "benchmark_report_digest": report.report_digest,
        "benchmark_capability_status": report.capability_status.value,
        "scenario_id": scenario_id,
        "action_digest": completed.action_digest,
        "envelope_digest": completed.envelope_digest,
        "terminal_state": completed.state.value,
        "envelope_verified": verify_boundary_envelope(completed),
        "physical_promotion_blocked": physical_promotion_blocked,
        "physical_promotion_error": physical_promotion_error,
        "claims_boundary": list(completed.claims_boundary),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the non-operational Sovereign Boundary Kernel proof: bind a "
            "SIMULATED_ONLY programmable-boundary scenario to a policy envelope, "
            "record its execution, and prove physical claim promotion fails closed."
        )
    )
    parser.add_argument(
        "--scenario",
        default="coherent_target",
        choices=(
            "passive_reference",
            "random_open_loop",
            "coherent_target",
            "null_target",
            "thermal_drift",
        ),
    )
    args = parser.parse_args()
    print(json.dumps(run_demo(scenario_id=args.scenario), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
