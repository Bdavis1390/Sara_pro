from security.poo.audit_projection import POO_AUDIT_SCHEMA, lineage_audit_projection
from security.poo.lineage_guard import LineageNode


def healthy_lineage():
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
        ),
    ]


def forked_lineage():
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


def test_healthy_lineage_projects_monitorable_non_authoritative_state():
    p = lineage_audit_projection(healthy_lineage())
    assert p["schema"] == POO_AUDIT_SCHEMA
    assert p["operation"] == "LINEAGE_INTEGRITY"
    assert p["lineage_checked"] is True
    assert p["lineage_valid"] is True
    assert p["active_tip_digest"] == "poo:002"
    assert p["lineage_issue_count"] == 0
    assert p["lineage_conflict_type"] == "NONE"
    assert p["echo_state"] == "ECHO_POO_LINEAGE_ACCEPTED"
    assert p["prime_state"] == "PRIME_POO_LINEAGE_ELIGIBLE"
    assert p["sara_state"] == "SARA_POO_LINEAGE_MONITORABLE"
    assert p["overwatch_state"] == "OVERWATCH_POO_LINEAGE_HEALTHY"
    assert p["technical_attestation_ready"] is False
    assert p["transfer_ready"] is False
    assert p["recovery_ready"] is False
    assert p["conflict_winner_selected"] is False
    assert p["lineage_auto_resolved"] is False
    assert p["legal_title_established"] is False


def test_fork_projects_fail_closed_dispute_state_without_selecting_winner():
    p = lineage_audit_projection(forked_lineage())
    assert p["operation"] == "LINEAGE_INTEGRITY"
    assert p["lineage_valid"] is False
    assert p["fork_detected"] is True
    assert p["active_tip_digest"] is None
    assert p["lineage_issue_count"] >= 1
    assert p["lineage_conflict_type"] == "FORK"
    assert p["echo_state"] == "ECHO_POO_LINEAGE_CONFLICT_CUSTODIED"
    assert p["prime_state"] == "PRIME_POO_LINEAGE_BLOCKED"
    assert p["sara_state"] == "SARA_POO_LINEAGE_DISPUTE_BLOCK"
    assert p["overwatch_state"] == "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE"
    assert p["technical_attestation_ready"] is False
    assert p["transfer_ready"] is False
    assert p["recovery_ready"] is False
    assert p["conflict_winner_selected"] is False
    assert p["lineage_auto_resolved"] is False
    assert p["ownership_changed"] is False
    assert p["transfer_executed"] is False
    assert p["live_value_authorized"] is False


def test_structural_lineage_failure_is_blocked_even_without_fork_or_cycle():
    nodes = [
        LineageNode(
            poo_digest="poo:002",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="missing-parent",
            event_type="TRANSFER",
            technical_poo_valid=True,
        )
    ]
    p = lineage_audit_projection(nodes)
    assert p["lineage_valid"] is False
    assert p["fork_detected"] is False
    assert p["cycle_detected"] is False
    assert p["lineage_conflict_type"] == "STRUCTURAL"
    assert p["prime_state"] == "PRIME_POO_LINEAGE_BLOCKED"
    assert p["sara_state"] == "SARA_POO_LINEAGE_DISPUTE_BLOCK"


def test_cycle_is_escalated_as_explicit_lineage_conflict():
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
    p = lineage_audit_projection(nodes)
    assert p["lineage_valid"] is False
    assert p["cycle_detected"] is True
    assert p["lineage_conflict_type"] == "CYCLE"
    assert p["active_tip_digest"] is None
    assert p["overwatch_state"] == "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE"
