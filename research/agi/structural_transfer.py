from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class StructuralTaskSignature:
    roles: frozenset[str]
    relations: frozenset[str]
    dynamics: frozenset[str]

    def features(self) -> frozenset[str]:
        return frozenset(
            {f"role:{x}" for x in self.roles}
            | {f"rel:{x}" for x in self.relations}
            | {f"dyn:{x}" for x in self.dynamics}
        )

def structural_similarity(
    a: StructuralTaskSignature,
    b: StructuralTaskSignature,
) -> float:
    af = a.features()
    bf = b.features()
    union = af | bf
    if not union:
        return 1.0
    return len(af & bf) / len(union)

@dataclass(frozen=True)
class TransferProposal:
    source_skill_id: str
    similarity: float
    source_signature: StructuralTaskSignature
    target_signature: StructuralTaskSignature

    def claim_state(self, threshold: float = 0.5) -> str:
        if self.similarity < threshold:
            return "INSUFFICIENT_STRUCTURAL_OVERLAP"
        return "TRANSFER_HYPOTHESIS_REQUIRES_TARGET_VALIDATION"

def propose_transfer(
    source_skill_id: str,
    source: StructuralTaskSignature,
    target: StructuralTaskSignature,
) -> TransferProposal:
    return TransferProposal(
        source_skill_id,
        structural_similarity(source,target),
        source,
        target,
    )
