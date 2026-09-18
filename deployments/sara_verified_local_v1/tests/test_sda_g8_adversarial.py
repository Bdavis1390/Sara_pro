from __future__ import annotations

import base64
import json
import math
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from worldshepherd_sara import sda_ddil_release as ddil_module
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.sda import (
    SdaContractValidationState,
    SdaIngestDisposition,
    SdaInterfaceContract,
    SdaObservation,
    SdaSourceClass,
    SdaSourceIdentity,
    evaluate_sda_ingest,
)
from worldshepherd_sara.sda_adapter_isolation import (
    SdaAdapterIsolationError,
    SdaAdapterIsolationPolicy,
    SdaAdapterRunStatus,
    run_isolated_adapter,
)
from worldshepherd_sara.sda_canonical import (
    SdaCanonicalEnvelope,
    SdaCanonicalStateVector,
    SdaCanonicalTimeTag,
    SdaObjectIdentity,
)
from worldshepherd_sara.sda_ccsds import (
    CcsdsKvnProfileError,
    parse_opm_v3_kvn_profile,
    parse_tdm_v2_range_kvn_profile,
)
from worldshepherd_sara.sda_ddil_release import (
    SdaDdilConflict,
    SdaDdilJournalFull,
    SdaDdilReleaseJournal,
    SdaDdilReleaseRecord,
    ddil_records_to_mission_events,
    reconcile_release_records,
    sda_ddil_release_audit_record,
)
from worldshepherd_sara.sda_hypothesis import (
    SdaHypothesisError,
    build_state_hypothesis_set,
)
from worldshepherd_sara.sda_identity import (
    SdaWorkloadIdentityAssertion,
    canonical_sda_workload_identity_message,
    verify_sda_workload_identity,
)
from worldshepherd_sara.sda_release_authorization import (
    SdaReleaseAuthorizationAssertion,
    SdaReleaseCandidate,
    SdaReleaseReceipt,
    canonical_sda_release_message,
    consume_sda_release_authorization,
    verify_sda_release_authorization,
)
from worldshepherd_sara.sda_transport_identity import SdaTransportIdentity


ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads(
    (ROOT / "fixtures" / "ws_sda_g8_adversarial_corpus_v1.json").read_text(
        encoding="utf-8"
    )
)
NOW = datetime(2026, 9, 18, 2, 0, tzinfo=timezone.utc)
KEY_ID = "G8-WORKLOAD-K1"
RELEASE_KEY_ID = "G8-RELEASE-K1"
WORKLOAD_ID = "spiffe://worldshepherd.internal/sda/adapter/g8"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _covariance(position_variance: float = 1.0, velocity_variance: float = 0.01):
    matrix = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(3):
        matrix[index][index] = position_variance
    for index in range(3, 6):
        matrix[index][index] = velocity_variance
    return matrix


def _g1_contract(**overrides) -> SdaInterfaceContract:
    values = {
        "contract_id": "G8-SDA-CONTRACT",
        "source_id": "G8-SOURCE",
        "adapter_id": "G8-ADAPTER",
        "adapter_version": "1.0.0",
        "authoritative_spec_ref": "internal://g8",
        "authoritative_spec_digest": "sha256:" + "b" * 64,
        "allowed_reference_frames": ["GCRF"],
        "allowed_releasability_tags": ["US_ONLY"],
        "max_age_seconds": 600.0,
        "max_future_skew_seconds": 30.0,
        "max_clock_uncertainty_seconds": 0.05,
        "validation_state": SdaContractValidationState.SYNTHETIC,
        "validation_ref": "test://g8",
        "enabled": True,
    }
    values.update(overrides)
    return SdaInterfaceContract.model_validate(values)


def _g1_observation(active: SdaInterfaceContract, **overrides) -> SdaObservation:
    values = {
        "observation_id": "G8-OBS-001",
        "source_event_id": "G8-EVENT-001",
        "source_sequence": 1,
        "source": SdaSourceIdentity(
            source_id="G8-SOURCE",
            source_class=SdaSourceClass.SYNTHETIC,
            provider="G8 synthetic",
            sensor_id="G8-SENSOR",
            adapter_id="G8-ADAPTER",
            adapter_version="1.0.0",
        ),
        "observed_at": NOW,
        "received_at": NOW + timedelta(seconds=1),
        "time_system": "UTC",
        "clock_uncertainty_seconds": 0.01,
        "reference_frame": "GCRF",
        "position_km": (1.0, 2.0, 3.0),
        "velocity_km_s": (0.1, 0.2, 0.3),
        "covariance_6x6": _covariance(),
        "measurement_confidence": 0.8,
        "source_reliability": 0.8,
        "handling_label": "UNCLASSIFIED_SYNTHETIC",
        "releasability_tags": ["US_ONLY"],
        "raw_source_digest": "sha256:" + "a" * 64,
        "interface_contract_id": active.contract_id,
        "interface_contract_digest": active.digest(),
        "transformation_refs": ["g8"],
    }
    values.update(overrides)
    return SdaObservation.model_validate(values)


