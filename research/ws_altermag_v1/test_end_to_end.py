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
    assert result["open_backend_ok"] is True
    assert result["memory_contract_ok"] is True
    assert "active Palace" in result["current_blocker"]
    assert "MemAvailable" in result["current_blocker"]
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
    assert data["selection"]["open_crosscheck"]["status"] == "SELECTED_STAGED_ISOLATED_RUNTIME_READY"
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
    assert elk["runtime_dependency_check"]["status"] == "RESOLVED_BY_STAGED_USERSPACE_RUNTIME"
    assert elk["runtime_dependency_check"]["current_missing_direct_linked_libraries"] == []
    assert elk["runtime_dependency_staging_status"] == "STAGED_USERSPACE_RUNTIME_READY"


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


def _valid_basis_summary(energy, moments=(2.5, 2.5)):
    return {
        "energy_convergence_target_achieved": True,
        "final_total_energy_ha_per_cell": energy,
        "cr_local_moment_magnitudes_muB": list(moments),
    }


def test_basis_sequencer_starts_with_rgkmax_6():
    from research.ws_altermag_v1.sequence_b000 import choose_next_basis_case

    result = choose_next_basis_case({})
    assert result["decision"] == "RUN_NEXT_BASIS_CASE"
    assert result["next_case"]["kgrid"] == [12, 12, 8]
    assert result["next_case"]["rgkmax"] == 6.0


def test_basis_sequencer_never_skips_invalid_prior_case():
    from research.ws_altermag_v1.sequence_b000 import choose_next_basis_case

    bad = _valid_basis_summary(-100.0)
    bad["energy_convergence_target_achieved"] = False
    result = choose_next_basis_case({"basis-rgkmax-6.0": bad})
    assert result["decision"] == "HOLD"
    assert result["reason"] == "EARLIER_CASE_INVALID"


def test_basis_gate_uses_highest_resolution_adjacent_pair():
    from research.ws_altermag_v1.sequence_b000 import choose_next_basis_case

    summaries = {
        "basis-rgkmax-6.0": _valid_basis_summary(-100.0000, (2.40, 2.40)),
        "basis-rgkmax-7.0": _valid_basis_summary(-100.0010, (2.50, 2.50)),
        "basis-rgkmax-8.0": _valid_basis_summary(-100.00105, (2.505, 2.504)),
    }
    result = choose_next_basis_case(summaries)
    assert result["coarse_6_to_7"]["pass"] is False
    assert result["final_7_to_8"]["pass"] is True
    assert result["decision"] == "BASIS_GATE_PASS"
    assert result["accepted_rgkmax"] == 8.0


def test_basis_gate_holds_when_final_pair_not_converged():
    from research.ws_altermag_v1.sequence_b000 import choose_next_basis_case

    summaries = {
        "basis-rgkmax-6.0": _valid_basis_summary(-100.0000),
        "basis-rgkmax-7.0": _valid_basis_summary(-100.00005),
        "basis-rgkmax-8.0": _valid_basis_summary(-100.00100, (2.53, 2.47)),
    }
    result = choose_next_basis_case(summaries)
    assert result["decision"] == "HOLD"
    assert result["reason"] == "BASIS_NOT_CONVERGED_AT_RGKMAX_8"


def test_fermi_export_contract_is_spin_resolved_and_fail_closed():
    from research.ws_altermag_v1.fermi_export_b000 import validate_contract

    result = validate_contract()
    assert result["contract_pass"] is True
    assert result["task"] == 102
    assert result["expected_outputs"] == ["FERMISURF_DN.bxsf", "FERMISURF_UP.bxsf"]
    assert result["quantum_oscillation_stage"] == "REQUIRES_ORBIT_EXTRACTOR"
    assert len(result["template_sha256"]) == 64


def test_fermi_export_template_uses_task_102_and_plot3d_grid():
    from research.ws_altermag_v1.fermi_export_b000 import render_fermi_export

    rendered = render_fermi_export(
        species_path="/var/tmp/staged/species/",
        np3d=(43, 43, 28),
        rgkmax=8.0,
    )
    assert "tasks\n  102\n" in rendered
    assert "plot3d\n  0.0 0.0 0.0" in rendered
    assert "  43 43 28\n" in rendered
    assert "sppath\n  '/var/tmp/staged/species/'" in rendered


