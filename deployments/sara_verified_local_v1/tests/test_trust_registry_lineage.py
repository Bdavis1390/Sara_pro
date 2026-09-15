from __future__ import annotations

from worldshepherd_sara.trust_registry import TrustKeyRecord, build_trust_registry
from worldshepherd_sara.trust_registry_lineage import (
    build_registry_anchor,
    build_registry_checkpoint,
    build_registry_revision,
    verify_registry_lineage,
    verify_registry_transition,
)


def _entry(
    key_id: str,
    status: str,
    *,
    valid_from_utc: str = "2026-09-01T00:00:00Z",
    valid_until_utc: str | None = None,
    revoked_utc: str | None = None,
    successor_key_id: str | None = None,
) -> TrustKeyRecord:
    return TrustKeyRecord(
        signer_id="worldshepherd-test-signer",
        key_id=key_id,
        algorithm="HMAC-SHA256-TEST",
        status=status,
        valid_from_utc=valid_from_utc,
        valid_until_utc=valid_until_utc,
        revoked_utc=revoked_utc,
        successor_key_id=successor_key_id,
    )


def _registry(generated_utc: str, entries: list[TrustKeyRecord]):
    return build_trust_registry(
        registry_id="trust-registry-v1",
        generated_utc=generated_utc,
        entries=entries,
    )


def _valid_lineage():
    first = _registry(
        "2026-09-10T00:00:00Z",
        [_entry("key-a", "ACTIVE")],
    )
    second = _registry(
        "2026-09-11T00:00:00Z",
        [
            _entry(
                "key-a",
                "RETIRED",
                valid_until_utc="2026-09-10T23:59:59Z",
                successor_key_id="key-b",
            ),
            _entry("key-b", "ACTIVE", valid_from_utc="2026-09-11T00:00:00Z"),
        ],
    )
    third = _registry(
        "2026-09-12T00:00:00Z",
        [
            _entry(
                "key-a",
                "RETIRED",
                valid_until_utc="2026-09-10T23:59:59Z",
                successor_key_id="key-b",
            ),
            _entry("key-b", "ACTIVE", valid_from_utc="2026-09-11T00:00:00Z"),
        ],
    )

    r0, anchor = build_registry_anchor(first)
    r1 = build_registry_revision(second, sequence=1, previous_revision=r0)
    r2 = build_registry_revision(third, sequence=2, previous_revision=r1)
    return first, second, third, r0, r1, r2, anchor


def test_registry_lineage_accepts_valid_rotation_and_checkpoint():
    first, second, third, r0, r1, r2, anchor = _valid_lineage()
    checkpoint = build_registry_checkpoint(anchor=anchor, revision=r2)

    assert verify_registry_transition(first, second)
    assert verify_registry_transition(second, third)
    assert verify_registry_lineage(
        [first, second, third],
        [r0, r1, r2],
        anchor=anchor,
        required_checkpoint=checkpoint,
    )


def test_registry_lineage_rejects_removed_historical_identity():
    first, second, _, r0, r1, _, anchor = _valid_lineage()
    removed = _registry(
        "2026-09-12T00:00:00Z",
        [_entry("key-b", "ACTIVE", valid_from_utc="2026-09-11T00:00:00Z")],
    )
    r2 = build_registry_revision(removed, sequence=2, previous_revision=r1)

    assert not verify_registry_transition(second, removed)
    assert not verify_registry_lineage([first, second, removed], [r0, r1, r2], anchor=anchor)


def test_registry_lineage_rejects_resurrection_of_retired_or_revoked_key():
    retired = _registry(
        "2026-09-11T00:00:00Z",
        [_entry("key-a", "RETIRED", valid_until_utc="2026-09-10T23:59:59Z")],
    )
    resurrected = _registry(
        "2026-09-12T00:00:00Z",
        [_entry("key-a", "ACTIVE")],
    )
    assert not verify_registry_transition(retired, resurrected)

    revoked = _registry(
        "2026-09-11T00:00:00Z",
        [_entry("key-a", "REVOKED", revoked_utc="2026-09-11T00:00:00Z")],
    )
    assert not verify_registry_transition(revoked, resurrected)


def test_registry_lineage_rejects_rewrite_of_retired_metadata():
    retired = _registry(
        "2026-09-11T00:00:00Z",
        [
            _entry(
                "key-a",
                "RETIRED",
                valid_until_utc="2026-09-10T23:59:59Z",
                successor_key_id="key-b",
            )
        ],
    )
    rewritten = _registry(
        "2026-09-12T00:00:00Z",
        [
            _entry(
                "key-a",
                "RETIRED",
                valid_until_utc="2026-09-09T23:59:59Z",
                successor_key_id="key-c",
            )
        ],
    )
    assert not verify_registry_transition(retired, rewritten)


def test_registry_lineage_rejects_non_monotonic_registry_time():
    current = _registry("2026-09-12T00:00:00Z", [_entry("key-a", "ACTIVE")])
    stale = _registry("2026-09-11T00:00:00Z", [_entry("key-a", "ACTIVE")])
    assert not verify_registry_transition(current, stale)


def test_checkpoint_detects_registry_history_rollback_or_fork():
    first, second, third, r0, r1, r2, anchor = _valid_lineage()
    checkpoint = build_registry_checkpoint(anchor=anchor, revision=r2)

    assert not verify_registry_lineage(
        [first, second],
        [r0, r1],
        anchor=anchor,
        required_checkpoint=checkpoint,
    )

    forked = _registry(
        "2026-09-12T00:00:00Z",
        [
            _entry(
                "key-a",
                "REVOKED",
                valid_until_utc="2026-09-10T23:59:59Z",
                revoked_utc="2026-09-12T00:00:00Z",
                successor_key_id="key-b",
            ),
            _entry("key-b", "ACTIVE", valid_from_utc="2026-09-11T00:00:00Z"),
        ],
    )
    fork_r2 = build_registry_revision(forked, sequence=2, previous_revision=r1)
    assert not verify_registry_lineage(
        [first, second, forked],
        [r0, r1, fork_r2],
        anchor=anchor,
        required_checkpoint=checkpoint,
    )
