from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .model import LinkState, LinkType


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PrimeSentinelPolicy:
    """Minimal route authorization policy for the v0.1 simulator.

    This is not BPSec or a cryptographic authorization implementation. It is a
    deterministic policy gate intended to exercise Worldshepherd control flow.
    """

    def __init__(self, minimum_survival: float = 0.40, allow_untrusted: bool = False):
        self.minimum_survival = minimum_survival
        self.allow_untrusted = allow_untrusted

    def authorize(self, link: LinkState) -> PolicyDecision:
        if not link.up:
            return PolicyDecision(False, "link_down")
        if not link.trusted and not self.allow_untrusted:
            return PolicyDecision(False, "untrusted_link")
        if link.survival_probability < self.minimum_survival:
            return PolicyDecision(False, "survival_below_policy_floor")
        return PolicyDecision(True, "authorized")

    def select(self, links: Iterable[LinkState]) -> Optional[LinkState]:
        candidates = []
        for link in links:
            decision = self.authorize(link)
            if decision.allowed:
                optical_bonus = 1.08 if link.link_type == LinkType.OPTICAL else 1.0
                score = link.rate_mbps * link.survival_probability * optical_bonus
                candidates.append((score, link))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