def test_qo_backend_contract_blocks_direct_elk_to_pyskeaf():
    from research.ws_altermag_v1.qo_contract import validate_qo_contract

    result = validate_qo_contract()
    assert result["contract_pass"] is True
    assert result["wheel_pinned"] is True
    assert result["paper_native_fail_closed"] is True
    assert result["format_adapter_required"] is True
    assert result["direct_elk_to_pyskeaf_allowed"] is False
    assert result["decision"].startswith("BLOCK_QO_EXTRACTION")
    assert result["synthetic_adapter_validated"] is True


def _synthetic_elk_task102_bxsf():
    import numpy as np

    base1 = np.arange(8, dtype=float).reshape(2, 2, 2) / 100.0
    base2 = (np.arange(8, dtype=float).reshape(2, 2, 2) + 10.0) / 100.0

    def periodic(base):
        out = np.empty((3, 3, 3), dtype=float)
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    out[i, j, k] = base[i % 2, j % 2, k % 2]
        return out

    bands = [periodic(base1), periodic(base2)]
    lines = [
        " BEGIN_INFO",
        " Fermi Energy: 0.0000000000",
        " END_INFO",
        " BEGIN_BLOCK_BANDGRID_3D",
        " band_energies",
        " BANDGRID_3D_BANDS",
        " 2",
        " 3 3 3",
        " 0.0 0.0 0.0",
        " 6.283185307179586 0.0 0.0",
        " 0.0 6.283185307179586 0.0",
        " 0.0 0.0 6.283185307179586",
    ]
    for idx, arr in enumerate(bands, start=1):
        lines.append(f" BAND: {idx}")
        flat = arr.reshape(-1)
        for j in range(0, len(flat), 6):
            lines.append(" ".join(str(v) for v in flat[j:j+6]))
    lines += [" END_BANDGRID_3D", " END_BLOCK_BANDGRID_3D"]
    return "\n".join(lines) + "\n"


def test_bxsf_adapter_splits_bands_strips_periodic_endpoint_and_converts_units(tmp_path):
    from research.ws_altermag_v1.elk_bxsf_adapter import adapt_elk_task102

    src = tmp_path / "FERMISURF_UP.bxsf"
    src.write_text(_synthetic_elk_task102_bxsf(), encoding="utf-8")
    outdir = tmp_path / "out"
    result = adapt_elk_task102(src, outdir, spin_label="UP")

    assert result["output_band_count"] == 2
    assert result["source_dims"] == [3, 3, 3]
    assert all(item["dims"] == [2, 2, 2] for item in result["outputs"])

    text = (outdir / "UP_band_0001.bxsf").read_text(encoding="utf-8")
    assert " 2 2 2\n" in text
    assert "1.000000000000 0.000000000000 0.000000000000" in text
    # First nonzero source energy is 0.01 Hartree -> 0.02 Rydberg.
    assert "2.000000000000E-02" in text


def test_bxsf_adapter_fails_closed_without_periodic_endpoint(tmp_path):
    from research.ws_altermag_v1.elk_bxsf_adapter import adapt_elk_task102

    lines = _synthetic_elk_task102_bxsf().splitlines()
    start = lines.index(" BAND: 1") + 1
    stop = lines.index(" BAND: 2")
    tokens = []
    for line in lines[start:stop]:
        tokens.extend(line.split())
    assert len(tokens) == 27
    tokens[-1] = "9.99"

    rebuilt = lines[:start]
    for i in range(0, len(tokens), 6):
        rebuilt.append(" ".join(tokens[i:i+6]))
    rebuilt.extend(lines[stop:])
    src = tmp_path / "bad.bxsf"
    src.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")

    import pytest
    with pytest.raises(ValueError):
        adapt_elk_task102(src, tmp_path / "out", spin_label="UP")


def test_qo_tilted_plane_angle_mapping_matches_reported_alpha22_point():
    from research.ws_altermag_v1.qo_angles_b000 import alpha_to_theta_phi

    theta, phi = alpha_to_theta_phi(22.0, 14.0)
    assert abs(theta - 84.8) <= 0.15
    assert abs(phi - 21.4) <= 0.15


def test_qo_angle_plan_contains_fig3_source_orientations():
    from research.ws_altermag_v1.qo_angles_b000 import build_angle_plan

    plan = build_angle_plan()
    assert plan["validation"]["pass"] is True
    assert len(plan["angles"]) == 12
    assert plan["angles"][-1]["alpha_deg"] == 0.0
    assert abs(plan["angles"][-1]["theta_deg"] - 90.0) <= 1.0e-12
    assert abs(plan["angles"][-1]["phi_deg"]) <= 1.0e-12


