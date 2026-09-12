from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .cbm_twin import ExpectedEnvelope, HealthFinding, TelemetrySample, evaluate_series
from .config_custody import (
    ConfigurationCustodyLedger,
    ConfigurationSnapshot,
    create_snapshot,
)
from .mission_replay import MissionEvent, replay_events
from .models import AuditRecord
from .prime import ActionProposal, ActionState, decide_action


WS_DEMA_SCHEMA = "WS-DEMA-G1-V1"
WS_DEMA_AUTHORITY = "identified-human-authority"

# G1 is deliberately non-weapon. These fields are rejected recursively from
# configuration and telemetry metadata so a mission-assurance demonstration
# cannot silently become a target/engagement controller.
PROHIBITED_CONTROL_KEYS = frozenset(
    {
        "target",
        "target_id",
        "target_track",
        "aimpoint",
        "aim_point",
        "fire_command",
        "engage",
        "engagement",
        "kill_probability",
        "lethality",
        "beam_command",
        "beam_steering",
        "weapon_release",
    }
)


class WsDemaScenario(BaseModel):
    schema: Literal[WS_DEMA_SCHEMA] = WS_DEMA_SCHEMA
    scenario_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )
    created_utc: str = Field(min_length=1)
    actor: str = Field(min_length=1, max_length=128)
    baseline_configuration: dict[str, Any]
    candidate_configuration: dict[str, Any]
    envelopes: list[ExpectedEnvelope] = Field(min_length=1)
    samples: list[TelemetrySample] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_safe_scope(self) -> "WsDemaScenario":
        _assert_non_weapon_payload(self.baseline_configuration)
        _assert_non_weapon_payload(self.candidate_configuration)
        metrics = [envelope.metric for envelope in self.envelopes]
        if len(metrics) != len(set(metrics)):
            raise ValueError("WS-DEMA expected-envelope metrics must be unique")
        supported = set(metrics)
        missing = sorted({sample.metric for sample in self.samples} - supported)
        if missing:
            raise ValueError(f"telemetry has no expected envelope: {', '.join(missing)}")
        return self


class WsDemaAssessment(BaseModel):
    schema: Literal[WS_DEMA_SCHEMA] = WS_DEMA_SCHEMA
    scenario_id: str
    readiness: Literal["READY", "DEGRADED"]
    degraded_metrics: list[str]
    findings: list[dict[str, Any]]
    baseline_digest: str
    active_configuration_digest: str
    authorization_state: ActionState
    authorization_reviewer: str | None = None


@dataclass(frozen=True)
class WsDemaRun:
    scenario: WsDemaScenario
    ledger: ConfigurationCustodyLedger
    baseline: ConfigurationSnapshot
    active: ConfigurationSnapshot
    proposal: ActionProposal
    findings: tuple[HealthFinding, ...]
    assessment: WsDemaAssessment
    replay: tuple[MissionEvent, ...]
    audit_records: tuple[AuditRecord, ...]