def _workload_materials():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={KEY_ID: _b64url(private.public_key().public_bytes_raw())}
    )
    return private, verifier


def _signed_workload(
    private: Ed25519PrivateKey,
    *,
    adapter_id: str = "G8-ADAPTER",
    issued_at: datetime = NOW - timedelta(seconds=5),
    expires_at: datetime = NOW + timedelta(minutes=2),
    transport_digest: str = "sha256:" + "d" * 64,
):
    unsigned = SdaWorkloadIdentityAssertion(
        key_id=KEY_ID,
        workload_id=WORKLOAD_ID,
        source_id="G8-SOURCE",
        adapter_id=adapter_id,
        adapter_version="1.0.0",
        transport_cert_sha256=transport_digest,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce="g8-workload-nonce-0001",
        signature_b64url="placeholder",
    )
    return unsigned.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_sda_workload_identity_message(unsigned))
            )
        }
    )


def _g3_policy(**overrides):
    values = {
        "policy_id": "G8-G3-POLICY",
        "adapter_id": "G8-ADAPTER",
        "adapter_version": "1.0.0",
        "executable_path": sys.executable,
        "max_input_bytes": 1024,
        "max_output_bytes": 128,
        "max_stderr_bytes": 128,
        "timeout_seconds": 0.5,
        "cpu_seconds": 2,
        "memory_limit_bytes": 256 * 1024 * 1024,
        "max_open_files": 32,
        "allow_exit_codes": [0],
    }
    values.update(overrides)
    return SdaAdapterIsolationPolicy.model_validate(values)


OPM = """\
CCSDS_OPM_VERS = 3.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
OBJECT_NAME = G8-OBJECT
OBJECT_ID = 2026-999A
CENTER_NAME = EARTH
REF_FRAME = GCRF
TIME_SYSTEM = UTC
EPOCH = 2026-09-18T00:00:01
X = 7000.0 [km]
Y = 0.0 [km]
Z = 0.0 [km]
X_DOT = 0.0 [km/s]
Y_DOT = 7.5 [km/s]
Z_DOT = 0.0 [km/s]
"""

TDM = """\
CCSDS_TDM_VERS = 2.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
META_START
TIME_SYSTEM = UTC
PARTICIPANT_1 = G8-STATION
PARTICIPANT_2 = G8-OBJECT
MODE = SEQUENTIAL
PATH = 1,2,1
RANGE_UNITS = km
META_STOP
DATA_START
RANGE = 2026-09-18T00:00:01 1234.5
DATA_STOP
"""


def _g5_envelope(
    observation_id: str,
    x_km: float,
    *,
    object_id: str = "2026-999A",
    epoch: str = "2026-09-18T02:00:00",
    frame: str = "GCRF",
) -> SdaCanonicalEnvelope:
    return SdaCanonicalEnvelope(
        observation_id=observation_id,
        source_event_id="EVENT-" + observation_id,
        source_sequence=int(observation_id.rsplit("-", 1)[-1]),
        source=SdaSourceIdentity(
            source_id="SRC-" + observation_id,
            source_class=SdaSourceClass.SYNTHETIC,
            provider="G8",
            sensor_id="SENSOR-" + observation_id,
            adapter_id="G8-G5",
            adapter_version="1.0.0",
        ),
        object_identity=SdaObjectIdentity(
            object_id=object_id,
            object_name="G8-OBJECT",
            center_name="EARTH",
        ),
        time_tag=SdaCanonicalTimeTag(
            raw=epoch,
            time_system="UTC",
            normalized_utc=NOW,
        ),
        received_at=NOW,
        payload=SdaCanonicalStateVector(
            reference_frame=frame,
            position_km=(x_km, 0.0, 0.0),
            velocity_km_s=(0.0, 0.0, 0.0),
            covariance_6x6=_covariance(1.0, 1.0),
            covariance_reference_frame=frame,
            covariance_source_ref="g8:covariance",
        ),
        raw_source_digest="sha256:" + observation_id[-1] * 64,
        interface_contract_id="G8-G5-CONTRACT",
        interface_contract_digest="sha256:" + "e" * 64,
        source_standard="G8-SYNTHETIC",
        source_profile="G8",
    )