def test_band_alignment_declared_shifts_convert_to_rydberg():
    from research.ws_altermag_v1.band_alignment_b000 import declared_shift_rydberg

    dog = declared_shift_rydberg("dogbone_hole")
    web = declared_shift_rydberg("web_electron")
    assert dog < 0.0
    assert web > 0.0
    assert abs(dog * 13.605693122994 + 0.11) <= 1.0e-12
    assert abs(web * 13.605693122994 - 0.015) <= 1.0e-12


def test_band_alignment_preserves_raw_and_shifts_single_band(tmp_path):
    from research.ws_altermag_v1.elk_bxsf_adapter import adapt_elk_task102
    from research.ws_altermag_v1.band_alignment_b000 import shift_single_band_bxsf, declared_shift_rydberg

    src = tmp_path / "FERMISURF_UP.bxsf"
    src.write_text(_synthetic_elk_task102_bxsf(), encoding="utf-8")
    adapted = tmp_path / "adapted"
    adapt_elk_task102(src, adapted, spin_label="UP")

    raw = adapted / "UP_band_0001.bxsf"
    raw_before = raw.read_text(encoding="utf-8")
    aligned = tmp_path / "aligned" / "UP_band_0001.bxsf"
    receipt = shift_single_band_bxsf(raw, aligned, sheet_class="dogbone_hole")

    assert receipt["raw_preserved"] is True
    assert raw.read_text(encoding="utf-8") == raw_before
    assert aligned.exists()
    assert receipt["shifted_energy_count"] == 8
    assert abs(receipt["shift_Ry"] - declared_shift_rydberg("dogbone_hole")) <= 1.0e-15
    assert receipt["output_sha256"] != receipt["input_sha256"]


def _perfect_qo_computed_fixture():
    import json
    from pathlib import Path

    ref = json.loads(Path(
        "research/ws_altermag_v1/manifests/qo_reference_targets_b000.json"
    ).read_text(encoding="utf-8"))
    return {
        "lane": "RAW",
        "provenance": {"fixture": "perfect-reference-copy"},
        "angles": [
            {
                "alpha_deg": row["alpha_deg"],
                "classification": "dogbone",
                "dogbone_frequencies_kT": row["observed_frequencies_kT"],
            }
            for row in ref["targets"]
        ],
    }


def test_qo_comparator_accepts_complete_perfect_fixture():
    from research.ws_altermag_v1.qo_compare_b000 import compare_qo

    result = compare_qo(_perfect_qo_computed_fixture())
    assert result["pass"] is True
    assert result["decision"] == "QO_REFERENCE_MATCH"
    assert result["coverage"] == 12
    assert result["overall_pair_mae_kT"] == 0.0
    assert result["nodes_pass"] is True


def test_qo_comparator_fails_closed_on_missing_angle():
    from research.ws_altermag_v1.qo_compare_b000 import compare_qo

    fixture = _perfect_qo_computed_fixture()
    fixture["angles"].pop()
    result = compare_qo(fixture)
    assert result["pass"] is False
    assert result["decision"] == "HOLD"
    assert 0.0 in result["missing_alpha_deg"]


def test_qo_comparator_rejects_broken_node():
    from research.ws_altermag_v1.qo_compare_b000 import compare_qo

    fixture = _perfect_qo_computed_fixture()
    node = next(x for x in fixture["angles"] if x["alpha_deg"] == -60.0)
    node["dogbone_frequencies_kT"] = [3.0, 3.3]
    result = compare_qo(fixture)
    assert result["pass"] is False
    assert result["nodes_pass"] is False


def test_pyskeaf_freqvsangle_parser_preserves_writer_fields(tmp_path):
    from research.ws_altermag_v1.pyskeaf_output_b000 import parse_freqvsangle

    p = tmp_path / "qo_EF_0_freqvsangle.out"
    p.write_text(
        " Azimuthal(deg),  Polar(deg),  Freq(kT),  mstar(me),  Curv(kTA2),  Type(+e-h),  NumOrbCopy\n"
        "      84.800405,    21.406417,  3.410000E+00,  1.200000E+00,  2.000000E-01,      -1.000,           2\n",
        encoding="utf-8",
    )
    result = parse_freqvsangle(p)
    assert result["row_count"] == 1
    orbit = result["orbits"][0]
    assert abs(orbit["writer_theta_deg"] - 84.800405) <= 1.0e-12
    assert abs(orbit["writer_phi_deg"] - 21.406417) <= 1.0e-12
    assert abs(orbit["frequency_kT"] - 3.41) <= 1.0e-12
    assert orbit["orbit_type"] == -1.0
    assert orbit["num_orbit_copies"] == 2


