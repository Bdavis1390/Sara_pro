from pathlib import Path

from research.ws_altermag_v1.benchmark_b000 import DEFAULT_MANIFEST, run
from research.ws_altermag_v1.reference_b000 import DEFAULT_REFERENCE, validate_reference


def test_b000_synthetic_end_to_end():
    result = run(DEFAULT_MANIFEST)
    assert result["pass"] is True
    assert result["inference"]["identifiable"] is True
    assert result["hypotheses"]["preferred"] == "H1_AM_PLUS_RELAXATION"
    assert result["hypotheses"]["delta_aic_h0_minus_h1"] >= 10.0
    assert "PROVEN INTERNALLY" in result["evidence"]["allowed_claims"]
    assert "IMPLEMENTED IN SOFTWARE" in result["evidence"]["allowed_claims"]
    assert "LAB VALIDATED" in result["evidence"]["blocked_promotions"]
    assert "DEVICE QUALIFIED" in result["evidence"]["blocked_promotions"]


def test_digest_is_deterministic():
    a = run(DEFAULT_MANIFEST)
    b = run(Path(DEFAULT_MANIFEST))
    assert a["experiment_digest"] == b["experiment_digest"]


def test_claim_boundary_is_explicit():
    result = run(DEFAULT_MANIFEST)
    boundary = result["claim_boundary"].lower()
    assert "synthetic" in boundary
    assert "does not validate" in boundary


def test_b000_literature_reference_adapter():
    result = validate_reference(DEFAULT_REFERENCE)
    assert result["pass"] is True
    assert result["status"] == "SUPPORTED BY LITERATURE"
    assert abs(result["representative_split_kT_recomputed"] - 0.41) <= 1.0e-12
    assert all(item["is_nodal"] for item in result["phi_nodal_checks"])
    assert all(item["is_nodal"] for item in result["theta_nodal_checks"])
    assert "does not independently reproduce" in result["claim_boundary"].lower()


def test_source_peak_picker():
    from research.ws_altermag_v1.source_data_b000 import _two_dominant_peaks

    xs = [3.20, 3.30, 3.40, 3.41, 3.42, 3.55, 3.70, 3.81, 3.82, 3.83, 3.95]
    ys = [0.0, 0.1, 0.6, 1.0, 0.5, 0.05, 0.08, 0.4, 0.8, 0.3, 0.0]
    peaks = _two_dominant_peaks(xs, ys, 3.25, 3.95, 0.20)
    assert len(peaks) == 2
    assert abs(peaks[0]["frequency_kT"] - 3.41) <= 1.0e-12
    assert abs(peaks[1]["frequency_kT"] - 3.82) <= 1.0e-12


def test_source_manifest_is_content_pinned():
    import json
    from research.ws_altermag_v1.source_data_b000 import DEFAULT_MANIFEST

    manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["dataset"]["repository_doi"] == "10.17863/CAM.131869"
    assert len(manifest["dataset"]["archive_sha256"]) == 64
    assert len(manifest["analysis"]["member_sha256"]) == 64


def test_integrity_audit_pair_contract():
    from research.ws_altermag_v1.source_integrity_b000 import PAIRS

    assert ("fig2b.csv", "fig2f.csv", "simulated_frequency_profiles") in PAIRS
    assert ("fig2c.csv", "fig2g.csv", "selected_torque_traces") in PAIRS
    assert ("fig2d.csv", "fig2h.csv", "selected_fft_spectra") in PAIRS


def test_angular_manifest_contract():
    import json
    from research.ws_altermag_v1.source_data_b000 import DEFAULT_MANIFEST

    manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    angular = manifest["analysis_angular"]
    assert angular["declared_node_alpha_deg"] == [-60, 0]
    assert angular["exported_dft_x_from_alpha"] == "x_deg = alpha_deg + 90"
    assert angular["minimum_off_node_matches"] >= 8
    assert angular["minimum_split_correlation"] >= 0.8


def test_dft_contract_is_complete_but_not_executed():
    from research.ws_altermag_v1.dft_contract import validate_contract

    result = validate_contract()
    assert result["contract_complete"] is True
    assert result["execution_status"] == "PROPOSED_NOT_EXECUTED"
    assert result["resource_clearance"] is False
    assert "active Palace" in result["current_blocker"]
    assert "No first-principles CrSb calculation" in result["claim_boundary"]