def _release_materials():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            RELEASE_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def _release_assertion(
    private: Ed25519PrivateKey,
    *,
    issued_at: datetime = NOW - timedelta(seconds=5),
    expires_at: datetime = NOW + timedelta(minutes=2),
):
    unsigned = SdaReleaseAuthorizationAssertion(
        key_id=RELEASE_KEY_ID,
        authorization_id="SDA-RELEASE-G8-001",
        hypothesis_set_digest="sha256:" + "a" * 64,
        payload_digest="sha256:" + "b" * 64,
        policy_revision_digest="sha256:" + "c" * 64,
        destination="INTERNAL:OVERWATCH",
        releasability_tags=["INTERNAL", "SYNTHETIC"],
        human_approval_id="G8-HUMAN-001",
        human_approver="identified-human-authority",
        issued_at=issued_at,
        expires_at=expires_at,
        nonce="g8-release-nonce-0001",
        signature_b64url="placeholder",
    )
    return unsigned.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_sda_release_message(unsigned))
            )
        }
    )


def _release_candidate(**overrides):
    values = {
        "hypothesis_set_digest": "sha256:" + "a" * 64,
        "payload_digest": "sha256:" + "b" * 64,
        "policy_revision_digest": "sha256:" + "c" * 64,
        "destination": "INTERNAL:OVERWATCH",
        "releasability_tags": ["INTERNAL", "SYNTHETIC"],
    }
    values.update(overrides)
    return SdaReleaseCandidate.model_validate(values)


def _receipt(auth_id: str, *, payload_fill: str = "b"):
    return SdaReleaseReceipt(
        authorization_id=auth_id,
        payload_digest="sha256:" + payload_fill * 64,
        hypothesis_set_digest="sha256:" + "a" * 64,
        policy_revision_digest="sha256:" + "c" * 64,
        destination="INTERNAL:OVERWATCH",
        releasability_tags=["INTERNAL", "SYNTHETIC"],
        human_approval_id="G8-HUMAN-001",
        human_approver="identified-human-authority",
        signing_key_id=RELEASE_KEY_ID,
        signing_key_fingerprint_sha256="1" * 64,
        consumed_at=NOW,
    )


def _ddil_record(auth_id: str, *, node: str = "node-a", payload_fill: str = "b"):
    return SdaDdilReleaseRecord.from_receipt(
        _receipt(auth_id, payload_fill=payload_fill),
        origin_node=node,
        logical_clock=1,
        authority=1,
        recorded_at=NOW + timedelta(seconds=1),
    )


def _blocked(callable_):
    try:
        callable_()
    except (
        ValidationError,
        ValueError,
        SdaAdapterIsolationError,
        CcsdsKvnProfileError,
        SdaHypothesisError,
        PrimeSentinelAuthorizationError,
        SdaDdilConflict,
        SdaDdilJournalFull,
        EchoEventConflict,
    ):
        return "BLOCK"
    raise AssertionError("expected operation to fail closed")


def _rejected(callable_):
    try:
        callable_()
    except (ValidationError, ValueError):
        return "REJECT"
    raise AssertionError("expected schema/data validation to reject input")