def test_orbit_selection_contract_starts_fail_closed():
    from pathlib import Path
    from research.ws_altermag_v1.pyskeaf_output_b000 import validate_selection_manifest

    p = Path("research/ws_altermag_v1/manifests/orbit_selection_b000.json")
    result = validate_selection_manifest(p)
    assert result["assignment_count"] == 0
    assert result["dogbone_ready"] is False
    assert result["decision"] == "BLOCK_DOGBONE_QO_SELECTION"


def test_first_case_completion_requires_energy_and_cr_moment_evidence():
    from research.ws_altermag_v1.first_case_runner import evaluate_completed_run

    summary = {
        "energy_convergence_target_achieved": True,
        "parse_complete_enough_for_energy_gate": True,
        "parse_complete_enough_for_moment_gate": True,
    }
    result = evaluate_completed_run(return_code=0, timed_out=False, summary=summary)
    assert result["usable_for_sequence"] is True
    assert result["decision"] == "CASE_READY_FOR_SEQUENCE"


def test_first_case_completion_holds_on_incomplete_moment_evidence():
    from research.ws_altermag_v1.first_case_runner import evaluate_completed_run

    summary = {
        "energy_convergence_target_achieved": True,
        "parse_complete_enough_for_energy_gate": True,
        "parse_complete_enough_for_moment_gate": False,
    }
    result = evaluate_completed_run(return_code=0, timed_out=False, summary=summary)
    assert result["usable_for_sequence"] is False
    assert "CR_LOCAL_MOMENT_EVIDENCE_INCOMPLETE" in result["blockers"]


def test_convergence_resource_gate_declares_memory_headroom():
    import json

    path = Path("research/ws_altermag_v1/manifests/convergence_b000.json")
    gate = json.loads(path.read_text(encoding="utf-8"))["resource_gate"]
    assert gate["minimum_mem_available_GB"] >= 1.0
    assert gate["minimum_swap_free_GB"] >= 1.0
    assert "engineering" in gate["memory_threshold_note"].lower()


def test_execution_gate_memory_snapshot_has_required_fields():
    from research.ws_altermag_v1.execution_gate import _memory_snapshot

    snap = _memory_snapshot()
    assert set(snap) == {"MemAvailable_GB", "SwapFree_GB"}
    assert snap["MemAvailable_GB"] >= 0.0
    assert snap["SwapFree_GB"] >= 0.0


def _palace_tsv(path, rows):
    path.write_text(
        "anchor_id\truntime_name\texit_code\tstatus\n"
        + "".join(f"{i}\tA{i:03d}-fixture\t{rc}\t{status}\n" for i, rc, status in rows),
        encoding="utf-8",
    )


def test_palace_queue_gate_blocks_between_completed_runs(tmp_path):
    from research.ws_altermag_v1.palace_queue_gate import inspect_palace_queue

    p = tmp_path / "job-results.tsv"
    _palace_tsv(p, [(27, 0, "EXIT0"), (28, 0, "EXIT0")])
    r = inspect_palace_queue(p, range(27, 55))
    assert r["queue_clear"] is False
    assert r["completed_ids"] == [27, 28]
    assert r["missing_ids"][0] == 29
    assert r["missing_ids"][-1] == 54
    assert r["decision"] == "BLOCK_PALACE_QUEUE_INCOMPLETE"


def test_palace_queue_gate_requires_all_expected_receipts(tmp_path):
    from research.ws_altermag_v1.palace_queue_gate import inspect_palace_queue

    p = tmp_path / "job-results.tsv"
    _palace_tsv(p, [(27, 0, "EXIT0"), (28, 0, "EXIT0")])
    r = inspect_palace_queue(p, [27, 28])
    assert r["queue_clear"] is True
    assert r["decision"] == "PALACE_QUEUE_CLEAR"


def test_palace_queue_gate_rejects_failure_and_duplicate(tmp_path):
    from research.ws_altermag_v1.palace_queue_gate import inspect_palace_queue

    p = tmp_path / "job-results.tsv"
    _palace_tsv(p, [(27, 0, "EXIT0"), (28, 3, "ERROR"), (28, 0, "EXIT0")])
    r = inspect_palace_queue(p, [27, 28])
    assert r["queue_clear"] is False
    assert r["duplicate_ids"] == [28]
    assert r["decision"] == "BLOCK_PALACE_QUEUE_INCOMPLETE"


