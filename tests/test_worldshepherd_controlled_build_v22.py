import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v22", ROOT / "tools/worldshepherd_controlled_build_v22.py")
mod = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)


def write_repo(tmp_path: Path):
    d = tmp_path / "deployments/sara_verified_local_v1"; d.mkdir(parents=True)
    (d / "constraints-runtime.txt").write_text("fastapi==0.141.1\npydantic==2.13.4\n", encoding="utf-8")
    (d / "pyproject.toml").write_text(
        '[build-system]\nrequires=["setuptools==80.9.0"]\nbuild-backend="setuptools.build_meta"\n'
        '[project]\nname="worldshepherd-sara"\nversion="0.1.0"\ndependencies=["fastapi>=0.110,<1","pydantic>=2.6,<3"]\n',
        encoding="utf-8",
    )
    return d


def item(name, version, digest):
    return {"metadata": {"name": name, "version": version}, "download_info": {"url": f"https://pypi.invalid/{name}.whl", "archive_info": {"hashes": {"sha256": digest}}}}


def report(ok=True):
    a = "a" * 64
    b = "b" * 64
    rows = [item("fastapi", "0.141.1", a), item("pydantic", "2.13.4", b)]
    if not ok:
        rows[0]["download_info"]["archive_info"]["hashes"] = {}
    rows.append({"metadata": {"name": "worldshepherd-sara", "version": "0.1.0"}, "download_info": {"url": "file:///repo/deployments/sara_verified_local_v1"}})
    return {"version": "1", "install": rows}


def test_exact_constraints_and_direct_coverage(tmp_path):
    d = write_repo(tmp_path)
    pins = mod.parse_constraints(d / "constraints-runtime.txt")
    audit = mod.audit_pyproject(d / "pyproject.toml", pins)
    assert audit["direct_runtime_dependencies"] == ["fastapi", "pydantic"]


def test_range_constraint_is_rejected(tmp_path):
    p = tmp_path / "constraints.txt"; p.write_text("fastapi>=0.1\n")
    with pytest.raises(ValueError, match="exact == pin"):
        mod.parse_constraints(p)


def test_report_requires_sha256(tmp_path):
    d = write_repo(tmp_path); pins = mod.parse_constraints(d / "constraints-runtime.txt")
    with pytest.raises(ValueError, match="lacks SHA-256"):
        mod.verify_resolver_report(report(False), pins)


def test_report_rejects_version_drift(tmp_path):
    d = write_repo(tmp_path); pins = mod.parse_constraints(d / "constraints-runtime.txt")
    r = report(); r["install"][0]["metadata"]["version"] = "0.141.0"
    with pytest.raises(ValueError, match="version mismatch"):
        mod.verify_resolver_report(r, pins)


def test_build_outputs_are_deterministic_with_fixed_timestamp(tmp_path, monkeypatch):
    d = write_repo(tmp_path)
    rp = tmp_path / "report.json"; rp.write_text(json.dumps(report(), sort_keys=True))
    out1 = tmp_path / "one"; out2 = tmp_path / "two"
    monkeypatch.setenv("WS_EVIDENCE_TIMESTAMP", "2026-09-30T13:07:00+00:00")
    a = mod.run_build(tmp_path, rp, out1, "deadbeef")
    b = mod.run_build(tmp_path, rp, out2, "deadbeef")
    assert a["outputs"] == b["outputs"]
    assert (out1 / "requirements-runtime-hashed.txt").read_bytes() == (out2 / "requirements-runtime-hashed.txt").read_bytes()
    assert (out1 / "worldshepherd-sara-runtime.cdx.json").read_bytes() == (out2 / "worldshepherd-sara-runtime.cdx.json").read_bytes()
    assert a["production_credit"] is False


def test_all_constraints_must_be_resolved(tmp_path):
    d = write_repo(tmp_path); pins = mod.parse_constraints(d / "constraints-runtime.txt")
    r = report(); r["install"] = [r["install"][0], r["install"][-1]]
    with pytest.raises(ValueError, match="absent from the resolved graph"):
        mod.verify_resolver_report(r, pins)
