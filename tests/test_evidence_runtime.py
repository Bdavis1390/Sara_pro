from worldshepherd_sara.evidence_server import app


def test_evidence_routes_are_registered_before_legacy_mount():
    paths = [getattr(route, "path", None) for route in app.routes]
    assert "/v1/evidence/experiments" in paths
    assert "/v1/evidence/claims" in paths
    assert "/v1/evidence/calibrations" in paths
    assert "/v1/evidence/calibrations/{calibration_id}" in paths
    assert "/v1/evidence/materials" in paths
    assert "/v1/evidence/materials/{material_batch_id}" in paths
    assert "/v1/evidence/export" in paths
    assert "/v1/evidence/metrics" in paths

    evidence_index = paths.index("/v1/evidence/experiments")
    mount_indexes = [
        index
        for index, route in enumerate(app.routes)
        if route.__class__.__name__ == "Mount"
    ]
    assert mount_indexes
    assert evidence_index < min(mount_indexes)


def test_capabilities_route_is_exposed_before_mount():
    paths = [getattr(route, "path", None) for route in app.routes]
    assert "/v1/capabilities" in paths
