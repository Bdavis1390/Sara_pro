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
