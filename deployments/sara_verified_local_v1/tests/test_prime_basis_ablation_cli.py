from __future__ import annotations

import json

from worldshepherd_sara.prime_basis_ablation_cli import main


def test_cli_exports_and_verifies_hash_bound_report(tmp_path, capsys):
    output = tmp_path / "prime-ablation.json"
    assert main(["--output", str(output)]) == 0
    digest = capsys.readouterr().out.strip()
    assert digest.startswith("sha256:")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["qualification_id"] == "WS-QE-2026-PRI-001"
    assert payload["summary"]["outcome"] == "NO_GENERAL_PRIME_ADVANTAGE_OBSERVED"
    assert payload["physical_validation_performed"] is False
    assert payload["quantum_physics_claimed"] is False

    assert main(["--verify", str(output)]) == 0
    assert capsys.readouterr().out.strip() == "VALID"


def test_cli_rejects_tampered_report(tmp_path, capsys):
    output = tmp_path / "prime-ablation.json"
    assert main(["--output", str(output)]) == 0
    capsys.readouterr()

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["rank"] = 4
    output.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--verify", str(output)]) == 1
    assert capsys.readouterr().out.strip() == "INVALID"
