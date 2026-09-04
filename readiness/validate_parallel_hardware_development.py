#!/usr/bin/env python3
"""Fail-closed validator for parallel PALACE/metasurface/AlTi development.

This validator checks that the newly linked hardware/material lanes remain inside
existing Worldshepherd evidence, access-control, and contact-authority boundaries.
It performs no physical validation and creates no external authority.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_metasurface() -> dict:
    p = load("metasurface/adaptive_control_contract.v1.json")
    require(p["schema"] == "WS-ADAPTIVE-METASURFACE-CONTROL-V1", "wrong metasurface schema")
    require(p["coupling_contract"]["K_ij_min"] == -1.0, "K_ij minimum drift")
    require(p["coupling_contract"]["K_ij_max"] == 1.0, "K_ij maximum drift")
    require(p["control_action"]["saturation_required"] is True, "actuator saturation must be required")
    require(p["control_action"]["command_without_valid_sensor_timestamp"] == "REJECT", "sensor-time fail closed missing")
    require(p["control_action"]["command_without_configuration_digest"] == "REJECT", "config digest fail closed missing")
    require(p["mode_indexing"]["prime_indexing"] == "MATHEMATICAL_DECOMPOSITION_ONLY", "prime indexing overclaimed")
    require(p["mode_indexing"]["prime_indexing_is_quantum_number_claim"] is False, "prime index cannot be quantum claim")
    require(p["mode_indexing"]["one_is_prime"] is False, "1 cannot be marked prime")
    require(p["mode_indexing"]["forty_nine_is_prime"] is False, "49 cannot be marked prime")
    require(p["spectral_scope"]["195_nm_to_9675_nm"] == "RESEARCH_TARGET_ONLY_NOT_DEMONSTRATED", "spectral target overclaimed")
    require(p["physics_constraints"]["finite_total_energy_required"] is True, "finite-energy constraint missing")
    require(p["physics_constraints"]["thermal_limit_required"] is True, "thermal constraint missing")
    require(p["physics_constraints"]["passivity_or_supplied_power_accounting_required"] is True, "power accounting missing")
    require(p["physics_constraints"]["momentum_and_force_claims_require_explicit_control_volume_balance"] is True, "force balance guard missing")
    expected_paths = {
        "convergence_source": "palace/anchor_manifest.v1.json",
        "snapshot_ingester": "palace/ingest_anchor_snapshot.py",
        "numerical_crosscheck": "palace/compare_cross_solver.py",
        "physical_correlation": "palace/compare_vna_correlation.py",
    }
    for key, path in expected_paths.items():
        require(p["palace_interface"][key] == path, f"PALACE interface drift: {key}")
        require((ROOT / path).is_file(), f"PALACE interface target missing: {path}")
    required_prohibitions = {
        "stealth achieved",
        "cloaking achieved",
        "broadband cancellation achieved",
        "195-9675 nm programmability demonstrated",
        "reactionless propulsion",
        "net energy from a static ambient field",
        "quantum behavior proven by prime indexing",
    }
    require(required_prohibitions.issubset(set(p["prohibited_claims"])), "required claim prohibitions missing")
    require(p["contact_authority_created"] is False, "metasurface contract cannot create contact authority")
    return {"schema": p["schema"], "prohibited_claim_count": len(p["prohibited_claims"])}


def validate_alti() -> dict:
    p = load("materials/ws_alti_m1_msz_prime_validation.v1.json")
    require(p["schema"] == "WS-ALTI-M1-MSZ-PRIME-VALIDATION-V1", "wrong AlTi schema")
    state = p["current_claim_state"]
    require(state["commercial_value_class"] == "IP_STAGE", "AlTi commercial class must remain IP_STAGE")
    require(state["physical_material_performance"] == "NOT_YET_VALIDATED_BY_THIS_CONTRACT", "physical material performance overclaimed")
    require(state["programmable_deposited_behavior"] == "HYPOTHESIS_REQUIRES_COUPON_VALIDATION", "programmability overclaimed")
    require(state["partner_interest"] == "NOT_ESTABLISHED_BY_INTERNAL_WORK", "partner interest overclaimed")
    stages = p["stages"]
    expected = [
        "A0_IP_AND_DESIGN_CUSTODY",
        "A1_MODELING",
        "A2_COUPON_BUILD",
        "A3_COUPON_CHARACTERIZATION",
        "A4_REPEATABILITY_AND_PROCESS_WINDOW",
        "A5_EXTERNAL_PARTNER_REPLICATION",
    ]
    require([s["stage_id"] for s in stages] == expected, "AlTi staged validation sequence drift")
    a4 = stages[4]
    require(int(a4["minimum_independent_builds"]) >= 3, "AlTi repeatability requires >=3 independent builds")
    require(int(a4["minimum_coupons_per_build"]) >= 3, "AlTi repeatability requires >=3 coupons/build")
    require(stages[5]["self_close_allowed"] is False, "external AlTi replication cannot self-close")
    prog = p["programmability_evidence_rule"]
    require(prog["internal_modeling_alone_sufficient"] is False, "modeling alone cannot prove AlTi programmability")
    require(len(prog["required_for_claim"]) >= 4, "programmability evidence rule incomplete")
    require(p["commercialization_boundary"]["valuation_must_not_be_upgraded_by_internal_readiness_alone"] is True, "valuation claims boundary missing")
    require(p["contact_authority_created"] is False, "AlTi contract cannot create contact authority")
    return {"schema": p["schema"], "stage_count": len(stages), "minimum_repeatability_coupons": a4["minimum_independent_builds"] * a4["minimum_coupons_per_build"]}


def validate_access_and_ingest() -> dict:
    p = load("security/palace_evidence_ingest_policy.v1.json")
    require(p["schema"] == "WS-PALACE-EVIDENCE-INGEST-POLICY-V1", "wrong PALACE ingest policy schema")
    require(p["existing_role_model"]["relay_role"] == "relay", "relay role drift")
    require(p["existing_role_model"]["admin_role"] == "admin", "admin role drift")
    require(p["existing_role_model"]["separate_tokens_required"] is True, "token separation required")
    modes = {x["mode"]: x for x in p["ingest_modes"]}
    require(modes["SNAPSHOT_READ"]["minimum_role"] == "relay", "snapshot read role drift")
    require(modes["SNAPSHOT_READ"]["writes_into_snapshot"] is False, "snapshot must be immutable to ingester")
    require(modes["EVIDENCE_REGISTER"]["minimum_role"] == "admin", "evidence register must require admin")
    require(modes["EVIDENCE_REGISTER"]["writes_into_live_solver_tree"] is False, "registration cannot write live solver tree")
    require(modes["EXTERNAL_EVIDENCE_PROMOTION"]["automatic_promotion"] is False, "external evidence cannot auto-promote")
    live = p["live_solver_boundary"]
    for key in (
        "live_worldshepherd_folder_is_read_write_target",
        "ingester_may_launch_palace",
        "ingester_may_stop_or_restart_palace",
        "ingester_may_delete_live_outputs",
        "ingester_may_infer_completed_anchor_ids_from_count",
    ):
        require(live[key] is False, f"live PALACE boundary must remain false: {key}")
    require(p["boeing_spirit_contact_effect"] == "NONE", "PALACE ingest cannot affect Boeing/Spirit contact gate")
    require(p["contact_authority_created"] is False, "PALACE ingest cannot create contact authority")

    auth_text = (ROOT / "deployments/sara_verified_local_v1/worldshepherd_sara/auth.py").read_text(encoding="utf-8")
    for token in ('RELAY = "relay"', 'ADMIN = "admin"', 'SARA_RELAY_TOKEN', 'SARA_ADMIN_TOKEN', 'require_admin'):
        require(token in auth_text, f"existing SARA auth contract missing token: {token}")
    require("hmac.compare_digest(relay, admin)" in auth_text, "existing SARA token-distinction guard missing")

    ingest_text = (ROOT / "palace/ingest_anchor_snapshot.py").read_text(encoding="utf-8")
    require("--output must be outside --snapshot-root" in ingest_text, "snapshot write-boundary guard missing")
    require("unknown anchor_id" in ingest_text, "anchor identity fail-closed guard missing")
    require("Palace" not in ingest_text or "launch" not in ingest_text.lower(), "ingester appears to contain a PALACE launch path")
    return {"schema": p["schema"], "ingest_mode_count": len(modes), "auth_role_model_static_crosscheck": "PASS"}


def main() -> None:
    report = {
        "schema": "WS-PARALLEL-HARDWARE-DEVELOPMENT-VALIDATION-REPORT-V1",
        "metasurface": validate_metasurface(),
        "alti": validate_alti(),
        "palace_access": validate_access_and_ingest(),
        "evidence_effect": "INTERNAL_CONTRACT_AND_SOFTWARE_VALIDATION_ONLY",
        "physical_validation_created": False,
        "partner_validation_created": False,
        "independent_replication_created": False,
        "contact_authority_created": False,
        "boeing_spirit_contact_effect": "NONE",
        "status": "PASS",
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
