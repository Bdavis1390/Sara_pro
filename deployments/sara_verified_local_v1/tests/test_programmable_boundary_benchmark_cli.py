from __future__ import annotations

import json

from worldshepherd_sara.programmable_boundary_benchmark_cli import main


def test_cli_exports_and_verifies_simulation_report(tmp_path, capsys):
    output = tmp_path / "programmable-boundary.json"
    assert main(["--output", str(output)]) == 0
    digest = capsys.readouterr().out.strip()
    assert digest.startswith("sha256:")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["qualification_id"] == "WS-QE-2026-EMB-001"
    assert payload["capability_status"] == "SIMULATED_ONLY"
    assert payload["summary"]["expected_control_behavior_observed"] is True
    assert payload["laboratory_validation_performed"] is False
    assert payload["stealth_or_cloaking_validated"] is False
    assert payload["operational_validation_performed"] is False

    assert main(["--verify", str(output)]) == 0
    assert capsys.readouterr().out.strip() == "VALID"


def test_cli_rejects_tampered_report(tmp_path, capsys):
    output = tmp_path / "programmable-boundary.json"
    assert main(["--output", str(output)]) == 0
    capsys.readouterr()

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["tile_spacing_wavelengths"] = 0.4
    output.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--verify", str(output)]) == 1
    assert capsys.readouterr().out.strip() == "INVALID"
