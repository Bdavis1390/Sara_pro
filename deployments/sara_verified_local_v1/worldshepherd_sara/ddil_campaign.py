from __future__ import annotations

from typing import Any

from .ddil import Envelope, FaultProfile, apply_fault_profile
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def _profiles() -> dict[str, FaultProfile]:
    return {
        "nominal": FaultProfile(),
        "packet_loss": FaultProfile(drop_sequences=frozenset({2, 5})),
        "latency": FaultProfile(added_latency_ms=250),
        "reorder": FaultProfile(reorder_windows=((2, 4),)),
        "stale_and_duplicate": FaultProfile(
            stale_sequences=frozenset({3}), duplicate_sequences=frozenset({4})
        ),
    }


def run_ddil_campaign(
    *,
    messages: list[Envelope],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    """Exercise deterministic message-fault handling and package internal evidence.

    Passing this campaign proves only the software harness behaves reproducibly
    against its synthetic fault profiles. It is not tactical-link or mission DDIL
    validation.
    """
    evidence: list[QualificationEvidenceRecord] = []
    base_digest = canonical_digest(
        [
            {
                "sequence": m.sequence,
                "source": m.source,
                "payload": m.payload,
                "timestamp_ms": m.timestamp_ms,
            }
            for m in messages
        ]
    )

    for index, (name, profile) in enumerate(_profiles().items(), start=1):
        first = apply_fault_profile(messages, profile)
        second = apply_fault_profile(messages, profile)
        deterministic = first.replay_signature() == second.replay_signature()
        result = ResultStatus.PASS if deterministic else ResultStatus.FAIL
        evidence.append(
            QualificationEvidenceRecord(
                qualification_id=f"WS-QE-2026-{1000 + index:04d}",
                requirement_id=requirement.requirement_delta_id,
                test_id=f"ddil_{name}",
                evidence_scope=EvidenceScope.SOFTWARE,
                capability_status=CapabilityStatus.PROVEN_INTERNALLY,
                environment_digest=canonical_digest({"campaign": "ddil_v1"}),
                configuration_digest=canonical_digest(
                    {
                        "profile": name,
                        "drop": sorted(profile.drop_sequences),
                        "duplicate": sorted(profile.duplicate_sequences),
                        "stale": sorted(profile.stale_sequences),
                        "latency_ms": profile.added_latency_ms,
                        "reorder_windows": profile.reorder_windows,
                    }
                ),
                inputs=[{"message_set_digest": base_digest}],
                outputs=[
                    {
                        "replay_signature": first.replay_signature(),
                        "dropped": first.dropped,
                        "duplicated": first.duplicated,
                        "stale": first.stale,
                    }
                ],
                metrics=[{"name": "deterministic_replay", "value": deterministic}],
                uncertainty=[
                    {"name": "operational_network_validity", "state": "NOT_EVALUATED"}
                ],
                result=result,
                rationale=(
                    "Synthetic fault profile replay was deterministic"
                    if deterministic
                    else "Synthetic fault profile replay diverged"
                ),
                negative_evidence=[] if deterministic else [{"profile": name}],
                software_commit=software_commit,
                executed_utc=executed_utc,
                operator=operator,
            )
        )

    bundle = compile_qualification_bundle(requirement, evidence)
    bundle.pop("bundle_digest", None)
    bundle["campaign"] = "DDIL_SYNTHETIC_V1"
    bundle["scope_note"] = (
        "Synthetic transport-fault qualification only; no RF, tactical network, or mission-readiness claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
