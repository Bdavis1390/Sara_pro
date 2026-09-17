"""Fail-closed replay/freshness state for canonical PQ signing contexts.

The canonical signing context binds replay_sequence, key_epoch, policy_version,
and envelope_version into the signed commitment.  Binding alone is insufficient:
a verifier must also remember what it has already accepted.  This module models
that monotonic acceptance state without signing transactions, moving value, or
authorizing execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from security.qcrypto.canonical_pq_signing_context import CanonicalSigningContextDecision

U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1


@dataclass(frozen=True)
class ReplayFreshnessPolicy:
    maximum_validity_seconds: int = 3600
    maximum_clock_skew_seconds: int = 60
    require_strict_sequence_increment: bool = True


@dataclass(frozen=True)
class ReplayCheckpoint:
    network_id: str
    authority_id: str
    replay_domain: str
    highest_replay_sequence: int
    highest_key_epoch: int
    highest_policy_version: int
    highest_envelope_version: int
    last_context_digest: str


@dataclass(frozen=True)
class ReplayCandidate:
    context: CanonicalSigningContextDecision
    valid_from_epoch_seconds: int
    valid_until_epoch_seconds: int
    observed_at_epoch_seconds: int


@dataclass(frozen=True)
class ReplayFreshnessDecision:
    verdict: str
    accepted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    next_checkpoint: ReplayCheckpoint | None
    duplicate_context: bool = False
    replay_sequence_advanced: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False
    transaction_authorized: bool = False
    claim_boundary: str = (
        "Replay/freshness policy result only; acceptance means the canonical context "
        "passes modeled monotonic-state checks. It does not verify a signature, "
        "authorize execution, authorize live value, or establish protocol conformance."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        if self.next_checkpoint is not None:
            data["next_checkpoint"] = asdict(self.next_checkpoint)
        return data


def _parse_uint_field(fields: dict[str, str], name: str, maximum: int) -> tuple[int | None, str | None]:
    raw = fields.get(name)
    if raw is None:
        return None, f"Canonical context is missing {name}."
    if not raw.isdigit():
        return None, f"Canonical context field {name} must be unsigned decimal text."
    value = int(raw)
    if value > maximum:
        return None, f"Canonical context field {name} exceeds its supported range."
    return value, None


def _validate_epoch_seconds(name: str, value: int) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return f"{name} must be an integer epoch-seconds value."
    if value < 0 or value > U64_MAX:
        return f"{name} must be in the inclusive range 0..{U64_MAX}."
    return None


def assess_replay_freshness(
    candidate: ReplayCandidate,
    policy: ReplayFreshnessPolicy,
    checkpoint: ReplayCheckpoint | None = None,
) -> ReplayFreshnessDecision:
    """Evaluate one canonical context against freshness and monotonic replay state."""

    blockers: list[str] = []
    warnings: list[str] = []
    context = candidate.context

    if not context.ready or not context.context_digest:
        blockers.append("Canonical signing context is not ready.")
    if not context.canonical_fields:
        blockers.append("Canonical signing context has no canonical fields.")

    if isinstance(policy.maximum_validity_seconds, bool) or policy.maximum_validity_seconds <= 0:
        blockers.append("maximum_validity_seconds must be a positive integer.")
    if isinstance(policy.maximum_clock_skew_seconds, bool) or policy.maximum_clock_skew_seconds < 0:
        blockers.append("maximum_clock_skew_seconds must be a non-negative integer.")

    for name, value in (
        ("valid_from_epoch_seconds", candidate.valid_from_epoch_seconds),
        ("valid_until_epoch_seconds", candidate.valid_until_epoch_seconds),
        ("observed_at_epoch_seconds", candidate.observed_at_epoch_seconds),
    ):
        error = _validate_epoch_seconds(name, value)
        if error:
            blockers.append(error)

    fields = context.canonical_fields
    network_id = fields.get("network_id")
    authority_id = fields.get("authority_id")
    replay_domain = fields.get("replay_domain")
    for name, value in (
        ("network_id", network_id),
        ("authority_id", authority_id),
        ("replay_domain", replay_domain),
    ):
        if not value:
            blockers.append(f"Canonical context is missing {name}.")

    replay_sequence, error = _parse_uint_field(fields, "replay_sequence", U64_MAX)
    if error:
        blockers.append(error)
    key_epoch, error = _parse_uint_field(fields, "key_epoch", U64_MAX)
    if error:
        blockers.append(error)
    policy_version, error = _parse_uint_field(fields, "policy_version", U32_MAX)
    if error:
        blockers.append(error)
    envelope_version, error = _parse_uint_field(fields, "envelope_version", U32_MAX)
    if error:
        blockers.append(error)

    if not blockers:
        validity = candidate.valid_until_epoch_seconds - candidate.valid_from_epoch_seconds
        if validity <= 0:
            blockers.append("Validity window must have positive duration.")
        elif validity > policy.maximum_validity_seconds:
            blockers.append("Validity window exceeds the governed maximum duration.")

        earliest = candidate.valid_from_epoch_seconds - policy.maximum_clock_skew_seconds
        latest = candidate.valid_until_epoch_seconds + policy.maximum_clock_skew_seconds
        if candidate.observed_at_epoch_seconds < earliest:
            blockers.append("Canonical context is not yet valid at the observed time.")
        if candidate.observed_at_epoch_seconds > latest:
            blockers.append("Canonical context has expired at the observed time.")

    duplicate = False
    advanced = False
    if checkpoint is not None and not blockers:
        if checkpoint.network_id != network_id:
            blockers.append("Checkpoint network id does not match canonical context.")
        if checkpoint.authority_id != authority_id:
            blockers.append("Checkpoint authority id does not match canonical context.")
        if checkpoint.replay_domain != replay_domain:
            blockers.append("Checkpoint replay domain does not match canonical context.")

        duplicate = checkpoint.last_context_digest == context.context_digest
        if duplicate:
            blockers.append("Duplicate canonical context digest rejected as replay.")

        assert replay_sequence is not None
        assert key_epoch is not None
        assert policy_version is not None
        assert envelope_version is not None

        if policy.require_strict_sequence_increment:
            if replay_sequence != checkpoint.highest_replay_sequence + 1:
                blockers.append("Replay sequence must advance by exactly one.")
        elif replay_sequence <= checkpoint.highest_replay_sequence:
            blockers.append("Replay sequence must advance monotonically.")

        if key_epoch < checkpoint.highest_key_epoch:
            blockers.append("Key epoch rollback rejected by replay checkpoint.")
        if policy_version < checkpoint.highest_policy_version:
            blockers.append("Policy version rollback rejected by replay checkpoint.")
        if envelope_version < checkpoint.highest_envelope_version:
            blockers.append("Envelope version rollback rejected by replay checkpoint.")

        advanced = replay_sequence > checkpoint.highest_replay_sequence

    if blockers:
        if duplicate:
            verdict = "REPLAY_DUPLICATE_REJECTED"
        elif any("expired" in item.lower() or "not yet valid" in item.lower() for item in blockers):
            verdict = "FRESHNESS_REJECTED"
        elif any("rollback" in item.lower() for item in blockers):
            verdict = "MONOTONIC_STATE_ROLLBACK_REJECTED"
        elif any("Replay sequence" in item for item in blockers):
            verdict = "REPLAY_SEQUENCE_REJECTED"
        else:
            verdict = "REPLAY_FRESHNESS_BLOCKED"
        return ReplayFreshnessDecision(
            verdict=verdict,
            accepted=False,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            next_checkpoint=None,
            duplicate_context=duplicate,
            replay_sequence_advanced=advanced,
        )

    assert network_id is not None
    assert authority_id is not None
    assert replay_domain is not None
    assert replay_sequence is not None
    assert key_epoch is not None
    assert policy_version is not None
    assert envelope_version is not None
    assert context.context_digest is not None

    next_checkpoint = ReplayCheckpoint(
        network_id=network_id,
        authority_id=authority_id,
        replay_domain=replay_domain,
        highest_replay_sequence=replay_sequence,
        highest_key_epoch=key_epoch,
        highest_policy_version=policy_version,
        highest_envelope_version=envelope_version,
        last_context_digest=context.context_digest,
    )
    return ReplayFreshnessDecision(
        verdict="REPLAY_FRESHNESS_ACCEPTED",
        accepted=True,
        blockers=(),
        warnings=tuple(warnings),
        next_checkpoint=next_checkpoint,
        duplicate_context=False,
        replay_sequence_advanced=checkpoint is None or advanced,
    )
