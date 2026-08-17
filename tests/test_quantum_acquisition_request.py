from worldshepherd_sara.quantum_acquisition_request import (
    build_acquisition_request,
    build_all_acquisition_requests,
    render_request_markdown,
)


def test_sara_first_hardware_request_contains_gate_critical_fields():
    request = build_acquisition_request("SARA-QRF", "SARA-QRF-EXT-01")

    assert request.from_stage == "integrated_simulation"
    assert request.to_stage == "single_external_hardware"
    assert ("qpu_execution", 1) in request.evidence_minimums
    for field in (
        "backend_or_device",
        "job_or_run_id",
        "result_digest",
        "latency_seconds",
        "cost_usd",
        "metadata.backend_properties_digest",
        "metadata.campaign_gate_id",
        "metadata.queue_seconds",
        "metadata.test_protocol_digest",
    ):
        assert field in request.required_record_fields


def test_physical_metrology_request_requires_null_control_structure():
    request = build_acquisition_request("WS-EM-PROPULSION", "WS-EM-PROPULSION-EXT-07")

    assert ("physical_metrology", 5) in request.evidence_minimums
    assert "metadata.null_controls_completed" in request.required_record_fields
    assert "metadata.null_matrix_digest" in request.required_record_fields
    assert "WS-EMP-PROPULSION-CLAIM-GATE-SEPARATE" in request.preconditions


def test_every_campaign_gate_has_one_acquisition_request():
    requests = build_all_acquisition_requests()
    ids = [request.request_id for request in requests]

    assert len(ids) == len(set(ids))
    assert len(ids) >= 50
    assert "REQ-SARA-QRF-EXT-01" in ids
    assert "REQ-WS-GLOB-EXT-08" in ids


def test_markdown_request_is_explicitly_a_template_not_evidence():
    request = build_acquisition_request("WS-APNT", "WS-APNT-EXT-02")
    markdown = render_request_markdown(request, organization="Candidate sensor partner")

    assert "Candidate sensor partner" in markdown
    assert "quantum_sensor" in markdown
    assert "calibration_id" in markdown
    assert "truth_reference_id" in markdown
    assert "not evidence" in markdown.lower()
