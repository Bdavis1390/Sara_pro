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
