"""WS-QPOS-1 bounded proof-of-stake preservation model.

Purpose
-------
Model cryptographic credential migration separately from validator economic state
and prove bounded preservation properties for the allowed migration transitions.

This module does NOT implement a post-quantum signature scheme, consensus client,
key generation, transaction signing, staking operations, or live-network changes.
It proves only the modeled state-preservation obligations under explicit
assumptions about the external cryptographic and consensus implementations.

Claims boundary
---------------
A PASS from this module means:
    BOUNDED_MODEL_PROOF_OF_POS_MIGRATION_PRESERVATION
It does not mean:
    PRODUCTION_PQ_CONSENSUS_PROVEN
    CRYPTOGRAPHIC_SECURITY_PROVEN
    ETHEREUM_MAINNET_COMPATIBILITY_PROVEN
    FORMAL_VERIFICATION_OF_CLIENT_IMPLEMENTATIONS
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from itertools import product
from math import ceil
from typing import Iterable, Sequence


class AuthMode(str, Enum):
    CLASSICAL = "CLASSICAL"
    PQ_REGISTERED = "PQ_REGISTERED"
    HYBRID_REQUIRED = "HYBRID_REQUIRED"
    PQ_PRIMARY = "PQ_PRIMARY"
    CLASSICAL_DISABLED = "CLASSICAL_DISABLED"
    EMERGENCY_PQ = "EMERGENCY_PQ"


@dataclass(frozen=True)
class ValidatorState:
    validator_id: str
    stake: int
    effective_balance: int
    withdrawal_owner: str
    slashed: bool
    slashing_history: tuple[str, ...]
    classical_credential: str
    pq_credential: str | None = None
    pq_scheme: str | None = None
    auth_mode: AuthMode = AuthMode.CLASSICAL
    aggregator_eligible: bool = False

    def __post_init__(self) -> None:
        if not self.validator_id:
            raise ValueError("validator_id is required")
        if self.stake < 0 or self.effective_balance < 0:
            raise ValueError("stake and effective_balance must be non-negative")
        if self.effective_balance > self.stake:
            raise ValueError("effective_balance cannot exceed stake in this model")
        if not self.withdrawal_owner:
            raise ValueError("withdrawal_owner is required")
        if not self.classical_credential:
            raise ValueError("classical_credential is required")
        if self.pq_credential is None and self.auth_mode not in {AuthMode.CLASSICAL}:
            raise ValueError("non-classical auth modes require a PQ credential")


@dataclass(frozen=True)
class EconomicProjection:
    validator_id: str
    stake: int
    effective_balance: int
    withdrawal_owner: str
    slashed: bool
    slashing_history: tuple[str, ...]


@dataclass(frozen=True)
class PreservationResult:
    preserved: bool
    before: EconomicProjection
    after: EconomicProjection
    changed_fields: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "preserved": self.preserved,
            "before": asdict(self.before),
            "after": asdict(self.after),
            "changed_fields": list(self.changed_fields),
        }


@dataclass(frozen=True)
class ProofReport:
    proof_status: str
    claim_state: str
    validator_transition_cases: int
    validator_set_cases: int
    hybrid_double_count_cases: int
    invalid_transition_cases: int
    assumptions: tuple[str, ...]
    proven_properties: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        for field in ("assumptions", "proven_properties", "excluded_claims"):
            data[field] = list(data[field])
        return data


def economic_projection(state: ValidatorState) -> EconomicProjection:
    return EconomicProjection(
        validator_id=state.validator_id,
        stake=state.stake,
        effective_balance=state.effective_balance,
        withdrawal_owner=state.withdrawal_owner,
        slashed=state.slashed,
        slashing_history=state.slashing_history,
    )


def preservation_result(before: ValidatorState, after: ValidatorState) -> PreservationResult:
    left = economic_projection(before)
    right = economic_projection(after)
    changed = tuple(
        name
        for name in EconomicProjection.__dataclass_fields__
        if getattr(left, name) != getattr(right, name)
    )
    return PreservationResult(not changed, left, right, changed)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def register_pq_credential(state: ValidatorState, *, credential: str, scheme: str) -> ValidatorState:
    _require(state.auth_mode is AuthMode.CLASSICAL, "PQ registration requires CLASSICAL mode")
    _require(bool(credential), "PQ credential is required")
    _require(bool(scheme), "PQ scheme identifier is required")
    return replace(
        state,
        pq_credential=credential,
        pq_scheme=scheme,
        auth_mode=AuthMode.PQ_REGISTERED,
    )


def require_hybrid_auth(state: ValidatorState) -> ValidatorState:
    _require(state.auth_mode is AuthMode.PQ_REGISTERED, "hybrid activation requires PQ_REGISTERED mode")
    _require(state.pq_credential is not None, "hybrid activation requires a PQ credential")
    return replace(state, auth_mode=AuthMode.HYBRID_REQUIRED)


def activate_pq_primary(state: ValidatorState) -> ValidatorState:
    _require(state.auth_mode is AuthMode.HYBRID_REQUIRED, "PQ primary requires HYBRID_REQUIRED mode")
    return replace(state, auth_mode=AuthMode.PQ_PRIMARY)


def disable_classical_auth(state: ValidatorState) -> ValidatorState:
    _require(state.auth_mode is AuthMode.PQ_PRIMARY, "classical sunset requires PQ_PRIMARY mode")
    return replace(state, auth_mode=AuthMode.CLASSICAL_DISABLED)


def enter_emergency_pq(state: ValidatorState) -> ValidatorState:
    _require(state.pq_credential is not None, "emergency PQ requires a registered PQ credential")
    return replace(state, auth_mode=AuthMode.EMERGENCY_PQ)


def set_aggregator_eligibility(state: ValidatorState, eligible: bool) -> ValidatorState:
    """Aggregator role is operational metadata and must not change stake weight."""
    return replace(state, aggregator_eligible=eligible)


def accepted_authentication(state: ValidatorState, supplied: Iterable[str]) -> bool:
    supplied_set = frozenset(supplied)
    has_classical = "classical" in supplied_set
    has_pq = "pq" in supplied_set

    if state.auth_mode in {AuthMode.CLASSICAL, AuthMode.PQ_REGISTERED}:
        return has_classical
    if state.auth_mode is AuthMode.HYBRID_REQUIRED:
        return has_classical and has_pq
    if state.auth_mode in {AuthMode.PQ_PRIMARY, AuthMode.CLASSICAL_DISABLED, AuthMode.EMERGENCY_PQ}:
        return has_pq
    raise AssertionError(f"Unhandled auth mode: {state.auth_mode}")


def validate_registry(states: Sequence[ValidatorState]) -> None:
    validator_ids = [s.validator_id for s in states]
    if len(set(validator_ids)) != len(validator_ids):
        raise ValueError("validator_id values must be unique")

    pq_credentials = [s.pq_credential for s in states if s.pq_credential is not None]
    if len(set(pq_credentials)) != len(pq_credentials):
        raise ValueError("PQ credentials must be unique in the WS-QPOS-1 registry model")


def total_effective_balance(states: Sequence[ValidatorState]) -> int:
    return sum(s.effective_balance for s in states)


def supermajority_threshold(states: Sequence[ValidatorState]) -> int:
    """Abstract >=2/3 stake threshold used only for preservation comparison."""
    total = total_effective_balance(states)
    return ceil((2 * total) / 3) if total else 0


def vote_weight_once(states: Sequence[ValidatorState], authenticated_validator_ids: Iterable[str]) -> int:
    """Count each validator identity once, even if hybrid credentials both authenticate it."""
    validate_registry(states)
    requested = frozenset(authenticated_validator_ids)
    return sum(s.effective_balance for s in states if s.validator_id in requested)


def pq_ready_stake(states: Sequence[ValidatorState]) -> int:
    return sum(
        s.effective_balance
        for s in states
        if s.auth_mode in {
            AuthMode.HYBRID_REQUIRED,
            AuthMode.PQ_PRIMARY,
            AuthMode.CLASSICAL_DISABLED,
            AuthMode.EMERGENCY_PQ,
        }
    )


def pq_ready_stake_fraction(states: Sequence[ValidatorState]) -> float:
    total = total_effective_balance(states)
    return 0.0 if total == 0 else pq_ready_stake(states) / total


def migrate_full_path(state: ValidatorState, *, pq_credential: str, pq_scheme: str) -> tuple[ValidatorState, ...]:
    s1 = register_pq_credential(state, credential=pq_credential, scheme=pq_scheme)
    s2 = require_hybrid_auth(s1)
    s3 = activate_pq_primary(s2)
    s4 = disable_classical_auth(s3)
    return s1, s2, s3, s4


def assert_preserved(before: ValidatorState, after: ValidatorState) -> None:
    result = preservation_result(before, after)
    if not result.preserved:
        raise AssertionError(f"migration changed protected economic fields: {result.changed_fields}")


def _sample_base_states() -> tuple[ValidatorState, ...]:
    states: list[ValidatorState] = []
    for stake, effective, slashed, history_len in product(
        (1, 32, 64),
        (0, 1, 32),
        (False, True),
        (0, 2),
    ):
        if effective > stake:
            continue
        history = tuple(f"slash-event-{i}" for i in range(history_len))
        states.append(
            ValidatorState(
                validator_id=f"v-{stake}-{effective}-{int(slashed)}-{history_len}",
                stake=stake,
                effective_balance=effective,
                withdrawal_owner=f"owner-{stake}-{effective}",
                slashed=slashed,
                slashing_history=history,
                classical_credential=f"bls-{stake}-{effective}-{int(slashed)}-{history_len}",
            )
        )
    return tuple(states)


def run_bounded_preservation_proof() -> ProofReport:
    """Exhaustively check the finite WS-QPOS-1 proof domain.

    The proof is intentionally bounded and implementation-local. It verifies the
    preservation invariants for every state in the enumerated domain and for all
    defined credential-migration stages. Cryptographic soundness of the PQ
    primitive and production consensus implementations are assumptions, not
    conclusions of this function.
    """

    bases = _sample_base_states()
    transition_cases = 0
    invalid_cases = 0

    for index, base in enumerate(bases):
        path = migrate_full_path(
            base,
            pq_credential=f"pq-{index}",
            pq_scheme="ABSTRACT_PQ_SIGNATURE",
        )
        previous = base
        for stage in path:
            assert_preserved(base, stage)
            assert_preserved(previous, stage)
            previous = stage
            transition_cases += 1

        emergency = enter_emergency_pq(path[0])
        assert_preserved(base, emergency)
        transition_cases += 1

        aggregator = set_aggregator_eligibility(path[-1], True)
        assert_preserved(base, aggregator)
        transition_cases += 1

        try:
            disable_classical_auth(base)
        except ValueError:
            invalid_cases += 1
        else:
            raise AssertionError("invalid direct CLASSICAL -> CLASSICAL_DISABLED transition was accepted")

        try:
            activate_pq_primary(path[0])
        except ValueError:
            invalid_cases += 1
        else:
            raise AssertionError("invalid PQ_REGISTERED -> PQ_PRIMARY transition was accepted")

    set_cases = 0
    double_count_cases = 0
    sample = bases[:6]
    for width in (1, 2, 3):
        for indices in product(range(len(sample)), repeat=width):
            if len(set(indices)) != width:
                continue
            before = tuple(sample[i] for i in indices)
            validate_registry(before)
            after = tuple(
                migrate_full_path(
                    state,
                    pq_credential=f"set-pq-{width}-{slot}-{state.validator_id}",
                    pq_scheme="ABSTRACT_PQ_SIGNATURE",
                )[-1]
                for slot, state in enumerate(before)
            )
            validate_registry(after)

            if total_effective_balance(before) != total_effective_balance(after):
                raise AssertionError("total effective balance changed under credential migration")
            if supermajority_threshold(before) != supermajority_threshold(after):
                raise AssertionError("stake-weighted supermajority threshold changed under credential migration")
            if tuple(economic_projection(s) for s in before) != tuple(economic_projection(s) for s in after):
                raise AssertionError("validator-set economic projection changed under credential migration")
            set_cases += 1

            ids = [s.validator_id for s in after]
            if vote_weight_once(after, ids + ids) != total_effective_balance(after):
                raise AssertionError("hybrid/double credential evidence inflated stake weight")
            double_count_cases += 1

    assumptions = (
        "The selected PQ signature primitive is quantum-resistant for the required security lifetime.",
        "Signature verification and any aggregation/proof system are implemented correctly and soundly.",
        "Consensus clients preserve the modeled validator-ID and stake-ledger semantics.",
        "Credential migration authorization occurs through a trusted governance/recovery path before classical compromise can subvert registration.",
        "The abstract >=2/3 threshold comparison is used only to prove threshold preservation, not to reproduce every production consensus edge case.",
    )
    proven = (
        "Credential migration preserves validator identity.",
        "Credential migration preserves stake and effective balance.",
        "Credential migration preserves withdrawal ownership.",
        "Credential migration preserves slashed state and slashing history.",
        "Aggregator eligibility cannot change modeled economic weight.",
        "Stake-weighted supermajority threshold is invariant under credential migration.",
        "Hybrid credentials cannot double-count validator stake when votes are keyed by validator identity.",
        "Classical authentication is rejected after classical sunset in the model.",
        "Invalid migration-order transitions fail closed.",
        "PQ readiness is measured by effective stake, not validator count.",
    )
    excluded = (
        "No claim that ABSTRACT_PQ_SIGNATURE is a real cryptographic algorithm.",
        "No proof of ML-DSA, SLH-DSA, leanXMSS, leanVM, SNARK/STARK, or other primitive security.",
        "No proof of Ethereum or other production-client correctness, interoperability, liveness, or mainnet readiness.",
        "No claim of production deployment, live staking migration, external validation, certification, or regulatory compliance.",
    )

    return ProofReport(
        proof_status="PASS",
        claim_state="BOUNDED_MODEL_PROOF_OF_POS_MIGRATION_PRESERVATION",
        validator_transition_cases=transition_cases,
        validator_set_cases=set_cases,
        hybrid_double_count_cases=double_count_cases,
        invalid_transition_cases=invalid_cases,
        assumptions=assumptions,
        proven_properties=proven,
        excluded_claims=excluded,
    )