def test_palace_queue_gate_missing_receipt_fails_closed(tmp_path):
    from research.ws_altermag_v1.palace_queue_gate import inspect_palace_queue

    r = inspect_palace_queue(tmp_path / "absent.tsv", [27, 28])
    assert r["receipt_present"] is False
    assert r["queue_clear"] is False
    assert r["missing_ids"] == [27, 28]


def _palace_quality_fixture(tmp_path, stdout):
    work = tmp_path / "work"
    case = work / "A027-fixture"
    (case / "palace-output").mkdir(parents=True)
    (case / "palace-output" / "port-S.csv").write_text(
        "frequency,s11\n9.20,1\n9.21,2\n9.22,3\n", encoding="utf-8"
    )
    (case / "stdout.txt").write_text(stdout, encoding="utf-8")
    return work


def test_palace_quality_audit_provisional_pass_not_physics_claim(tmp_path):
    from research.ws_altermag_v1.palace_quality_audit import audit_case

    work = _palace_quality_fixture(tmp_path, "GMRES solver converged in 15 iterations\n")
    result = audit_case(
        work, 27, {"exit_code": "0", "status": "EXIT0"},
        expected_points=3
    )
    assert result["grid_complete"] is True
    assert result["gmres_nonconvergence_count"] == 0
    assert result["decision"] == "PROVISIONAL_SOLVER_LOG_PASS"
    assert "not a mesh convergence" in result["claim_boundary"]


def test_palace_quality_audit_exit0_with_gmres_warning_holds(tmp_path):
    from research.ws_altermag_v1.palace_quality_audit import audit_case

    work = _palace_quality_fixture(
        tmp_path, "GMRES solver did NOT converge in 200 iterations\n"
        "Linear solver did not converge\n",
    )
    result = audit_case(
        work, 27, {"exit_code": "0", "status": "EXIT0"},
        expected_points=3
    )
    assert result["grid_complete"] is True
    assert result["receipt_exit0"] is True
    assert result["gmres_nonconvergence_count"] == 1
    assert result["decision"] == "HOLD_SOLVER_NONCONVERGENCE_REVIEW"


def test_palace_residual_profile_extracts_per_frequency_and_statistics(tmp_path):
    from research.ws_altermag_v1.palace_residual_profile import (
        summarize_nonconvergence_log,
    )

    p = tmp_path / "stdout.txt"
    p.write_text(
        "It 1/3: ω/2π = 9.200e+00 GHz\n"
        "GMRES solver did NOT converge in 200 iterations\n"
        "Linear solver did not converge, norm(Ax-b)/norm(b) = 1.313e-03 (norm(b) = 2.419e+01)!\n"
        "It 2/3: ω/2π = 9.210e+00 GHz\n"
        "GMRES solver did NOT converge in 200 iterations\n"
        "Linear solver did not converge, norm(Ax-b)/norm(b) = 4.948e-04 (norm(b) = 2.421e+01)!\n"
        "It 3/3: ω/2π = 9.220e+00 GHz\n"
        "GMRES solver converged in 15 iterations\n",
        encoding="utf-8",
    )
    r = summarize_nonconvergence_log(p)
    assert r["total_frequency_points_declared"] == 3
    assert r["frequency_points_parsed"] == 3
    assert r["nonconverged_frequency_points"] == 2
    assert r["residual_max"] == 1.313e-3
    assert r["residual_median"] == (1.313e-3 + 4.948e-4) / 2
    assert r["worst_twelve"][0]["step"] == 1
    assert r["decision"] == "HOLD_SOLVER_NONCONVERGENCE_REVIEW"


def test_palace_residual_profile_refuses_inconsistent_warning(tmp_path):
    import pytest
    from research.ws_altermag_v1.palace_residual_profile import (
        summarize_nonconvergence_log,
    )

    p = tmp_path / "stdout.txt"
    p.write_text(
        "It 1/1: ω/2π = 9.200e+00 GHz\n"
        "GMRES solver did NOT converge in 200 iterations\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="inconsistent GMRES"):
        summarize_nonconvergence_log(p)


def test_palace_residual_profile_refuses_noncontiguous_frequency_steps(tmp_path):
    import pytest
    from research.ws_altermag_v1.palace_residual_profile import (
        summarize_nonconvergence_log,
    )

    p = tmp_path / "stdout.txt"
    p.write_text(
        "It 1/3: ω/2π = 9.200e+00 GHz\n"
        "GMRES solver converged in 15 iterations\n"
        "It 3/3: ω/2π = 9.220e+00 GHz\n"
        "GMRES solver converged in 15 iterations\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Non-contiguous"):
        summarize_nonconvergence_log(p)
