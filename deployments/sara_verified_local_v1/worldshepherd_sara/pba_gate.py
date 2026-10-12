from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .pba_authorization import (
    PBAAuthorizationVerifier,
    PBAReplayLedger,
    VerifiedPBAAuthorization,
)
from .pba_models import PBAObservation, SafeToBeamAuthorization
from .pba_state_machine import PBADecision, evaluate_delivery_authorization


@dataclass(frozen=True, slots=True)
class PBAGateResult:
    """Result of the combined cryptographic + semantic admission gate."""

    permitted: bool
    reason: str
    verified_authorization: VerifiedPBAAuthorization


def authorize_delivery_once(
    *,
    verifier: PBAAuthorizationVerifier,
    ledger: PBAReplayLedger,
    token: SafeToBeamAuthorization,
    observation: PBAObservation,
    now: datetime | None = None,
) -> PBAGateResult:
    """Admit one bounded delivery transition only after both G2 and G1 checks pass.

    Ordering is intentional:

    1. cryptographically verify the token and its time/key policy;
    2. evaluate the live G1 semantic assurance invariants;
    3. claim the token in the persistent replay ledger only when the semantic
       decision is permitted.

    A transient semantic denial therefore does not burn an otherwise valid
    authorization. Once a transition is permitted, the token becomes one-use;
    a subsequent attempt is rejected by ``PBAReplayLedger``.

    This function returns authorization state only. It exposes no partner
    hardware actuation, pointing, targeting, waveform, or beam-control method.
    """

    verified = verifier.verify(token, now=now)
    decision: PBADecision = evaluate_delivery_authorization(
        token,
        observation,
        now=now,
    )
    if not decision.permitted:
        return PBAGateResult(
            permitted=False,
            reason=decision.reason,
            verified_authorization=verified,
        )

    ledger.claim(verified)
    return PBAGateResult(
        permitted=True,
        reason=decision.reason,
        verified_authorization=verified,
    )
