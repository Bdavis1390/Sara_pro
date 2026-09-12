"""Evidence-bounded credibility warrant for Worldshepherd QCRYPTO.

This module evaluates what the research record can legitimately support about
Worldshepherd's process. It deliberately does not turn external scientific
findings into claims of original authorship, independent validation, quantum
hardware capability, certification, or a demonstrated production key break.
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
    internal_reproducible: bool = False


@dataclass(frozen=True)
class CredibilityWarrant:
    warrant_state: str
    independent_external_families: int
    peer_reviewed_external_present: bool
    hardware_external_present: bool
    internal_reproducible_present: bool
    warranted_claims: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_credibility(items: list[EvidenceItem]) -> CredibilityWarrant:
    """Return a conservative warrant for research-engineering credibility.

    The highest state means the *process* is triangulated: multiple independent
    external evidence families, peer-reviewed support, hardware evidence, and a
    reproducible internal software gate are all present. It is not a scientific
    endorsement of Worldshepherd by those external sources.
    """

    external_families = {
        item.source_family.strip()
        for item in items
        if item.external and item.source_family.strip()
    }
    peer_reviewed = any(item.external and item.peer_reviewed for item in items)
    hardware = any(item.external and item.hardware_demonstrated for item in items)
    internal = any(item.internal_reproducible for item in items)

    if len(external_families) >= 3 and peer_reviewed and hardware and internal:
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
            "SUPPORTED_BY_LITERATURE: the quantum-risk premises are grounded in cited external publications."
        )
    if internal:
        warranted.append(
            "IMPLEMENTED_IN_SOFTWARE: Worldshepherd has encoded claims-control and migration-risk logic in a reproducible repository workflow."
        )
        warranted.append(
            "PROVEN_INTERNALLY: the referenced repository validation gate can establish that the software checks passed at an exact commit head."
        )
    if len(external_families) >= 3 and peer_reviewed and hardware and internal:
        warranted.append(
            "CREDIBILITY WARRANTED FOR PROCESS: independent algorithmic, architecture-specific, peer-reviewed, and hardware-QEC evidence is being synthesized without collapsing their distinct evidence classes."
        )

    excluded = (
        "Original authorship of the cited external scientific discoveries.",
        "Independent external validation, endorsement, certification, or adoption of Worldshepherd.",
        "Demonstration of a production-strength cryptographic key break.",
        "Possession of a cryptographically relevant quantum computer.",
        "Proof that any cryptocurrency is presently compromised by quantum attack.",
    )

    return CredibilityWarrant(
        warrant_state=state,
        independent_external_families=len(external_families),
        peer_reviewed_external_present=peer_reviewed,
        hardware_external_present=hardware,
        internal_reproducible_present=internal,
        warranted_claims=tuple(warranted),
        excluded_claims=excluded,
    )
