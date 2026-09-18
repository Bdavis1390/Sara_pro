from security.poo.state_engine import (
    STATE_SCHEMA,
    TechnicalOwnershipState,
    evaluate_state_lineage,
)


def state(
    *,
    poo,
    coc,
    generation,
    event,
    claimant="claimant:one",
    prev_poo=None,
    prev_coc=None,
):
    return TechnicalOwnershipState(
        schema=STATE_SCHEMA,
        asset_id="asset:alpha",
        claimant_id=claimant,
        active_poo_digest=poo,
        active_coc_digest=coc,
        control_key_fingerprint=f"key:{generation}",
        title_reference="title:alpha",
        generation=generation,
        source_event_type=event,
        previous_poo_digest=prev_poo,
        previous_coc_digest=prev_coc,
    )


def test_valid_dual_lineage_reports_all_dimensions_true():
    g = state(poo="poo:0", coc="coc:0", generation=0, event="CLAIM")
    t = state(
        poo="poo:1",
        coc="coc:1",
        generation=1,
        event="TRANSFER",
        claimant="claimant:two",
        prev_poo="poo:0",
        prev_coc="coc:0",
    )
    d = evaluate_state_lineage([g, t])
    assert d.lineage_valid is True
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is True
    assert d.generation_valid is True
    assert d.active_tip_digest == "poo:1"
    assert d.legal_title_established is False


def test_valid_poo_chain_with_broken_coc_predecessor_is_rejected():
    g = state(poo="poo:0", coc="coc:0", generation=0, event="CLAIM")
    t = state(
        poo="poo:1",
        coc="coc:1",
        generation=1,
        event="TRANSFER",
        claimant="claimant:two",
        prev_poo="poo:0",
        prev_coc="coc:wrong",
    )
    d = evaluate_state_lineage([g, t])
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is False
    assert d.lineage_valid is False
    assert "COC: predecessor mismatch at generation 1" in d.issues


def test_duplicate_coc_digest_is_rejected_even_when_poo_digests_are_unique():
    g = state(poo="poo:0", coc="coc:same", generation=0, event="CLAIM")
    t = state(
        poo="poo:1",
        coc="coc:same",
        generation=1,
        event="RECOVERY",
        prev_poo="poo:0",
        prev_coc="coc:same",
    )
    d = evaluate_state_lineage([g, t])
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is False
    assert "COC: duplicate active COC digest" in d.issues


def test_generation_gap_is_reported_directly():
    g = state(poo="poo:0", coc="coc:0", generation=0, event="CLAIM")
    t = state(
        poo="poo:1",
        coc="coc:1",
        generation=2,
        event="TRANSFER",
        prev_poo="poo:0",
        prev_coc="coc:0",
    )
    d = evaluate_state_lineage([g, t])
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is True
    assert d.generation_valid is False
    assert d.lineage_valid is False
    assert "state generations must be contiguous from zero" in d.issues


def test_genesis_with_previous_coc_is_rejected():
    g = state(
        poo="poo:0",
        coc="coc:0",
        generation=0,
        event="CLAIM",
        prev_coc="unexpected",
    )
    d = evaluate_state_lineage([g])
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is False
    assert d.lineage_valid is False
    assert "COC: genesis technical state must have no previous COC" in d.issues
