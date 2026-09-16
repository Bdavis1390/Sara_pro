"""Fail-closed multi-provider Hoodi checkpoint bootstrap assessment.

This reduces reliance on any single checkpoint provider during weak-subjectivity
bootstrap. It does not replace Ethereum consensus verification: after bootstrap,
the local execution/consensus clients remain responsible for validating chain
state under the protocol rules.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re


HOODI_CHECKPOINT_PROVIDERS = {
    "sigma_prime": "https://hoodi.checkpoint.sigp.io",
    "ethpandaops": "https://checkpoint-sync.hoodi.ethpandaops.io",
    "ethstaker": "https://hoodi.beaconstate.ethstaker.cc",
}
ROOT_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class HoodiCheckpointQuorumAssessment:
    state: str
    configured_provider: str | None
    configured_url: str
    quorum_root: str | None
    agreeing_providers: tuple[str, ...]
    observed_roots: dict[str, str]
    provider_count: int
    quorum_count: int
    accepted: bool
    consensus_verification_replaced: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize(url: str) -> str:
    return url.rstrip("/")


def assess_hoodi_checkpoint_quorum(
    configured_url: str,
    provider_roots: dict[str, str],
) -> HoodiCheckpointQuorumAssessment:
    blockers: list[str] = []
    warnings: list[str] = []
    configured_url = _normalize(configured_url)

    provider_by_url = {_normalize(url): name for name, url in HOODI_CHECKPOINT_PROVIDERS.items()}
    configured_provider = provider_by_url.get(configured_url)
    if configured_provider is None:
        blockers.append("Configured Hoodi checkpoint URL is not in the reviewed provider set.")

    clean: dict[str, str] = {}
    for name, root in provider_roots.items():
        if name not in HOODI_CHECKPOINT_PROVIDERS:
            blockers.append(f"Unknown checkpoint provider in evidence: {name}")
            continue
        if not isinstance(root, str) or not ROOT_RE.fullmatch(root):
            blockers.append(f"Invalid finalized root from provider: {name}")
            continue
        clean[name] = root.lower()

    if len(clean) < 2:
        blockers.append("At least two independent Hoodi checkpoint providers must return valid finalized roots.")

    quorum_root: str | None = None
    agreeing: tuple[str, ...] = ()
    quorum_count = 0
    if clean:
        counts = Counter(clean.values())
        candidate, count = counts.most_common(1)[0]
        quorum_count = count
        if count >= 2:
            quorum_root = candidate
            agreeing = tuple(sorted(name for name, root in clean.items() if root == candidate))
        else:
            blockers.append("No 2-of-N agreement exists on the Hoodi finalized root.")

    if configured_provider is not None and quorum_root is not None:
        configured_root = clean.get(configured_provider)
        if configured_root is None:
            blockers.append("Configured checkpoint provider did not return a valid finalized root.")
        elif configured_root != quorum_root:
            blockers.append("Configured checkpoint provider disagrees with the multi-provider finalized-root quorum.")

    accepted = not blockers and quorum_root is not None and quorum_count >= 2
    if accepted:
        state = "HOODI_CHECKPOINT_QUORUM_ACCEPTED"
        warnings.append(
            "Checkpoint-provider agreement is only weak-subjectivity bootstrap evidence; it does not replace local Ethereum consensus verification."
        )
    else:
        state = "HOODI_CHECKPOINT_QUORUM_REJECTED"

    return HoodiCheckpointQuorumAssessment(
        state=state,
        configured_provider=configured_provider,
        configured_url=configured_url,
        quorum_root=quorum_root,
        agreeing_providers=agreeing,
        observed_roots=clean,
        provider_count=len(clean),
        quorum_count=quorum_count,
        accepted=accepted,
        consensus_verification_replaced=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
