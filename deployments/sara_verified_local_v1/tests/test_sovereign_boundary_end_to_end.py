from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import _delivery_patch
from worldshepherd_sara.qualification import CapabilityStatus, EvidenceScope
from worldshepherd_sara.sovereign_boundary_authority import (
    OpaBoundDecision,
    OpaPolicyAdapterError,
    OpaPolicyRef,
    OpaRequirements,
    PrimeEffectAuthorizationAssertion,
    PrimeEffectAuthorizationError,
    PrimeEffectAuthorizationVerifier,
    bind_verified_prime_authorization,
    boundary_policy_from_opa,
    canonical_prime_effect_authorization_message,
)
from worldshepherd_sara.sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
    PrimeEffectAuthorizationLedgerError,
    assert_claimed_effect_authorization_usable,
    claim_effect_authorization_registry_patch,
    consumed_effect_authorization_registry_patch,
    verified_effect_authorization_registry_patch,
)
from worldshepherd_sara.sovereign_boundary_kernel import (
    BoundaryAction,
    BoundaryContext,
    BoundaryDomain,
    BoundaryEnvironment,
    BoundaryKernelError,
    BoundaryProvenance,
    BoundaryState,
    ExecutionResultStatus,
    authorize_after_human_approval,
    bind_prime_execution_claim,
    boundary_action_digest,
    create_boundary_envelope,
    queue_boundary_transition,
    record_execution,
    verify_boundary_envelope,
)
from worldshepherd_sara.sovereign_boundary_replay import (
    boundary_transition_events,
    sovereign_boundary_evidence_graph,
)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _lab_action() -> BoundaryAction:
    return BoundaryAction(
        domain=BoundaryDomain.PROGRAMMABLE_BOUNDARY,
        action_type="LAB_VALIDATION_EXPERIMENT",
        resource="lab:bounded-non-operational-demo",
        parameters={
            "test_fixture": "synthetic-command-interface",
            "energy_enabled": False,
            "purpose": "authority-chain-verification",
        },
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.REQUIRES_LAB_VALIDATION,
    )


def _signed_prime_assertion(envelope, *, private_key: Ed25519PrivateKey, key_id: str):
    now = datetime.now(timezone.utc)
    unsigned = PrimeEffectAuthorizationAssertion(
        key_id=key_id,
        authorization_id="PRIME-EFFECT-AUTH-001",
        envelope_id=envelope.envelope_id,
        actor=envelope.actor,
        action_digest=envelope.action_digest,
        effect_scope=envelope.action.effect_scope,
        capability_status=envelope.action.capability_status,
        policy_revision=envelope.policy.policy_revision,
        human_approval_ref=envelope.human_approval_ref,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-effect-auth-0001",
        signature_b64url="unsigned",
    )
    signature = private_key.sign(canonical_prime_effect_authorization_message(unsigned))
    return unsigned.model_copy(update={"signature_b64url": _b64url(signature)})


