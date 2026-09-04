from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, Field

from .hmaa import (
    AssuranceAssessment,
    HMAAEvidenceBundle,
    build_evidence_bundle,
    seal_event,
)
from .hmaa_lattice_contract import (
    LATTICE_PUBLIC_CONTRACT_VERSION,
    LatticeContractEvent,
    LatticeStream,
    parse_entity_stream_message,
    parse_task_stream_message,
)
from .hmaa_state import HMAAAssuranceState, HMAAStateObservation


class InteropStep(BaseModel):
    contract_event: LatticeContractEvent
    state: HMAAStateObservation
    assessment: AssuranceAssessment


class InteropEvidenceManifest(BaseModel):
    contract_version: str = LATTICE_PUBLIC_CONTRACT_VERSION
    source_label: str
    mission_id: str
    live_environment_validated: bool = False
    fixture_sha256: str
    event_count: int
    disposition_counts: dict[str, int] = Field(default_factory=dict)
    final_chain_hash: str | None = None


class InteropRunResult(BaseModel):
    manifest: InteropEvidenceManifest
    evidence_bundle: HMAAEvidenceBundle
    steps: list[InteropStep]


def _fixture_digest(items: Sequence[Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        list(items),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_public_contract_replay(
    *,
    mission_id: str,
    items: Sequence[Mapping[str, Any]],
    source_label: str = "synthetic-public-contract-fixture",
    clock_skew_tolerance_seconds: float = 2.0,
) -> InteropRunResult:
    if not items:
        raise ValueError("interop replay requires at least one stream item")

    state = HMAAAssuranceState(
        clock_skew_tolerance_seconds=clock_skew_tolerance_seconds
    )
    previous_hash: str | None = None
    sealed_events = []
    steps: list[InteropStep] = []
    counts: Counter[str] = Counter()

    for index, item in enumerate(items):
        stream_value = item.get("stream")
        message = item.get("message")
        if not isinstance(message, Mapping):
            raise ValueError(f"interop item[{index}] message must be an object")

        try:
            stream = LatticeStream(str(stream_value))
        except ValueError as exc:
            raise ValueError(
                f"interop item[{index}] has unsupported stream {stream_value!r}"
            ) from exc

        if stream is LatticeStream.ENTITIES:
            contract_event = parse_entity_stream_message(
                message, mission_id=mission_id
            )
        else:
            contract_event = parse_task_stream_message(
                message, mission_id=mission_id
            )

        observation, assessment = state.assess(contract_event.hmaa_event)
        sealed = seal_event(contract_event.hmaa_event, previous_hash)
        previous_hash = sealed.event_hash
        sealed_events.append(sealed)
        counts[assessment.disposition.value] += 1
        steps.append(
            InteropStep(
                contract_event=contract_event.model_copy(
                    update={"hmaa_event": sealed}
                ),
                state=observation,
                assessment=assessment,
            )
        )

    bundle = build_evidence_bundle(mission_id, sealed_events)
    manifest = InteropEvidenceManifest(
        source_label=source_label,
        mission_id=mission_id,
        live_environment_validated=False,
        fixture_sha256="sha256:" + _fixture_digest(items),
        event_count=len(sealed_events),
        disposition_counts=dict(sorted(counts.items())),
        final_chain_hash=bundle.final_chain_hash,
    )
    return InteropRunResult(
        manifest=manifest,
        evidence_bundle=bundle,
        steps=steps,
    )
