from __future__ import annotations

import pytest

from worldshepherd_sara.poo_registry_commit import (
    POO_TECHNICAL_REGISTRY_KEY,
    PoODurableCommitError,
    PoOTechnicalRegistryNamespace,
    PoOTechnicalStateRecord,
    load_poo_registry_namespace,
    poo_registry_digest,
)


def genesis() -> PoOTechnicalStateRecord:
    return PoOTechnicalStateRecord(
        asset_id="asset:recovery",
        claimant_id="claimant:owner",
        active_poo_digest="poo:genesis",
        active_coc_digest="coc:genesis",
        control_key_fingerprint="key:old",
        title_reference="title:recovery",
        generation=0,
        source_event_type="CLAIM",
        previous_poo_digest=None,
        previous_coc_digest=None,
    )


def recovery(*, claimant_id: str) -> PoOTechnicalStateRecord:
    return PoOTechnicalStateRecord(
        asset_id="asset:recovery",
        claimant_id=claimant_id,
        active_poo_digest="poo:recovery:1",
        active_coc_digest="coc:recovery:1",
        control_key_fingerprint="key:new",
        title_reference="title:recovery",
        generation=1,
        source_event_type="RECOVERY",
        previous_poo_digest="poo:genesis",
        previous_coc_digest="coc:genesis",
    )


def registry_payload(states: list[PoOTechnicalStateRecord]) -> dict:
    namespace = PoOTechnicalRegistryNamespace(
        registry_digest=poo_registry_digest(states),
        states=states,
        commits={},
    )
    return {POO_TECHNICAL_REGISTRY_KEY: namespace.model_dump(mode="json")}


def test_same_claimant_recovery_is_structurally_valid_at_durable_boundary():
    states = [genesis(), recovery(claimant_id="claimant:owner")]
    namespace = load_poo_registry_namespace(registry_payload(states))
    assert len(namespace.states) == 2
    assert namespace.states[-1].source_event_type == "RECOVERY"
    assert namespace.states[-1].claimant_id == namespace.states[0].claimant_id


def test_claimant_changing_recovery_is_rejected_independent_of_upstream_projection():
    states = [genesis(), recovery(claimant_id="claimant:attacker")]
    with pytest.raises(PoODurableCommitError, match="RECOVERY must preserve parent claimant"):
        load_poo_registry_namespace(registry_payload(states))
