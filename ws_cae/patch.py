from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from .reference import Profile, assess


@dataclass(frozen=True)
class EvidenceRef:
    label: str
    url: str
    claim: str


@dataclass(frozen=True)
class ChainPatch:
    spec: str
    chain: str
    revision: int
    as_of: str
    profile: Profile
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True)
class PatchAssessment:
    valid: bool
    state: str
    profile_assessment: dict
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def assess_patch(patch: ChainPatch) -> PatchAssessment:
    issues: list[str] = []
    if patch.spec != "WS-CAE-CHAIN-PATCH-1":
        issues.append("spec must be WS-CAE-CHAIN-PATCH-1")
    if not patch.chain.strip():
        issues.append("chain must be non-empty")
    if not patch.evidence:
        issues.append("at least one evidence reference is required")
    for index, ref in enumerate(patch.evidence):
        if not ref.label.strip() or not ref.claim.strip():
            issues.append(f"evidence[{index}] requires label and claim")
        if not _https(ref.url):
            issues.append(f"evidence[{index}] must use an https URL")

    profile_result = assess(patch.profile)
    if not profile_result.valid:
        issues.append("embedded profile is nonconformant")
    if patch.profile.ecosystem.strip().lower() != patch.chain.strip().lower():
        issues.append("chain and embedded profile ecosystem must match")

    state = "CHAIN_PATCH_VALID" if not issues else "CHAIN_PATCH_INVALID"
    return PatchAssessment(not issues, state, profile_result.to_dict(), tuple(issues))
