#!/usr/bin/env python3
"""Fail-closed cross-domain validator for PALACE, metasurface and WS-AlTi lanes.

The checks are contract/software checks only. They create no physical, partner,
independent, certification, or external-contact evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise AssertionError(msg)


def validate_metasurface() -> dict:
    p = load("metasurface/adaptive_control_contract.v1.json")
    require(p["schema"] == "WS-ADAPTIVE-METASURFACE-CONTROL-V1", "metasurface schema drift")
    c = p["coupling_contract"]
    require((c["K_ij_min"], c["K_ij_max"]) == (-1.0, 1.0), "signed coupling bounds drift")
    a = p["control_action"]
    require(a["saturation_required"] is True, "saturation must be required")
    require(a["command_without_valid_sensor_timestamp"] == "REJECT", "sensor-time guard missing")
    require(a["command_without_configuration_digest"] == "REJECT", "configuration guard missing")

    m = p["mode_indexing"]
    require(m["prime_indexing"] == "MATHEMATICAL_DECOMPOSITION_ONLY", "prime indexing overclaimed")
    require(m["prime_indexing_is_quantum_number_claim"] is False, "prime index cannot imply quantum status")
    require(m["one_is_prime"] is False and m["forty_nine_is_prime"] is False, "1/49 prime correction lost")
    require(p["spectral_scope"]["195_nm_to_9675_nm"] == "RESEARCH_TARGET_ONLY_NOT_DEMONSTRATED", "spectral scope overclaimed")

    pc = p["physics_constraints"]
    for key in (
        "maxwell_consistency_required", "finite_total_energy_required",
        "bounded_coupling_required", "thermal_limit_required",
        "actuator_saturation_required", "stability_or_bounded_state_evolution_required",
        "passivity_or_supplied_power_accounting_required",
        "momentum_and_force_claims_require_explicit_control_volume_balance",
    ):
        require(pc[key] is True, f"physics guard missing: {key}")

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
        "stealth achieved", "cloaking achieved", "broadband cancellation achieved",
        "195-9675 nm programmability demonstrated", "reactionless propulsion",
        "net energy from a static ambient field", "quantum behavior proven by prime indexing",
    }
    require(required_prohibitions.issubset(set(p["prohibited_claims"])), "claims prohibitions incomplete")
    require(p["contact_authority_created"] is False, "metasurface cannot create contact authority")
    return {"schema": p["schema"], "prohibited_claim_count": len(p["prohibited_claims"])}


def validate_alti() -> dict:
    p = load("materials/ws_alti_m1_msz_prime_validation.v1.json")
    require(p["schema"] == "WS-ALTI-M1-MSZ-PRIME-VALIDATION-V1", "AlTi schema drift")
    s = p["current_claim_state"]
    require(s["commercial_value_class"] == "IP_STAGE", "AlTi must remain IP-stage here")
    require(s["physical_material_performance"] == "NOT_YET_VALIDATED_BY_THIS_CONTRACT", "physical performance overclaimed")
    require(s["programmable_deposited_behavior"] == "HYPOTHESIS_REQUIRES_COUPON_VALIDATION", "programmability overclaimed")
    require(s["partner_interest"] == "NOT_ESTABLISHED_BY_INTERNAL_WORK", "partner interest overclaimed")

    stages = p["stages"]
    ids = [x["stage_id"] for x in stages]
    require(ids == [
        "A0_IP_AND_DESIGN_CUSTODY", "A1_MODELING", "A2_COUPON_BUILD",
        "A3_COUPON_CHARACTERIZATION", "A4_REPEATABILITY_AND_PROCESS_WINDOW",
        "A5_EXTERNAL_PARTNER_REPLICATION",
    ], "AlTi stage sequence drift")
    a4, a5 = stages[4], stages[5]
    require(int(a4["minimum_independent_builds"]) >= 3, "need >=3 independent AlTi builds")
    require(int(a4["minimum_coupons_per_build"]) >= 3, "need >=3 AlTi coupons/build")
    require(a5["self_close_allowed"] is False, "external AlTi replication cannot self-close")
    require(p["programmability_evidence_rule"]["internal_modeling_alone_sufficient"] is False, "modeling cannot prove programmability")
    require(len(p["programmability_evidence_rule"]["required_for_claim"]) >= 4, "programmability evidence rule incomplete")
    require(p["commercialization_boundary"]["valuation_must_not_be_upgraded_by_internal_readiness_alone"] is True, "valuation guard missing")
    require(p["contact_authority_created"] is False, "AlTi cannot create contact authority")
    return {"schema": p["schema"], "stage_count": len(stages), "minimum_repeatability_coupons": int(a4["minimum_independent_builds"]) * int(a4["minimum_coupons_per_build"])}


def validate_access() -> dict:
    p = load("security/palace_evidence_ingest_policy.v1.json")
    require(p["schema"] == "WS-PALACE-EVIDENCE-INGEST-POLICY-V1", "PALACE ingest schema drift")
    r = p["existing_role_model"]
    require(r["relay_role"] == "relay" and r["admin_role"] == "admin", "SARA role drift")
    require(r["separate_tokens_required"] is True, "relay/admin tokens must remain separate")
    modes = {x["mode"]: x for x in p["ingest_modes"]}
    require(modes["SNAPSHOT_READ"]["minimum_role"] == "relay", "snapshot read role drift")
    require(modes["SNAPSHOT_READ"]["writes_into_snapshot"] is False, "snapshot must remain immutable")
    require(modes["EVIDENCE_REGISTER"]["minimum_role"] == "admin", "evidence register must require admin")
    require(modes["EVIDENCE_REGISTER"]["writes_into_live_solver_tree"] is False, "registration cannot mutate live solver")
    require(modes["EXTERNAL_EVIDENCE_PROMOTION"]["automatic_promotion"] is False, "no automatic external promotion")
    for key, value in p["live_solver_boundary"].items():
        require(value is False, f"live solver permission must remain false: {key}")
    require(p["boeing_spirit_contact_effect"] == "NONE", "PALACE cannot affect Boeing contact gate")
    require(p["contact_authority_created"] is False, "PALACE cannot create contact authority")

    auth = (ROOT / "deployments/sara_verified_local_v1/worldshepherd_sara/auth.py").read_text(encoding="utf-8")
    for text in ('RELAY = "relay"', 'ADMIN = "admin"', 'SARA_RELAY_TOKEN', 'SARA_ADMIN_TOKEN', 'require_admin', 'hmac.compare_digest(relay, admin)'):
        require(text in auth, f"existing SARA auth guard missing: {text}")

    ing = (ROOT / "palace/ingest_anchor_snapshot.py").read_text(encoding="utf-8")
    require("--output must be outside --snapshot-root" in ing, "snapshot write guard missing")
    require("unknown anchor_id" in ing, "anchor identity guard missing")
    # Documentation may contain words such as 'launches'; reject actual common execution primitives instead.
    for primitive in ("subprocess.run", "subprocess.Popen", "os.system(", "os.exec", "shlex.split"):
        require(primitive not in ing, f"PALACE ingester execution primitive forbidden: {primitive}")
    return {"schema": p["schema"], "ingest_mode_count": len(modes), "auth_static_crosscheck": "PASS"}


def main() -> None:
    out = {
        "schema": "WS-PARALLEL-HARDWARE-DEVELOPMENT-VALIDATION-REPORT-V1",
        "metasurface": validate_metasurface(),
        "alti": validate_alti(),
        "palace_access": validate_access(),
        "evidence_effect": "INTERNAL_CONTRACT_AND_SOFTWARE_VALIDATION_ONLY",
        "physical_validation_created": False,
        "partner_validation_created": False,
        "independent_replication_created": False,
        "contact_authority_created": False,
        "boeing_spirit_contact_effect": "NONE",
        "status": "PASS",
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
