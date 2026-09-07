from __future__ import annotations

import json

from worldshepherd_sara.programmable_boundary_robustness_cli import main


def test_cli_exports_and_verifies_robustness_report(tmp_path, capsys):
    output = tmp_path / "programmable-boundary-robustness.json"
    assert main(["--output", str(output)]) == 0
    digest = capsys.readouterr().out.strip()
    assert digest.startswith("sha256:")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["qualification_id"] == "WS-QE-2026-EMB-002"
    assert payload["capability_status"] == "SIMULATED_ONLY"
    assert payload["summary"]["outcome"] == "NO_ROBUSTNESS_PROMOTION"
    assert payload["summary"]["nominal_case_count"] == 36
    assert payload["laboratory_validation_performed"] is False
    assert payload["operational_validation_performed"] is False

    assert main(["--verify", str(output)]) == 0
    assert capsys.readouterr().out.strip() == "VALID"


def test_cli_rejects_tampered_robustness_report(tmp_path, capsys):
    output = tmp_path / "programmable-boundary-robustness.json"
    assert main(["--output", str(output)]) == 0
    capsys.readouterr()

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["gate"]["minimum_nominal_pass_fraction"] = 0.50
    output.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--verify", str(output)]) == 1
    assert capsys.readouterr().out.strip() == "INVALID"
