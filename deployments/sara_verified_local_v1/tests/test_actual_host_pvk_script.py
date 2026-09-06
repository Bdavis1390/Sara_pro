from __future__ import annotations

import subprocess
from pathlib import Path


def test_actual_host_pvk_acceptance_script_has_valid_bash_syntax():
    script = Path("scripts/verify_actual_host_pvk.sh")
    assert script.exists()
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_actual_host_pvk_script_preserves_scientific_boundary():
    text = Path("scripts/verify_actual_host_pvk.sh").read_text(encoding="utf-8")
    assert "scientific_validation_claim=NOT_ESTABLISHED_BY_THIS_TEST" in text
    assert '"validation_state": "concept"' in text
    assert "down -v --remove-orphans" in text
    assert "WS_PVK_SHADOW_PORT" in text