def _run_g1(scenario: str) -> str:
    active = _g1_contract()
    if scenario == "unknown_field_schema":
        payload = _g1_observation(active).model_dump(mode="json")
        payload["unexpected"] = True
        return _rejected(lambda: SdaObservation.model_validate(payload))
    if scenario == "asymmetric_covariance":
        bad = _covariance()
        bad[0][1] = 1.0
        return _rejected(lambda: _g1_observation(active, covariance_6x6=bad))
    if scenario == "nonfinite_position":
        return _blocked(
            lambda: _g1_observation(active, position_km=(math.inf, 2.0, 3.0))
        )
    if scenario == "disabled_contract":
        disabled = _g1_contract(enabled=False)
        item = _g1_observation(disabled)
        return evaluate_sda_ingest(item, contract=disabled, now=NOW).disposition.value
    if scenario == "source_id_mismatch":
        source = _g1_observation(active).source.model_copy(update={"source_id": "OTHER"})
        item = _g1_observation(active, source=source)
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario == "adapter_id_mismatch":
        source = _g1_observation(active).source.model_copy(update={"adapter_id": "OTHER"})
        item = _g1_observation(active, source=source)
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario == "adapter_version_mismatch":
        source = _g1_observation(active).source.model_copy(
            update={"adapter_version": "9.9.9"}
        )
        item = _g1_observation(active, source=source)
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario == "stale_contract_digest":
        item = _g1_observation(active).model_copy(
            update={"interface_contract_digest": "sha256:" + "f" * 64}
        )
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario in {"backward_sequence", "same_sequence_mutation"}:
        first = _g1_observation(
            active,
            source_sequence=2,
            source_event_id="G8-EVENT-002",
            observation_id="G8-OBS-002",
        )
        accepted = evaluate_sda_ingest(first, contract=active, now=NOW)
        assert accepted.next_replay_state is not None
        if scenario == "backward_sequence":
            item = _g1_observation(
                active,
                source_sequence=1,
                source_event_id="G8-EVENT-001",
                observation_id="G8-OBS-001",
            )
        else:
            item = _g1_observation(
                active,
                source_sequence=2,
                source_event_id="G8-EVENT-002",
                observation_id="G8-OBS-002",
                position_km=(9.0, 2.0, 3.0),
            )
        return evaluate_sda_ingest(
            item,
            contract=active,
            replay_state=accepted.next_replay_state,
            now=NOW,
        ).disposition.value
    if scenario == "stale_observation":
        item = _g1_observation(active, observed_at=NOW - timedelta(seconds=700))
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario == "unapproved_releasability":
        item = _g1_observation(active, releasability_tags=["PARTNER"])
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    raise AssertionError(scenario)


def _run_g2(scenario: str) -> str:
    private, verifier = _workload_materials()
    active = _g1_contract(
        require_workload_identity=True,
        require_transport_identity=scenario
        in {"missing_transport_identity", "transport_fingerprint_mismatch"},
    )
    item = _g1_observation(active)

    if scenario == "missing_workload_identity":
        return evaluate_sda_ingest(item, contract=active, now=NOW).disposition.value
    if scenario == "workload_signature_tamper":
        signed = _signed_workload(private)
        tampered = signed.model_copy(update={"source_id": "OTHER"})
        return _blocked(
            lambda: verify_sda_workload_identity(tampered, verifier=verifier, now=NOW)
        )
    if scenario == "workload_revoked_key":
        signed = _signed_workload(private)
        revoked = PrimeSentinelVerifier(
            public_keys_b64url={
                KEY_ID: _b64url(private.public_key().public_bytes_raw())
            },
            revoked_key_ids={KEY_ID},
        )
        return _blocked(
            lambda: verify_sda_workload_identity(signed, verifier=revoked, now=NOW)
        )
    if scenario == "workload_expired":
        signed = _signed_workload(
            private,
            issued_at=NOW - timedelta(minutes=3),
            expires_at=NOW - timedelta(seconds=1),
        )
        return _blocked(
            lambda: verify_sda_workload_identity(signed, verifier=verifier, now=NOW)
        )
    if scenario == "workload_future_issue":
        signed = _signed_workload(
            private,
            issued_at=NOW + timedelta(seconds=31),
            expires_at=NOW + timedelta(minutes=2),
        )
        return _blocked(
            lambda: verify_sda_workload_identity(signed, verifier=verifier, now=NOW)
        )

    adapter = "OTHER" if scenario == "workload_wrong_adapter" else "G8-ADAPTER"
    signed = _signed_workload(private, adapter_id=adapter)
    verified = verify_sda_workload_identity(signed, verifier=verifier, now=NOW)
    if scenario == "workload_wrong_adapter":
        return evaluate_sda_ingest(
            item, contract=active, workload_identity=verified, now=NOW
        ).disposition.value
    if scenario == "missing_transport_identity":
        return evaluate_sda_ingest(
            item, contract=active, workload_identity=verified, now=NOW
        ).disposition.value
    if scenario == "transport_fingerprint_mismatch":
        transport = SdaTransportIdentity(
            certificate_sha256="sha256:" + "e" * 64,
            san_uris=[WORKLOAD_ID],
            not_valid_before=NOW - timedelta(minutes=1),
            not_valid_after=NOW + timedelta(minutes=1),
            client_auth_eku=True,
            basic_constraints_ca=False,
        )
        return evaluate_sda_ingest(
            item,
            contract=active,
            workload_identity=verified,
            transport_identity=transport,
            now=NOW,
        ).disposition.value
    raise AssertionError(scenario)