def test_crsb_structure_contract():
    from research.ws_altermag_v1.structure_b000 import validate_structure

    result = validate_structure()
    assert result["pass"] is True
    assert result["stoichiometry"] == {"Cr": 2, "Sb": 2}
    assert result["compensated_initialization"] is True
    assert all(result["position_checks"].values())


def test_backend_selection_stays_fail_closed():
    import json

    path = Path("research/ws_altermag_v1/manifests/backend_selection_b000.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["selection"]["open_crosscheck"]["backend"] == "Elk"
    assert data["selection"]["open_crosscheck"]["status"] == "SELECTED_NOT_INSTALLED"
    assert data["resource_snapshot"]["palace_active"] is True
    assert data["resource_snapshot"]["install_now"] is False


def test_open_backend_package_is_content_pinned():
    import json

    path = Path("research/ws_altermag_v1/manifests/backend_selection_b000.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    elk = data["selection"]["open_crosscheck"]
    assert elk["package"] == "elk-lapw"
    assert elk["ubuntu_jammy_candidate"] == "7.2.42-2"
    assert elk["package_sha256"] == "6c838f8d98e5aeae80caa2aaf4fb1817e5d1f74512e1015669a039b5e089bb4a"
    assert len(elk["extracted_binary_sha256"]) == 64
    assert len(elk["species_sha256"]["Cr.in"]) == 64
    assert len(elk["species_sha256"]["Sb.in"]) == 64
    assert elk["staging_status"] == "DOWNLOADED_AND_EXTRACTED_NOT_INSTALLED"
    assert elk["runtime_dependency_check"]["status"] == "NOT_RUNNABLE_FROM_EXTRACTED_TREE_YET"


def test_elk_template_encodes_reference_geometry_without_execution():
    from research.ws_altermag_v1.elk_input_b000 import render_elk_template

    rendered = render_elk_template()
    assert "NOT EXECUTION APPROVED" in rendered
    assert "xctype\n  20" in rendered
    assert "spinpol\n  .true." in rendered
    assert "ngridk\n  43 43 28" in rendered
    assert "'Cr.in'" in rendered
    assert "'Sb.in'" in rendered
    assert "1.00000000e-03" in rendered
    assert "-1.00000000e-03" in rendered

def test_convergence_plan_is_deterministic_and_reference_last():
    from research.ws_altermag_v1.convergence_b000 import build_plan

    plan = build_plan()
    assert plan["execution_status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["case_count"] == 8
    assert plan["cases"][0]["kind"] == "basis"
    assert plan["cases"][-1]["kind"] == "reference"
    assert plan["cases"][-1]["kgrid"] == [43, 43, 28]
    assert plan["cases"][-1]["rgkmax"] == 8.0
    assert all(len(case["template_sha256"]) == 64 for case in plan["cases"])


def test_elk_template_supports_convergence_parameters():
    from research.ws_altermag_v1.elk_input_b000 import render_elk_template

    rendered = render_elk_template(ngridk=(12, 12, 8), rgkmax=7.0)
    assert "rgkmax\n  7.000000" in rendered
    assert "ngridk\n  12 12 8" in rendered
    assert "NOT EXECUTION APPROVED" in rendered


def test_staged_runtime_dependency_packages_are_pinned():
    import json

    path = Path("research/ws_altermag_v1/manifests/backend_selection_b000.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    elk = data["selection"]["open_crosscheck"]
    deps = elk["runtime_dependencies_staged"]
    assert elk["runtime_dependency_staging_status"] == "MISSING_DEPENDENCY_PACKAGES_DOWNLOADED_NOT_INSTALLED"
    assert deps["libopenmpi3"]["version"] == "4.1.2-2ubuntu1"
    assert deps["libopenmpi3"]["package_sha256"] == "25fc67e365e70abd06146962e97fbb0aead26403f36ba59b41f63954c768d352"
    assert deps["libxc9"]["version"] == "5.1.7-1ubuntu1"
    assert deps["libxc9"]["package_sha256"] == "d96bb2c83ff66ac71eab15fe84c5995a9a1313f58074bf70efdb08e9c1b300db"


def test_startup_sanity_transcript_is_bounded():
    from research.ws_altermag_v1.startup_sanity_b000 import evaluate_transcript

    stdout = "\nElk code version 7.2.42 started\n\nError(readinput): error opening elk.in\n"
    result = evaluate_transcript(stdout, info_out_exists=False)
    assert result["pass"] is True
    assert result["version_started"] is True
    assert result["expected_no_input_stop"] is True


def test_startup_sanity_rejects_real_run_artifact():
    from research.ws_altermag_v1.startup_sanity_b000 import evaluate_transcript

    stdout = "\nElk code version 7.2.42 started\n\nError(readinput): error opening elk.in\n"
    result = evaluate_transcript(stdout, info_out_exists=True)
    assert result["pass"] is False


def test_elk_template_accepts_isolated_species_path():
    from research.ws_altermag_v1.elk_input_b000 import render_elk_template

    rendered = render_elk_template(
        ngridk=(12, 12, 8),
        rgkmax=6.0,
        species_path="/var/tmp/staged/species/",
    )
    assert "sppath\n  '/var/tmp/staged/species/'" in rendered
    assert "ngridk\n  12 12 8" in rendered
    assert "rgkmax\n  6.000000" in rendered


def test_first_case_is_cheapest_declared_basis_case():
    import json
    from research.ws_altermag_v1.convergence_b000 import DEFAULT_PLAN
    from research.ws_altermag_v1.first_case_runner import _first_case

    plan = json.loads(DEFAULT_PLAN.read_text(encoding="utf-8"))
    case = _first_case(plan)
    assert case["kgrid"] == [12, 12, 8]
    assert case["rgkmax"] == 6.0


def test_elk_info_parser_handles_energy_and_local_moments():
    from research.ws_altermag_v1.elk_output_b000 import parse_info_out

    sample = """
      -123.4567890000 : total energy per unit cell

      Moments :
       interstitial                 :  0.0000000000
       muffin-tins
       species : 1 (Cr)
       atom 1                       :  2.5000000000
       atom 2                       : -2.5000000000
       species : 2 (Sb)
       atom 1                       :  0.0100000000
       atom 2                       : -0.0100000000
       total in muffin-tins         :  0.0000000000
       total moment                 :  0.0000000000

      Absolute change in total energy (target)   :  5.0E-07 ( 1.0E-06 )
      Energy convergence target achieved
    """
    result = parse_info_out(sample)
    assert abs(result["total_energy_ha_per_cell"] + 123.456789) <= 1.0e-12
    assert result["total_moment_muB"] == [0.0]
    assert result["total_moment_magnitude_muB"] == 0.0
    assert result["cr_local_moment_magnitudes_muB"] == [2.5, 2.5]
    assert abs(result["energy_change_ha"] - 5.0e-7) <= 1.0e-15
    assert result["energy_convergence_target_achieved"] is True


def test_momentm_parser_uses_one_scalar_per_iteration():
    from research.ws_altermag_v1.elk_output_b000 import parse_momentm_out

    result = parse_momentm_out("0.010\n0.005\n0.001\n")
    assert result["iteration_count"] == 3
    assert result["values_muB"] == [0.01, 0.005, 0.001]
    assert result["final_total_moment_magnitude_muB"] == 0.001


def test_convergence_evaluator_requires_energy_and_cr_local_moments():
    from research.ws_altermag_v1.convergence_eval import compare_metrics

    lower = {
        "final_total_energy_ha_per_cell": -100.000000,
        "cr_local_moment_magnitudes_muB": [2.500, 2.500],
    }
    higher = {
        "final_total_energy_ha_per_cell": -100.000050,
        "cr_local_moment_magnitudes_muB": [2.505, 2.504],
    }
    result = compare_metrics(
        lower,
        higher,
        energy_mev_per_atom_max=1.0,
        cr_moment_muB_delta_max=0.01,
    )
    assert result["energy_pass"] is True
    assert result["moment_pass"] is True
    assert result["decision"] == "ADVANCE"


def test_convergence_evaluator_fails_closed_when_moments_missing():
    from research.ws_altermag_v1.convergence_eval import compare_metrics

    result = compare_metrics(
        {"final_total_energy_ha_per_cell": -100.0, "cr_local_moment_magnitudes_muB": []},
        {"final_total_energy_ha_per_cell": -100.0, "cr_local_moment_magnitudes_muB": []},
        energy_mev_per_atom_max=1.0,
        cr_moment_muB_delta_max=0.01,
    )
    assert result["energy_pass"] is True
    assert result["moment_pass"] is False
    assert result["decision"] == "HOLD"
