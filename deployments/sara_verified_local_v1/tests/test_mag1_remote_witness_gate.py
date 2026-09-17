from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.mag1_prime_binding import PRIME_MAG1_ACTION
from worldshepherd_sara.mag1_prime_transition import (
    PrimeMag1TransitionDisposition,
    PrimeMag1TransitionError,
    execute_prime_requalification_transition,
    get_prime_custody_record,
    prime_custody_registry_patch,
)
from worldshepherd_sara.prime_configuration_custody import (
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
    REQUALIFICATION_CHECKS,
)
from worldshepherd_sara.prime_sentinel_authorization import (
    PRIME_SENTINEL_AUTHZ_REGISTRY_KEY,
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelVerifier,
    canonical_authorization_message,
    verified_authorization_registry_patch,
)
from worldshepherd_sara.registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryMonotonicWitnessClient,
    RegistryMonotonicWitnessVerifier,
    RegistryWitnessCoordinates,
)
from worldshepherd_sara.registry_witness_gate import (
    RegistryWitnessGateError,
    RegistryWitnessPrecondition,
    RegistryWitnessPreconditionStale,
    assert_registry_witness_precondition,
    prepare_registry_witness_precondition,
)
from worldshepherd_sara.registry_witness_service import RegistryWitnessLedger
from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.trajectory_guard import TrajectoryState


NOW = datetime(2026, 9, 17, 22, 0, tzinfo=timezone.utc)
PRIME_ID = "PRIME-MAG16R"
AUTH_ID = "AUTH-MAG16R-001"
PRIME_KEY_ID = "PS-MAG16R"
WITNESS_ID = "WITNESS-MAG16R"
WITNESS_KEY_ID = "WITNESS-MAG16R-KEY"
NAMESPACE = "worldshepherd/sara/registry"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class _LedgerTransport:
    witness_mode = REMOTE_WITNESS_MODE

    def __init__(self, ledger: RegistryWitnessLedger):
        self.ledger = ledger

    def _namespace(self, namespace: str) -> None:
        if namespace != self.ledger.namespace:
            raise ValueError("unexpected witness namespace")

    def read_head(self, namespace: str):
        self._namespace(namespace)
        return self.ledger.read_head()

    def witness(self, namespace: str, coordinates: RegistryWitnessCoordinates):
        self._namespace(namespace)
        return self.ledger.witness(coordinates)


def _prime_material():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            PRIME_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        }
    )
    draft = PrimeSentinelAuthorizationAssertion(
        key_id=PRIME_KEY_ID,
        authorization_id=AUTH_ID,
        prime_id=PRIME_ID,
        target_environment=PrimeEnvironment.SPACE,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
        nonce="mag16r-prime-authorization-nonce-0001",
        signature_b64url=_b64url(b"0" * 64),
    )
    assertion = draft.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_authorization_message(draft))
            )
        }
    )
    return verifier, assertion


def _setup(tmp_path):
    verifier, assertion = _prime_material()
    verified = verifier.verify(assertion, now=NOW)
    store = DurableStore(tmp_path / "sara")
    store.patch_registry(verified_authorization_registry_patch({}, verified))
    custody = PrimeConfigurationCustodyRecord(
        prime_id=PRIME_ID,
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )
    store.patch_registry(prime_custody_registry_patch(store.get_registry(), custody))

    witness_private = Ed25519PrivateKey.generate()
    ledger = RegistryWitnessLedger(
        tmp_path / "witness" / "witness.db",
        private_key=witness_private,
        witness_id=WITNESS_ID,
        key_id=WITNESS_KEY_ID,
        namespace=NAMESPACE,
    )
    witness_verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            WITNESS_KEY_ID: _b64url(
                witness_private.public_key().public_bytes_raw()
            )
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=NAMESPACE,
    )
    witness_client = RegistryMonotonicWitnessClient(
        transport=_LedgerTransport(ledger),
        verifier=witness_verifier,
    )
    return store, verifier, assertion, witness_client


def _execute(store, verifier, assertion, **overrides):
    values = dict(
        assertion=assertion,
        verifier=verifier,
        pack=PrimeMissionPackEvidence(
            pack_id="SPACE-PACK-MAG16R",
            target_environment=PrimeEnvironment.SPACE,
            authenticated=True,
            compatible_with_prime=True,
            target_environment_qualification_valid=True,
        ),
        candidate=AutonomousActionCandidate(
            action_id="ACT-MAG16R",
            action_type=PRIME_MAG1_ACTION,
            confidence=1.0,
            requested_authority=1,
            reversible=True,
        ),
        autonomy_policy=AutonomyPolicy(
            policy_id="POL-MAG16R",
            allowed_auto_action_types=[PRIME_MAG1_ACTION],
            minimum_auto_confidence=0.99,
            maximum_auto_authority=1,
        ),
        trajectory_state=TrajectoryState(
            trajectory_id="TRJ-MAG16R",
            originating_human_request_hash="sha256:mag16r-request",
            root_authority="PRIME_SENTINEL",
        ),
        trajectory_action_id="ACT-MAG16R",
        now=NOW,
    )
    values.update(overrides)
    return execute_prime_requalification_transition(store, **values)