def _run_g3(scenario: str, tmp_path: Path) -> str:
    if scenario == "oversized_input":
        result = run_isolated_adapter(
            policy=_g3_policy(max_input_bytes=4),
            arguments=["-c", "print('should not run')"],
            payload=b"12345",
        )
        return "BLOCK" if result.status == SdaAdapterRunStatus.INPUT_REJECTED else result.status.value
    if scenario == "shell_metacharacter_literal":
        marker = tmp_path / "g8-must-not-exist"
        hostile = f"; touch {marker}"
        result = run_isolated_adapter(
            policy=_g3_policy(),
            arguments=["-c", "import sys; print(sys.argv[1])", hostile],
            payload=b"",
        )
        if result.status == SdaAdapterRunStatus.SUCCEEDED and not marker.exists():
            return "SAFE_LITERAL"
        return result.status.value
    if scenario == "wall_clock_timeout":
        result = run_isolated_adapter(
            policy=_g3_policy(timeout_seconds=0.1),
            arguments=["-c", "import time; time.sleep(2)"],
            payload=b"",
        )
        return "BLOCK" if result.status == SdaAdapterRunStatus.TIMED_OUT else result.status.value
    if scenario == "stdout_flood":
        result = run_isolated_adapter(
            policy=_g3_policy(),
            arguments=["-c", "import sys; sys.stdout.write('X'*100000)"],
            payload=b"",
        )
        return "BLOCK" if result.status == SdaAdapterRunStatus.OUTPUT_LIMIT_EXCEEDED else result.status.value
    if scenario == "stderr_flood":
        result = run_isolated_adapter(
            policy=_g3_policy(),
            arguments=["-c", "import sys; sys.stderr.write('E'*100000)"],
            payload=b"",
        )
        return "BLOCK" if result.status == SdaAdapterRunStatus.OUTPUT_LIMIT_EXCEEDED else result.status.value
    if scenario == "nonallowed_exit":
        result = run_isolated_adapter(
            policy=_g3_policy(),
            arguments=["-c", "raise SystemExit(7)"],
            payload=b"",
        )
        return "BLOCK" if result.status == SdaAdapterRunStatus.PROCESS_FAILED else result.status.value
    if scenario == "missing_executable":
        return _blocked(
            lambda: run_isolated_adapter(
                policy=_g3_policy(executable_path="/not/a/real/g8/adapter"),
                arguments=["x"],
                payload=b"",
            )
        )
    if scenario == "nul_argument":
        return _blocked(
            lambda: run_isolated_adapter(
                policy=_g3_policy(),
                arguments=["bad\x00argument"],
                payload=b"",
            )
        )
    raise AssertionError(scenario)


def _run_g4(scenario: str) -> str:
    replacements = {
        "opm_wrong_version": ("CCSDS_OPM_VERS = 3.0", "CCSDS_OPM_VERS = 2.0", "opm"),
        "opm_wrong_position_unit": ("X = 7000.0 [km]", "X = 7000.0 [m]", "opm"),
        "opm_wrong_velocity_unit": ("Y_DOT = 7.5 [km/s]", "Y_DOT = 7500 [m/s]", "opm"),
        "opm_duplicate_required_keyword": (
            OPM,
            OPM + "X = 7000.0 [km]\n",
            "opm-full",
        ),
        "opm_nonfinite_numeric": ("X = 7000.0 [km]", "X = NaN [km]", "opm"),
        "tdm_wrong_version": ("CCSDS_TDM_VERS = 2.0", "CCSDS_TDM_VERS = 1.0", "tdm"),
        "tdm_invalid_range_unit": ("RANGE_UNITS = km", "RANGE_UNITS = m", "tdm"),
        "tdm_unsupported_observable": (
            "RANGE = 2026-09-18T00:00:01 1234.5",
            "ANGLE_1 = 2026-09-18T00:00:01 1.0",
            "tdm",
        ),
    }
    old, new, kind = replacements[scenario]
    if kind == "opm-full":
        text = new
        return _blocked(lambda: parse_opm_v3_kvn_profile(text))
    if kind == "opm":
        return _blocked(lambda: parse_opm_v3_kvn_profile(OPM.replace(old, new)))
    return _blocked(lambda: parse_tdm_v2_range_kvn_profile(TDM.replace(old, new)))


