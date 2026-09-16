"""Claims-controlled comparative assurance benchmark for Worldshepherd PoO.

The benchmark can establish that one assurance profile is stronger on an explicit,
selected set of dimensions. It intentionally cannot establish global superiority,
legal superiority, standards compliance, production readiness, or external validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

BENCHMARK_SCHEMA = "WS-POO-METHODOLOGY-BENCHMARK-V1"

ASSURANCE_DIMENSIONS: Tuple[str, ...] = (
    "identity_binding",
    "asset_binding",
    "challenge_response_control",
    "custody_evidence_binding",
    "exact_coc_digest_binding",
    "provenance_binding",
    "freshness",
    "revocation",
    "ownership_lineage",
    "custody_lineage",
    "coupled_ownership_custody_lineage",
    "conflict_detection",
    "stale_writer_protection",
    "durable_audit_provenance",
    "human_approval_boundary",
    "legal_title_nonclaim",
    "standard_interoperability",
    "independent_implementation",
    "formal_verification",
    "production_deployment",
    "legal_recognition",
)


@dataclass(frozen=True)
class AssuranceProfile:
    name: str
    dimensions: Mapping[str, bool]


@dataclass(frozen=True)
class ComparativeDecision:
    schema: str
    candidate: str
    baseline: str
    selected_dimensions: Tuple[str, ...]
    stronger_dimensions: Tuple[str, ...]
    weaker_dimensions: Tuple[str, ...]
    equal_dimensions: Tuple[str, ...]
    status: str
    stronger_on_selected_dimensions: bool
    global_superiority_established: bool
    standards_compliance_established: bool
    legal_superiority_established: bool
    external_validation_established: bool


@dataclass(frozen=True)
class TripleCheckEvidence:
    protocol_regressions_passed: bool
    native_integration_regressions_passed: bool
    comparative_benchmark_passed: bool
    independent_implementation_reproduced: bool = False
    formal_verification_completed: bool = False
    production_deployment_validated: bool = False
    legal_recognition_established: bool = False


@dataclass(frozen=True)
class TripleCheckDecision:
    status: str
    internal_method_validation_complete: bool
    external_validation_established: bool
    global_superiority_established: bool
    production_readiness_established: bool
    legal_superiority_established: bool


def _validate_profile(profile: AssuranceProfile) -> None:
    unknown = sorted(set(profile.dimensions) - set(ASSURANCE_DIMENSIONS))
    if unknown:
        raise ValueError(f"unknown assurance dimensions: {', '.join(unknown)}")


def compare_profiles(
    candidate: AssuranceProfile,
    baseline: AssuranceProfile,
    *,
    selected_dimensions: Iterable[str],
) -> ComparativeDecision:
    """Compare two profiles only on explicitly selected dimensions."""
    _validate_profile(candidate)
    _validate_profile(baseline)
    selected = tuple(dict.fromkeys(selected_dimensions))
    if not selected:
        raise ValueError("at least one comparison dimension is required")
    unknown = sorted(set(selected) - set(ASSURANCE_DIMENSIONS))
    if unknown:
        raise ValueError(f"unknown selected dimensions: {', '.join(unknown)}")

    stronger = []
    weaker = []
    equal = []
    for dimension in selected:
        candidate_value = bool(candidate.dimensions.get(dimension, False))
        baseline_value = bool(baseline.dimensions.get(dimension, False))
        if candidate_value and not baseline_value:
            stronger.append(dimension)
        elif baseline_value and not candidate_value:
            weaker.append(dimension)
        else:
            equal.append(dimension)

    selected_stronger = bool(stronger) and not weaker
    if selected_stronger:
        status = "STRONGER_ON_SELECTED_DIMENSIONS_ONLY"
    elif weaker:
        status = "MIXED_OR_WEAKER_ON_SELECTED_DIMENSIONS"
    else:
        status = "EQUIVALENT_ON_SELECTED_DIMENSIONS"

    return ComparativeDecision(
        schema=BENCHMARK_SCHEMA,
        candidate=candidate.name,
        baseline=baseline.name,
        selected_dimensions=selected,
        stronger_dimensions=tuple(stronger),
        weaker_dimensions=tuple(weaker),
        equal_dimensions=tuple(equal),
        status=status,
        stronger_on_selected_dimensions=selected_stronger,
        global_superiority_established=False,
        standards_compliance_established=False,
        legal_superiority_established=False,
        external_validation_established=False,
    )


def poo_v3_internal_profile() -> AssuranceProfile:
    """Return only capabilities exercised by the current internal PoO V3 test design."""
    return AssuranceProfile(
        name="Worldshepherd PoO V3 internal",
        dimensions={
            "identity_binding": True,
            "asset_binding": True,
            "challenge_response_control": True,
            "custody_evidence_binding": True,
            "exact_coc_digest_binding": True,
            "provenance_binding": True,
            "freshness": True,
            "revocation": True,
            "ownership_lineage": True,
            "custody_lineage": True,
            "coupled_ownership_custody_lineage": True,
            "conflict_detection": True,
            "stale_writer_protection": True,
            "durable_audit_provenance": True,
            "human_approval_boundary": True,
            "legal_title_nonclaim": True,
            "standard_interoperability": False,
            "independent_implementation": False,
            "formal_verification": False,
            "production_deployment": False,
            "legal_recognition": False,
        },
    )


def modeled_current_practice_composite_profile() -> AssuranceProfile:
    """Return a deliberately generous upper-bound model of current practice.

    This is not one deployed system. It gives today's ecosystem collective credit for
    capabilities supplied across mature wallet authentication, on-chain asset state,
    verifiable credentials/identifiers, institutional custody controls, audit systems,
    and authoritative legal registries. It therefore prevents a strawman comparison.
    """
    return AssuranceProfile(
        name="modeled current-practice composite upper bound",
        dimensions={
            "identity_binding": True,
            "asset_binding": True,
            "challenge_response_control": True,
            "custody_evidence_binding": True,
            "exact_coc_digest_binding": False,
            "provenance_binding": True,
            "freshness": True,
            "revocation": True,
            "ownership_lineage": True,
            "custody_lineage": True,
            "coupled_ownership_custody_lineage": False,
            "conflict_detection": True,
            "stale_writer_protection": True,
            "durable_audit_provenance": True,
            "human_approval_boundary": True,
            "legal_title_nonclaim": True,
            "standard_interoperability": True,
            "independent_implementation": True,
            "formal_verification": False,
            "production_deployment": True,
            "legal_recognition": True,
        },
    )


def evaluate_triple_check(evidence: TripleCheckEvidence) -> TripleCheckDecision:
    internal = (
        evidence.protocol_regressions_passed
        and evidence.native_integration_regressions_passed
        and evidence.comparative_benchmark_passed
    )
    return TripleCheckDecision(
        status=(
            "INTERNAL_TRIPLE_CHECK_COMPLETE"
            if internal
            else "INTERNAL_TRIPLE_CHECK_INCOMPLETE"
        ),
        internal_method_validation_complete=internal,
        external_validation_established=evidence.independent_implementation_reproduced,
        global_superiority_established=False,
        production_readiness_established=(
            evidence.production_deployment_validated
            and evidence.independent_implementation_reproduced
        ),
        legal_superiority_established=False,
    )


def profile_record(profile: AssuranceProfile) -> Dict[str, object]:
    _validate_profile(profile)
    return {"name": profile.name, "dimensions": dict(profile.dimensions)}