def _witness_current(store, witness_client):
    assessment = witness_client.advance_and_verify(store.checkpoint_status())
    assert assessment["status"] == "PASS"
    return prepare_registry_witness_precondition(store, witness_client)


def test_exact_witness_precondition_allows_release_and_is_bound_into_evidence(tmp_path):
    store, verifier, assertion, witness_client = _setup(tmp_path)
    precondition = _witness_current(store, witness_client)
    assert precondition.witness_mode == REMOTE_WITNESS_MODE
    assert_registry_witness_precondition(
        store.get_registry(),
        precondition,
        verifier=witness_client.verifier,
    )

    result = _execute(
        store,
        verifier,
        assertion,
        registry_witness_precondition=precondition,
        registry_witness_verifier=witness_client.verifier,
    )

    assert result.disposition == PrimeMag1TransitionDisposition.APPLIED
    assert result.registry_witness_receipt_sha256 == precondition.witness_receipt_sha256
    assert result.registry_witness_precondition_sha256 is not None

    registry = store.get_registry()
    assert registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTH_ID]["status"] == "CONSUMED"
    assert get_prime_custody_record(
        registry,
        prime_id=PRIME_ID,
    ).state == PrimeCustodyState.READY

    transition = registry[EVENT_OUTBOX_REGISTRY_KEY][result.transition_event_id]
    payload = transition["payload"]
    assert payload["registry_witness_required"] is True
    assert payload["registry_witness_receipt_sha256"] == precondition.witness_receipt_sha256
    assert payload["registry_witness_precondition_sha256"] == result.registry_witness_precondition_sha256
    assert payload["registry_witness_independence_verified"] is False
    assert payload["registry_witness_post_transition_covered"] is False


def test_intervening_registry_change_makes_precondition_stale_and_preserves_authority(tmp_path):
    store, verifier, assertion, witness_client = _setup(tmp_path)
    precondition = _witness_current(store, witness_client)

    store.patch_registry({"INTERVENING_SECURITY_STATE": "CHANGED"})
    before_attempt = store.get_registry()

    with pytest.raises(
        RegistryWitnessPreconditionStale,
        match="registry changed after witness verification",
    ):
        _execute(
            store,
            verifier,
            assertion,
            registry_witness_precondition=precondition,
            registry_witness_verifier=witness_client.verifier,
        )

    after = store.get_registry()
    assert after == before_attempt
    assert after[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTH_ID]["status"] == "VERIFIED"
    assert get_prime_custody_record(
        after,
        prime_id=PRIME_ID,
    ).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION


def test_witness_is_mandatory_without_caller_selectable_opt_out(tmp_path):
    store, verifier, assertion, _witness_client = _setup(tmp_path)
    before = store.get_registry()

    with pytest.raises(
        PrimeMag1TransitionError,
        match="witness precondition is mandatory",
    ):
        _execute(store, verifier, assertion)

    assert store.get_registry() == before
    assert store.get_registry()[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTH_ID]["status"] == "VERIFIED"


def test_precondition_requires_pinned_verifier_even_when_receipt_is_present(tmp_path):
    store, verifier, assertion, witness_client = _setup(tmp_path)
    precondition = _witness_current(store, witness_client)
    before = store.get_registry()

    with pytest.raises(
        PrimeMag1TransitionError,
        match="pinned registry witness verifier is mandatory",
    ):
        _execute(
            store,
            verifier,
            assertion,
            registry_witness_precondition=precondition,
        )

    assert store.get_registry() == before


def test_tampered_embedded_signed_receipt_fails_closed(tmp_path):
    store, verifier, assertion, witness_client = _setup(tmp_path)
    precondition = _witness_current(store, witness_client)
    receipt = precondition.receipt()
    receipt["state_root_sha256"] = "f" * 64
    tampered = RegistryWitnessPrecondition(
        generation=precondition.generation,
        state_root_sha256=precondition.state_root_sha256,
        commit_hash=precondition.commit_hash,
        witness_id=precondition.witness_id,
        witness_mode=precondition.witness_mode,
        witness_receipt_sha256=precondition.witness_receipt_sha256,
        witness_receipt_json=json.dumps(receipt, sort_keys=True, separators=(",", ":")),
    )
    before = store.get_registry()

    with pytest.raises(
        RegistryWitnessGateError,
        match="pinned-key verification",
    ):
        _execute(
            store,
            verifier,
            assertion,
            registry_witness_precondition=tampered,
            registry_witness_verifier=witness_client.verifier,
        )

    assert store.get_registry() == before
    assert store.get_registry()[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTH_ID]["status"] == "VERIFIED"


def test_precondition_evidence_never_claims_independence_or_post_transition_coverage(tmp_path):
    store, _verifier, _assertion, witness_client = _setup(tmp_path)
    precondition = _witness_current(store, witness_client)
    evidence = precondition.evidence()

    assert evidence["signed_receipt_embedded"] is True
    assert evidence["verification_required_at_use"] is True
    assert evidence["external_witnessed"] is False
    assert evidence["independence_verified"] is False
    assert "post-transition checkpoint coverage" in evidence["claims_boundary"]