def _run_g5(scenario: str) -> str:
    if scenario == "empty_observation_set":
        return _blocked(lambda: build_state_hypothesis_set([]))
    if scenario == "duplicate_observation_id":
        a = _g5_envelope("OBS-1", 0.0)
        b = _g5_envelope("OBS-1", 1.0)
        return _blocked(lambda: build_state_hypothesis_set([a, b]))
    if scenario == "object_identity_mismatch":
        a = _g5_envelope("OBS-1", 0.0)
        b = _g5_envelope("OBS-2", 1.0, object_id="OTHER")
        return _blocked(lambda: build_state_hypothesis_set([a, b]))
    if scenario == "epoch_mismatch":
        a = _g5_envelope("OBS-1", 0.0)
        b = _g5_envelope("OBS-2", 1.0, epoch="2026-09-18T02:00:01")
        return _blocked(lambda: build_state_hypothesis_set([a, b]))
    if scenario == "reference_frame_mismatch":
        a = _g5_envelope("OBS-1", 0.0)
        b = _g5_envelope("OBS-2", 1.0, frame="TEME")
        return _blocked(lambda: build_state_hypothesis_set([a, b]))
    if scenario == "incompatible_outlier":
        a = _g5_envelope("OBS-1", 0.0)
        b = _g5_envelope("OBS-2", 0.5)
        c = _g5_envelope("OBS-3", 100.0)
        result = build_state_hypothesis_set([a, b, c], compatibility_threshold=36.0)
        if result.requires_resolution and len(result.hypotheses) > 1:
            return "MULTI_HYPOTHESIS"
        return "NO_CONFLICT"
    raise AssertionError(scenario)


def _run_g6(scenario: str) -> str:
    private, verifier = _release_materials()
    signed = _release_assertion(private)

    tamper = {
        "tamper_hypothesis_digest": ("hypothesis_set_digest", "sha256:" + "d" * 64),
        "tamper_payload_digest": ("payload_digest", "sha256:" + "d" * 64),
        "tamper_policy_digest": ("policy_revision_digest", "sha256:" + "d" * 64),
        "tamper_destination": ("destination", "PARTNER:OTHER"),
        "tamper_releasability": ("releasability_tags", ["INTERNAL"]),
        "tamper_human_approval": ("human_approval_id", "OTHER-HUMAN"),
    }
    if scenario in tamper:
        field, value = tamper[scenario]
        changed = signed.model_copy(update={field: value})
        return _blocked(
            lambda: verify_sda_release_authorization(changed, verifier=verifier, now=NOW)
        )
    if scenario == "release_expired":
        expired = _release_assertion(
            private,
            issued_at=NOW - timedelta(minutes=3),
            expires_at=NOW - timedelta(seconds=1),
        )
        return _blocked(
            lambda: verify_sda_release_authorization(expired, verifier=verifier, now=NOW)
        )
    if scenario == "release_future_issue":
        future = _release_assertion(
            private,
            issued_at=NOW + timedelta(seconds=31),
            expires_at=NOW + timedelta(minutes=2),
        )
        return _blocked(
            lambda: verify_sda_release_authorization(future, verifier=verifier, now=NOW)
        )

    verified = verify_sda_release_authorization(signed, verifier=verifier, now=NOW)
    if scenario == "release_replay_consumption":
        patch, _receipt_value = consume_sda_release_authorization(
            {}, verified, _release_candidate(), now=NOW
        )
        return _blocked(
            lambda: consume_sda_release_authorization(
                patch, verified, _release_candidate(), now=NOW
            )
        )
    if scenario == "release_use_time_expiry":
        short = _release_assertion(
            private,
            issued_at=NOW - timedelta(seconds=5),
            expires_at=NOW + timedelta(seconds=5),
        )
        short_verified = verify_sda_release_authorization(
            short, verifier=verifier, now=NOW
        )
        return _blocked(
            lambda: consume_sda_release_authorization(
                {},
                short_verified,
                _release_candidate(),
                now=NOW + timedelta(seconds=6),
            )
        )
    raise AssertionError(scenario)