def _assert_non_weapon_payload(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in PROHIBITED_CONTROL_KEYS:
                raise ValueError(f"WS-DEMA G1 prohibits weapon-control field {path}.{key}")
            _assert_non_weapon_payload(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_non_weapon_payload(child, path=f"{path}[{index}]")


def _finding_payload(finding: HealthFinding) -> dict[str, Any]:
    return {
        "sample_id": finding.sample_id,
        "asset_id": finding.asset_id,
        "metric": finding.metric,
        "status": finding.status,
        "deviation": finding.deviation,
        "expected_minimum": finding.expected_minimum,
        "expected_maximum": finding.expected_maximum,
    }


def _audit(
    *,
    scenario_id: str,
    sequence: int,
    timestamp: str,
    event: str,
    actor: str,
    payload: dict[str, Any],
) -> AuditRecord:
    safe_payload = dict(payload)
    _assert_non_weapon_payload(safe_payload)
    safe_payload.update(
        {
            "_outbox_event_id": f"SARA-EVENT-WS-DEMA-{scenario_id}-{sequence:04d}",
            "_delivery_semantics": "AT_LEAST_ONCE",
            "ws_dema_schema": WS_DEMA_SCHEMA,
            "scenario_id": scenario_id,
        }
    )
    return AuditRecord(timestamp=timestamp, event=event, actor=actor, payload=safe_payload)


def propose_configuration_change(scenario: WsDemaScenario) -> ActionProposal:
    return ActionProposal(
        proposal_id=f"WS-DEMA-CONFIG-{scenario.scenario_id}",
        action="apply_mission_assurance_configuration",
        rationale=[
            "Candidate configuration is limited to non-weapon mission-assurance state.",
            "An identified human authority must approve the change before custody advances.",
        ],
        authority_required=WS_DEMA_AUTHORITY,
    )


def run_g1_scenario(
    scenario: WsDemaScenario,
    *,
    reviewer: str | None = None,
    approve_candidate: bool = False,
    decision_reason: str = "G1 synthetic mission-assurance configuration review",
) -> WsDemaRun:
    envelopes = {envelope.metric: envelope for envelope in scenario.envelopes}
    findings = evaluate_series(scenario.samples, envelopes)

    ledger = ConfigurationCustodyLedger()
    baseline = create_snapshot(
        snapshot_id=f"{scenario.scenario_id}-baseline",
        payload=dict(scenario.baseline_configuration),
        created_utc=scenario.created_utc,
        actor=scenario.actor,
        reason="WS-DEMA G1 baseline",
    )
    ledger.append(baseline)

    proposal = propose_configuration_change(scenario)
    active = baseline
    if approve_candidate:
        if not reviewer:
            raise ValueError("approved WS-DEMA configuration changes require an identified reviewer")
        proposal = decide_action(
            proposal,
            reviewer=reviewer,
            state=ActionState.APPROVED,
            reason=decision_reason,
        )
        candidate = create_snapshot(
            snapshot_id=f"{scenario.scenario_id}-candidate",
            payload=dict(scenario.candidate_configuration),
            created_utc=scenario.created_utc,
            actor=reviewer,
            reason=decision_reason,
            parent_digest=baseline.digest,
        )
        ledger.append(candidate)
        active = candidate
    elif reviewer:
        proposal = decide_action(
            proposal,
            reviewer=reviewer,
            state=ActionState.DENIED,
            reason=decision_reason,
        )

    degraded_metrics = sorted({finding.metric for finding in findings if finding.status != "NOMINAL"})
    readiness: Literal["READY", "DEGRADED"] = "DEGRADED" if degraded_metrics else "READY"

    replay_events_input: list[MissionEvent] = []
    audit_records: list[AuditRecord] = []
    for sequence, finding in enumerate(findings, start=1):
        event_type = "subsystem_nominal" if finding.status == "NOMINAL" else "subsystem_degraded"
        payload = _finding_payload(finding)
        replay_events_input.append(
            MissionEvent(
                sequence=sequence,
                t_seconds=float(sequence - 1),
                source=finding.asset_id,
                event_type=event_type,
                payload=payload,
            )
        )
        audit_records.append(
            _audit(
                scenario_id=scenario.scenario_id,
                sequence=sequence,
                timestamp=scenario.created_utc,
                event=f"ws_dema.{event_type}",
                actor=scenario.actor,
                payload=payload,
            )
        )

    decision_sequence = len(findings) + 1
    decision_payload = {
        "proposal_id": proposal.proposal_id,
        "state": proposal.state.value,
        "reviewer": proposal.reviewer,
        "authority_required": proposal.authority_required,
        "baseline_digest": baseline.digest,
        "active_configuration_digest": active.digest,
    }
    replay_events_input.append(
        MissionEvent(
            sequence=decision_sequence,
            t_seconds=float(decision_sequence - 1),
            source="PRIME_SENTINEL",
            event_type="configuration_authorization_state",
            payload=decision_payload,
        )
    )
    audit_records.append(
        _audit(
            scenario_id=scenario.scenario_id,
            sequence=decision_sequence,
            timestamp=scenario.created_utc,
            event="ws_dema.configuration_authorization_state",
            actor=proposal.reviewer or "PRIME_SENTINEL",
            payload=decision_payload,
        )
    )

    assessment = WsDemaAssessment(
        scenario_id=scenario.scenario_id,
        readiness=readiness,
        degraded_metrics=degraded_metrics,
        findings=[_finding_payload(finding) for finding in findings],
        baseline_digest=baseline.digest,
        active_configuration_digest=active.digest,
        authorization_state=proposal.state,
        authorization_reviewer=proposal.reviewer,
    )
    return WsDemaRun(
        scenario=scenario,
        ledger=ledger,
        baseline=baseline,
        active=active,
        proposal=proposal,
        findings=findings,
        assessment=assessment,
        replay=replay_events(replay_events_input),
        audit_records=tuple(audit_records),
    )


def rollback_to_baseline(
    run: WsDemaRun,
    *,
    snapshot_id: str,
    created_utc: str,
    actor: str,
    reason: str,
) -> ConfigurationSnapshot:
    if run.proposal.state != ActionState.APPROVED:
        raise ValueError("rollback requires a previously approved configuration transition")
    rollback = run.ledger.rollback_snapshot(
        target_digest=run.baseline.digest,
        snapshot_id=snapshot_id,
        created_utc=created_utc,
        actor=actor,
        reason=reason,
    )
    run.ledger.append(rollback)
    return rollback
