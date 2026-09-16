from dataclasses import replace

from security.poo.registry_guard import evaluate_registry, registry_digest
from security.poo.state_engine import STATE_SCHEMA, TechnicalOwnershipState


def state(asset, claimant, poo, coc, generation=0, event="CLAIM", prev_poo=None, prev_coc=None):
    return TechnicalOwnershipState(
        schema=STATE_SCHEMA,
        asset_id=asset,
        claimant_id=claimant,
        active_poo_digest=poo,
        active_coc_digest=coc,
        control_key_fingerprint=f"key:{claimant}:{generation}",
        title_reference=f"title:{asset}",
        generation=generation,
        source_event_type=event,
        previous_poo_digest=prev_poo,
        previous_coc_digest=prev_coc,
    )


def test_multi_asset_registry_exposes_one_active_technical_tip_per_asset():
    a0 = state("asset:a", "alice", "poo:a0", "coc:a0")
    a1 = state(
        "asset:a", "bob", "poo:a1", "coc:a1", 1, "TRANSFER", "poo:a0", "coc:a0"
    )
    b0 = state("asset:b", "carol", "poo:b0", "coc:b0")
    d = evaluate_registry([a0, a1, b0])
    assert d.registry_valid is True
    assert d.asset_count == 2
    assert d.state_count == 3
    assert d.active_poo_by_asset == {"asset:a": "poo:a1", "asset:b": "poo:b0"}
    assert d.active_claimant_by_asset == {"asset:a": "bob", "asset:b": "carol"}
    assert d.legal_registry_authority is False
    assert d.legal_title_established is False


def test_two_genesis_claims_for_same_asset_are_blocked():
    g1 = state("asset:a", "alice", "poo:a0", "coc:a0")
    g2 = state("asset:a", "mallory", "poo:aX", "coc:aX")
    d = evaluate_registry([g1, g2])
    assert d.registry_valid is False
    assert any("exactly one genesis" in issue for issue in d.issues)
    assert d.active_poo_by_asset == {}


def test_duplicate_technical_state_is_blocked():
    g = state("asset:a", "alice", "poo:a0", "coc:a0")
    d = evaluate_registry([g, g])
    assert d.registry_valid is False
    assert "duplicate technical ownership state" in d.issues


def test_reused_poo_digest_across_assets_is_blocked():
    a = state("asset:a", "alice", "poo:same", "coc:a0")
    b = state("asset:b", "bob", "poo:same", "coc:b0")
    d = evaluate_registry([a, b])
    assert d.registry_valid is False
    assert "PoO digest reused across registry states" in d.issues


def test_generation_gap_is_blocked_even_if_poo_and_coc_links_connect():
    g = state("asset:a", "alice", "poo:a0", "coc:a0")
    bad = state(
        "asset:a", "bob", "poo:a1", "coc:a1", 2, "TRANSFER", "poo:a0", "coc:a0"
    )
    d = evaluate_registry([g, bad])
    assert d.registry_valid is False
    assert "asset:a: state generations must be contiguous from zero" in d.issues


def test_broken_coc_lineage_is_blocked_even_if_poo_links_connect():
    g = state("asset:a", "alice", "poo:a0", "coc:a0")
    bad = state(
        "asset:a", "bob", "poo:a1", "coc:a1", 1, "TRANSFER", "poo:a0", "coc:wrong"
    )
    d = evaluate_registry([g, bad])
    assert d.registry_valid is False
    assert "asset:a: COC: predecessor mismatch at generation 1" in d.issues


def test_registry_digest_is_order_independent_but_content_sensitive():
    a = state("asset:a", "alice", "poo:a0", "coc:a0")
    b = state("asset:b", "bob", "poo:b0", "coc:b0")
    assert registry_digest([a, b]) == registry_digest([b, a])
    assert registry_digest([a, b]) != registry_digest([a, replace(b, claimant_id="carol")])


def test_empty_registry_fails_closed():
    d = evaluate_registry([])
    assert d.registry_valid is False
    assert "technical ownership registry is empty" in d.issues