def _run_g7(scenario: str, tmp_path: Path, monkeypatch) -> str:
    if scenario == "journal_semantic_conflict":
        journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())
        journal.append(_ddil_record("SDA-RELEASE-G8-101", payload_fill="b"))
        try:
            journal.append(_ddil_record("SDA-RELEASE-G8-101", payload_fill="d"))
        except SdaDdilConflict:
            return "CONFLICT"
        return "MISSED"
    if scenario == "journal_capacity":
        monkeypatch.setattr(ddil_module, "MAX_DDIL_RELEASE_RECORDS", 1)
        journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())
        journal.append(_ddil_record("SDA-RELEASE-G8-102"))
        return _blocked(
            lambda: journal.append(_ddil_record("SDA-RELEASE-G8-103"))
        )
    if scenario == "journal_tamper_health":
        journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())
        item = _ddil_record("SDA-RELEASE-G8-104")
        journal.append(item)
        connection = sqlite3.connect(journal.db_path)
        try:
            connection.execute(
                "UPDATE release_records SET receipt_digest=? WHERE authorization_id=?",
                ("sha256:" + "f" * 64, item.receipt.authorization_id),
            )
            connection.commit()
        finally:
            connection.close()
        return "DETECT" if journal.health()["ok"] is False else "MISSED"
    if scenario == "rejoin_receipt_conflict":
        plan = reconcile_release_records(
            [_ddil_record("SDA-RELEASE-G8-105", node="left", payload_fill="b")],
            [_ddil_record("SDA-RELEASE-G8-105", node="right", payload_fill="d")],
        )
        return "CONFLICT" if plan.conflicts else "MISSED"
    if scenario == "single_side_internal_conflict":
        try:
            reconcile_release_records(
                [
                    _ddil_record("SDA-RELEASE-G8-106", payload_fill="b"),
                    _ddil_record("SDA-RELEASE-G8-106", payload_fill="d"),
                ],
                [],
            )
        except SdaDdilConflict:
            return "CONFLICT"
        return "MISSED"
    if scenario == "echo_same_origin_mutation":
        echo = EchoEventStore((tmp_path / "echo").resolve())
        first = _ddil_record("SDA-RELEASE-G8-107", payload_fill="b")
        mutated = _ddil_record("SDA-RELEASE-G8-107", payload_fill="d")
        echo.ingest(sda_ddil_release_audit_record(first))
        try:
            echo.ingest(sda_ddil_release_audit_record(mutated))
        except EchoEventConflict:
            return "CONFLICT"
        return "MISSED"
    if scenario == "replay_invalid_sequence":
        return _blocked(
            lambda: ddil_records_to_mission_events(
                [_ddil_record("SDA-RELEASE-G8-108")],
                starting_sequence=0,
            )
        )
    if scenario == "replica_node_identity_separation":
        left = _ddil_record("SDA-RELEASE-G8-109", node="left")
        right = _ddil_record("SDA-RELEASE-G8-109", node="right")
        return (
            "SEPARATED"
            if left.stable_echo_event_id() != right.stable_echo_event_id()
            else "COLLISION"
        )
    raise AssertionError(scenario)


def run_case(case: dict, tmp_path: Path, monkeypatch) -> str:
    gate = case["gate"]
    scenario = case["scenario"]
    if gate == "G1":
        return _run_g1(scenario)
    if gate == "G2":
        return _run_g2(scenario)
    if gate == "G3":
        return _run_g3(scenario, tmp_path)
    if gate == "G4":
        return _run_g4(scenario)
    if gate == "G5":
        return _run_g5(scenario)
    if gate == "G6":
        return _run_g6(scenario)
    if gate == "G7":
        return _run_g7(scenario, tmp_path, monkeypatch)
    raise AssertionError(gate)


def test_g8_manifest_is_frozen_unique_and_budgeted():
    assert CORPUS["schema"] == "WS-SDA-G8-ADVERSARIAL-CORPUS-V1"
    assert CORPUS["frozen_case_count"] == 60
    assert CORPUS["mandatory_false_negative_budget"] == 0
    cases = CORPUS["cases"]
    assert len(cases) == 60
    assert len({case["id"] for case in cases}) == 60
    assert {case["gate"] for case in cases} == {
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",
        "G6",
        "G7",
    }
    assert sum(1 for case in cases if case["must_detect"]) >= 58


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_frozen_g8_case(case, tmp_path, monkeypatch):
    observed = run_case(case, tmp_path, monkeypatch)
    assert observed == case["expected"], (
        f"{case['id']} {case['scenario']} expected={case['expected']} observed={observed}"
    )
