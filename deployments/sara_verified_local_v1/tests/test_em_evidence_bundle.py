import pytest

from worldshepherd_sara.em_evidence_bundle import (
    EMCandidateEvidenceBundle,
    EMHardwareModelContext,
    EMTransformationStep,
    build_em_candidate_evidence_bundle,
    verify_em_candidate_evidence_bundle,
)
from worldshepherd_sara.em_intelligence import (
    EMCandidate,
    EMEvidenceClass,
    EMIntent,
    EMOperatingMode,
)
from worldshepherd_sara.em_validation import assess_candidate_for_palace


D0 = "sha256:" + "0" * 64
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def _intent() -> EMIntent:
    return EMIntent(
        intent_id="I-BUNDLE",
        objective="Preserve TE observability while expanding TM control",
        operating_mode=EMOperatingMode.DESIGN_EXPLORATION,
    )


def _candidate() -> EMCandidate:
    return EMCandidate(
        candidate_id="C-BUNDLE",
        source_model="pareto-search",
        source_version="v0.1",
        evidence_class=EMEvidenceClass.HYPOTHESIS,
        convergence_status="PENDING_FULL_WAVE_VALIDATION",
        model_discrepancy_status="BOUNDED_FOR_EXPLORATION",
        evidence_refs=["github:research/uc06_p1/D4_SUMMARY.md"],
        hardware_action_authorized=False,
    )


def _context() -> EMHardwareModelContext:
    return EMHardwareModelContext(
        context_id="CTX-1",
        geometry_id="UC06-NEXTGEN-CANDIDATE",
        mesh_id="UNASSIGNED",
        solver_name="Palace",
        solver_version="0.17.0-12d8069",
        hardware_revision=None,
        notes=["simulation candidate; no physical hardware claim"],
    )


def test_bundle_binds_context_transformations_and_validation():
    intent = _intent()
    candidate = _candidate()
    validation = assess_candidate_for_palace(intent, candidate)
    steps = [
        EMTransformationStep(
            step_id="T1",
            operation="latent candidate generation",
            tool_name="worldshepherd-em",
            tool_version="v0.1",
            input_digest=D0,
            output_digest=D1,
            actor="SARA",
            observed_utc="2026-09-30T19:00:00Z",
        ),
        EMTransformationStep(
            step_id="T2",
            operation="pareto screening",
            tool_name="worldshepherd-em",
            tool_version="v0.1",
            input_digest=D1,
            output_digest=D2,
            actor="SARA",
            observed_utc="2026-09-30T19:01:00Z",
        ),
    ]

    bundle = build_em_candidate_evidence_bundle(
        bundle_id="B-1",
        intent=intent,
        candidate=candidate,
        validation=validation,
        context=_context(),
        transformations=steps,
        source_receipts=["local:r2r-b0-d4-capability-attribution-20260930T001230Z"],
        claims_boundary=["SIMULATION_VALIDATION_ONLY", "NO_HARDWARE_ACTION"],
    )

    assert isinstance(bundle, EMCandidateEvidenceBundle)
    assert bundle.validation.hardware_action_authorized is False
    assert bundle.bundle_digest.startswith("sha256:")
    assert verify_em_candidate_evidence_bundle(bundle) is True


def test_bundle_rejects_noncontiguous_transformation_history():
    intent = _intent()
    candidate = _candidate()
    validation = assess_candidate_for_palace(intent, candidate)
    steps = [
        EMTransformationStep(
            step_id="T1",
            operation="step one",
            tool_name="tool",
            input_digest=D0,
            output_digest=D1,
            actor="SARA",
            observed_utc="2026-09-30T19:00:00Z",
        ),
        EMTransformationStep(
            step_id="T2",
            operation="step two",
            tool_name="tool",
            input_digest=D2,
            output_digest=D0,
            actor="SARA",
            observed_utc="2026-09-30T19:01:00Z",
        ),
    ]

    with pytest.raises(ValueError, match="not digest-contiguous"):
        build_em_candidate_evidence_bundle(
            bundle_id="B-BAD",
            intent=intent,
            candidate=candidate,
            validation=validation,
            context=_context(),
            transformations=steps,
            source_receipts=["receipt"],
            claims_boundary=["NO_HARDWARE_ACTION"],
        )


def test_bundle_digest_detects_tampering():
    intent = _intent()
    candidate = _candidate()
    validation = assess_candidate_for_palace(intent, candidate)
    bundle = build_em_candidate_evidence_bundle(
        bundle_id="B-2",
        intent=intent,
        candidate=candidate,
        validation=validation,
        context=_context(),
        transformations=[],
        source_receipts=["receipt"],
        claims_boundary=["NO_HARDWARE_ACTION"],
    )

    tampered = bundle.model_copy(
        update={
            "context": bundle.context.model_copy(update={"geometry_id": "TAMPERED"})
        }
    )
    assert verify_em_candidate_evidence_bundle(tampered) is False
