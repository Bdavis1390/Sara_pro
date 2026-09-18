from dataclasses import replace

from security.poo.lineage_guard import LineageNode, evaluate_lineage, lineage_digest


def linear_lineage():
    return [
        LineageNode(
            poo_digest="poo:001",
            asset_id="asset:alpha",
            claimant_id="claimant:one",
            previous_poo_digest=None,
            event_type="CLAIM",
            technical_poo_valid=True,
            superseded=True,
        ),
        LineageNode(
            poo_digest="poo:002",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
            superseded=True,
        ),
        LineageNode(
            poo_digest="poo:003",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:002",
            event_type="RECOVERY",
            technical_poo_valid=True,
            superseded=False,
        ),
    ]


def test_linear_lineage_has_exactly_one_active_tip():
    d = evaluate_lineage(linear_lineage())
    assert d.lineage_valid is True
    assert d.status == "LINEAGE_INTERNALLY_CONSISTENT"
    assert d.active_tip_digest == "poo:003"
    assert d.fork_detected is False
    assert d.cycle_detected is False
    assert d.legal_title_established is False


def test_two_successors_from_same_parent_detects_double_transfer_fork():
    nodes = linear_lineage()[:1] + [
        LineageNode(
            poo_digest="poo:002a",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
        ),
        LineageNode(
            poo_digest="poo:002b",
            asset_id="asset:alpha",
            claimant_id="claimant:three",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
        ),
    ]
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert d.fork_detected is True
    assert "forked ownership lineage detected" in d.issues
    assert d.active_tip_digest is None


def test_missing_parent_is_rejected():
    nodes = [
        LineageNode(
            poo_digest="poo:002",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="missing",
            event_type="TRANSFER",
            technical_poo_valid=True,
        )
    ]
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "missing prior PoO: missing" in d.issues


def test_cycle_is_rejected():
    nodes = [
        LineageNode(
            poo_digest="poo:001",
            asset_id="asset:alpha",
            claimant_id="claimant:one",
            previous_poo_digest="poo:002",
            event_type="TRANSFER",
            technical_poo_valid=True,
            superseded=True,
        ),
        LineageNode(
            poo_digest="poo:002",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
            superseded=True,
        ),
    ]
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert d.cycle_detected is True
    assert "cyclic ownership lineage detected" in d.issues


def test_revoked_parent_cannot_spawn_successor():
    nodes = linear_lineage()[:2]
    nodes[0] = replace(nodes[0], revoked=True)
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "revoked PoO cannot have successor: poo:001" in d.issues


def test_parent_with_successor_must_be_marked_superseded():
    nodes = linear_lineage()
    nodes[0] = replace(nodes[0], superseded=False)
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "prior PoO with successor must be superseded: poo:001" in d.issues


def test_terminal_record_cannot_be_marked_superseded():
    nodes = linear_lineage()
    nodes[-1] = replace(nodes[-1], superseded=True)
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "terminal PoO cannot be marked superseded: poo:003" in d.issues


def test_lineage_cannot_mix_asset_ids():
    nodes = linear_lineage()
    nodes[-1] = replace(nodes[-1], asset_id="asset:other")
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "lineage must bind exactly one non-empty asset_id" in d.issues


def test_nonvalid_technical_poo_is_rejected():
    nodes = linear_lineage()
    nodes[-1] = replace(nodes[-1], technical_poo_valid=False)
    d = evaluate_lineage(nodes)
    assert d.lineage_valid is False
    assert "lineage contains non-valid technical PoO" in d.issues


def test_lineage_digest_is_order_independent_but_content_sensitive():
    nodes = linear_lineage()
    assert lineage_digest(nodes) == lineage_digest(list(reversed(nodes)))
    altered = list(nodes)
    altered[-1] = replace(altered[-1], claimant_id="claimant:changed")
    assert lineage_digest(altered) != lineage_digest(nodes)