def test_full_governed_effect_chain_opa_prime_echo_and_replay(tmp_path):
    action = _lab_action()
    opa = OpaBoundDecision(
        decision="escalate",
        reason="physical lab validation requires explicit human approval",
        decision_id="OPA-DECISION-001",
        policy=OpaPolicyRef(
            package="worldshepherd.sbk",
            revision="sha256:policy-revision-demo",
        ),
        requirements=OpaRequirements(human_approval=True),
        action_digest=boundary_action_digest(action),
    )
    policy = boundary_policy_from_opa(opa, action)

    proposed = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(
            environment=BoundaryEnvironment.LAB_TEST,
            mission_id="WS-SBK-E2E-001",
            human_present=True,
            network_state="LOCAL",
        ),
        provenance=BoundaryProvenance(
            agent_version="sbk-e2e-test",
            source_evidence_refs=("WS-QE-LAB-PENDING-001",),
        ),
        policy=policy,
        envelope_id="WS-SBK-E2E-ENVELOPE-001",
    )
    assert proposed.state == BoundaryState.AWAITING_HUMAN_APPROVAL

    human_authorized = authorize_after_human_approval(
        proposed,
        approval_ref="approval:CRE1AWS:e2e-001",
        approver="CRE1AWS",
    )
    assert human_authorized.state == BoundaryState.AUTHORIZED

    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assertion = _signed_prime_assertion(
        human_authorized,
        private_key=private_key,
        key_id="prime-test-key-001",
    )
    verifier = PrimeEffectAuthorizationVerifier(
        public_keys_b64url={"prime-test-key-001": _b64url(public_raw)}
    )
    verified = verifier.verify_for_envelope(assertion, human_authorized)
    prime_bound = bind_verified_prime_authorization(human_authorized, verified)
    assert prime_bound.prime_authorization_ref == "PRIME-EFFECT-AUTH-001"
    assert verify_boundary_envelope(prime_bound) is True

    authorization_registry: dict = {}
    authorization_registry.update(
        verified_effect_authorization_registry_patch(authorization_registry, verified)
    )
    execution_id = "WS-SBK-EXECUTION-001"
    authorization_registry.update(
        claim_effect_authorization_registry_patch(
            authorization_registry,
            authorization_id=verified.authorization_id,
            envelope=prime_bound,
            execution_id=execution_id,
        )
    )
    claimed = bind_prime_execution_claim(prime_bound, execution_id=execution_id)
    assert_claimed_effect_authorization_usable(
        authorization_registry,
        authorization_id=verified.authorization_id,
        envelope=claimed,
        execution_id=execution_id,
    )

    completed = record_execution(
        claimed,
        runtime_action=action,
        status=ExecutionResultStatus.SUCCEEDED,
        outcome_ref="lab-record:non-operational-authority-chain-001",
        evidence_refs=("echo:e2e:execution-001",),
    )
    assert completed.state == BoundaryState.EXECUTED
    assert verify_boundary_envelope(completed) is True

    authorization_registry.update(
        consumed_effect_authorization_registry_patch(
            authorization_registry,
            authorization_id=verified.authorization_id,
            execution_id=execution_id,
            terminal_envelope=completed,
        )
    )
    ledger_entry = authorization_registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][verified.authorization_id]
    assert ledger_entry["status"] == "CONSUMED"
    assert ledger_entry["terminal_envelope_digest"] == completed.envelope_digest

    with pytest.raises(PrimeEffectAuthorizationLedgerError, match="not claimable"):
        claim_effect_authorization_registry_patch(
            authorization_registry,
            authorization_id=verified.authorization_id,
            envelope=prime_bound,
            execution_id="WS-SBK-REPLAY-ATTEMPT",
        )

    registry_patch, event_id = queue_boundary_transition({}, completed)
    _delivered_patch, audit = _delivery_patch(registry_patch, event_id=event_id)
    assert audit.payload["_outbox_event_id"] == event_id
    assert audit.payload["_delivery_semantics"] == "AT_LEAST_ONCE"
    assert "parameters" not in audit.payload
    assert audit.payload["prime_authorization_ref"] == "PRIME-EFFECT-AUTH-001"
    assert audit.payload["prime_execution_claim_ref"] == execution_id

    store = EchoEventStore(tmp_path / "echo")
    first = store.ingest(audit)
    second = store.ingest(audit)
    assert first.outcome == "STORED"
    assert second.outcome == "DEDUPLICATED"
    assert second.record.delivery_count == 2
    reconciliation = store.reconcile([audit])
    assert reconciliation["counts"] == {"MATCHED": 1}
    assert store.health()["ok"] is True

    replay = boundary_transition_events(
        [proposed, human_authorized, prime_bound, claimed, completed]
    )
    assert [event.sequence for event in replay] == [1, 2, 3, 4, 5]
    assert replay[-1].payload["state"] == "EXECUTED"

    graph = sovereign_boundary_evidence_graph(
        graph_id="WS-SBK-E2E-GRAPH-001",
        envelopes=[completed],
    )
    node_types = {node.node_type for node in graph.nodes}
    assert {
        "sbk_bound_action",
        "sbk_policy_decision",
        "sbk_envelope",
        "human_approval",
        "prime_sentinel_authorization",
        "sbk_execution_result",
    }.issubset(node_types)
    assert any(edge.relation == "purpose_bound_authorization" for edge in graph.edges)


def test_opa_action_digest_mismatch_fails_closed():
    action = _lab_action()
    decision = OpaBoundDecision(
        decision="allow",
        reason="test",
        decision_id="OPA-MISMATCH-001",
        policy=OpaPolicyRef(package="worldshepherd.sbk", revision="rev-1"),
        action_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(OpaPolicyAdapterError, match="action_digest"):
        boundary_policy_from_opa(decision, action)


def test_prime_signature_is_purpose_bound_to_exact_envelope_and_action():
    action = _lab_action()
    decision = OpaBoundDecision(
        decision="escalate",
        reason="human gate",
        decision_id="OPA-DECISION-002",
        policy=OpaPolicyRef(package="worldshepherd.sbk", revision="rev-2"),
        requirements=OpaRequirements(human_approval=True),
        action_digest=boundary_action_digest(action),
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
        provenance=BoundaryProvenance(agent_version="test"),
        policy=boundary_policy_from_opa(decision, action),
        envelope_id="WS-SBK-E2E-ENVELOPE-002",
    )
    envelope = authorize_after_human_approval(
        envelope,
        approval_ref="approval:002",
        approver="CRE1AWS",
    )

    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assertion = _signed_prime_assertion(
        envelope,
        private_key=private_key,
        key_id="prime-test-key-002",
    )
    verifier = PrimeEffectAuthorizationVerifier(
        public_keys_b64url={"prime-test-key-002": _b64url(public_raw)}
    )

    changed = envelope.model_copy(update={"actor": "DIFFERENT-ACTOR", "envelope_digest": None})
    from worldshepherd_sara.qualification import canonical_digest

    changed = changed.model_copy(
        update={
            "envelope_digest": canonical_digest(
                changed.model_dump(mode="json", exclude={"envelope_digest"})
            )
        }
    )
    with pytest.raises(PrimeEffectAuthorizationError, match="binding mismatch"):
        verifier.verify_for_envelope(assertion, changed)


def test_physical_execution_without_prime_binding_fails_even_after_human_approval():
    action = _lab_action()
    opa = OpaBoundDecision(
        decision="escalate",
        reason="physical action",
        decision_id="OPA-DECISION-003",
        policy=OpaPolicyRef(package="worldshepherd.sbk", revision="rev-3"),
        requirements=OpaRequirements(human_approval=True),
        action_digest=boundary_action_digest(action),
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
        provenance=BoundaryProvenance(agent_version="test"),
        policy=boundary_policy_from_opa(opa, action),
    )
    envelope = authorize_after_human_approval(
        envelope,
        approval_ref="approval:003",
        approver="CRE1AWS",
    )

    with pytest.raises(BoundaryKernelError, match="PRIME authorization"):
        record_execution(
            envelope,
            runtime_action=action,
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="should-not-execute",
        )
