from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def test_base_package_import_does_not_bootstrap_same_process_sentinel_custody():
    code = (
        "import sys, worldshepherd_sara; "
        "assert 'worldshepherd_sara.infrastructure_assurance' not in sys.modules; "
        "assert 'worldshepherd_sara.infrastructure_assurance_legacy' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_production_sentinel_scripts_route_to_isolated_authority():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["ws-sentinel-infrastructure"] == "worldshepherd_sara.sentinel_authority_cli:main"
    assert scripts["ws-sentinel-readiness"] == "worldshepherd_sara.sentinel_authority_cli:main"
    assert scripts["ws-sentinel-synthetic-infrastructure"] == "worldshepherd_sara.sentinel_infrastructure_cli:main"
    assert scripts["ws-sentinel-synthetic-readiness"] == "worldshepherd_sara.sentinel_readiness_cli:main"


def test_production_authority_cli_fails_closed_without_authority(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldshepherd_sara.sentinel_authority_cli",
            "--authority-socket",
            str(tmp_path / "missing.sock"),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert '"authority_status": "FAIL_CLOSED"' in result.stdout
