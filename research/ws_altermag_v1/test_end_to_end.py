from pathlib import Path

from research.ws_altermag_v1.benchmark_b000 import DEFAULT_MANIFEST, run


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
