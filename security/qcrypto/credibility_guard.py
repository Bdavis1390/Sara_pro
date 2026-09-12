"""Evidence-bounded credibility warrant for Worldshepherd QCRYPTO.

This module evaluates what the research record can legitimately support about
Worldshepherd's process. It does not convert external scientific findings into
claims of original authorship, independent validation, certification,
endorsement, government approval, or demonstrated production cryptographic
compromise.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EvidenceItem:
    name: str
    source_family: str
    external: bool = True
    peer_reviewed: bool = False
    hardware_demonstrated: bool = False
    standards_authority: bool = False
    operational_migration_deployment: bool = False
    national_security_transition_policy: bool = False
    internal_reproducible: bool = False


@dataclass(frozen=True)
class CredibilityWarrant:
    warrant_state: str
    independent_external_families: int
    peer_reviewed_external_present: bool
    hardware_external_present: bool
    standards_authority_present: bool
    operational_migration_present: bool
    national_security_transition_present: bool
    internal_reproducible_present: bool
    warranted_claims: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_credibility(items: list[EvidenceItem]) -> CredibilityWarrant:
    """Return a conservative warrant for research-engineering credibility.

    The strongest state requires independent external evidence families plus
    peer-reviewed science, measured hardware evidence, authoritative standards,
    a real operational post-quantum migration deployment, an official national-
    security transition signal, and a reproducible internal software gate.

    This warrants the quality and relevance of the synthesis and engineering
    process. It does not establish government approval, compliance, endorsement,
    certification, adoption, or external validation of Worldshepherd.
    """

    external_families = {
        item.source_family.strip()
        for item in items
        if item.external and item.source_family.strip()
    }
    peer_reviewed = any(item.external and item.peer_reviewed for item in items)
    hardware = any(item.external and item.hardware_demonstrated for item in items)
    standards = any(item.external and item.standards_authority for item in items)
    operational = any(item.external and item.operational_migration_deployment for item in items)
    national_security = any(item.external and item.national_security_transition_policy for item in items)
    internal = any(item.internal_reproducible for item in items)

    if (
        len(external_families) >= 6
        and peer_reviewed
        and hardware
        and standards
        and operational
        and national_security
        and internal
    ):
        state = "NATIONAL_SECURITY_TRANSITION_AWARE_ENGINEERING_RECORD"
    elif (
        len(external_families) >= 5
        and peer_reviewed
        and hardware
        and standards
        and operational
        and internal
    ):
        state = "MULTI_AXIS_TRIANGULATED_ENGINEERING_RECORD"
    elif len(external_families) >= 3 and peer_reviewed and hardware and internal:
        state = "TRIANGULATED_CLAIMS_CONTROLLED_IMPLEMENTATION"
    elif len(external_families) >= 2 and internal:
        state = "CORROBORATED_CLAIMS_CONTROLLED_IMPLEMENTATION"
    elif internal:
        state = "INTERNAL_IMPLEMENTATION_ONLY"
    elif external_families:
        state = "SOURCE_SYNTHESIS_ONLY"
    else:
        state = "UNWARRANTED"

    warranted: list[str] = []
    if external_families:
        warranted.append(
            "SUPPORTED_BY_LITERATURE: the quantum-risk and migration premises are grounded in cited external publications and primary sources."
        )
    if standards:
        warranted.append(
            "STANDARDS_ALIGNED: the migration case is anchored to authoritative post-quantum standards and transition guidance."
        )
    if operational:
        warranted.append(
            "DEPLOYMENT_AWARE: the record includes a real post-quantum migration capability deployed by an external blockchain ecosystem."
        )
    if national_security:
        warranted.append(
            "NATIONAL_SECURITY_TRANSITION_AWARE: the record tracks official NSA/CNSS post-quantum transition activity affecting National Security Systems and CSfC solution architectures."
        )
    if internal:
        warranted.append(
            "IMPLEMENTED_IN_SOFTWARE: Worldshepherd has encoded claims-control and migration-risk logic in a reproducible repository workflow."
        )
        warranted.append(
            "PROVEN_INTERNALLY: the referenced repository validation gate can establish that the software checks passed at an exact commit head."
        )
    if state == "NATIONAL_SECURITY_TRANSITION_AWARE_ENGINEERING_RECORD":
        warranted.append(
            "CREDIBILITY WARRANTED FOR PROCESS AND TRANSITION RELEVANCE: the record triangulates peer-reviewed analysis, hardware progress, standards guidance, operational migration evidence, national-security transition policy, and reproducible internal controls without collapsing their evidence classes."
        )
    elif state == "MULTI_AXIS_TRIANGULATED_ENGINEERING_RECORD":
        warranted.append(
            "CREDIBILITY WARRANTED FOR PROCESS: the record triangulates peer-reviewed analysis, architecture-specific estimates, measured hardware progress, standards guidance, operational migration evidence, and reproducible internal controls without collapsing their evidence classes."
        )
    elif state == "TRIANGULATED_CLAIMS_CONTROLLED_IMPLEMENTATION":
        warranted.append(
            "CREDIBILITY WARRANTED FOR PROCESS: multiple independent evidence classes are synthesized with reproducible claims controls."
        )

    excluded = (
        "Original authorship of cited external scientific discoveries.",
        "Independent external validation, endorsement, certification, or adoption of Worldshepherd.",
        "Government approval, NSA approval, CNSS approval, CSfC registration, or demonstrated compliance.",
        "Demonstration of a production-strength cryptographic key break.",
        "Possession of a cryptographically relevant quantum computer.",
        "Proof that any cryptocurrency is presently compromised by quantum attack.",
        "Proof that a partial post-quantum deployment makes an entire blockchain ecosystem quantum-safe.",
    )

    return CredibilityWarrant(
        warrant_state=state,
        independent_external_families=len(external_families),
        peer_reviewed_external_present=peer_reviewed,
        hardware_external_present=hardware,
        standards_authority_present=standards,
        operational_migration_present=operational,
        national_security_transition_present=national_security,
        internal_reproducible_present=internal,
        warranted_claims=tuple(warranted),
        excluded_claims=excluded,
    )
