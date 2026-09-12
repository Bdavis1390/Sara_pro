#!/usr/bin/env python3
"""Non-destructive PALACE convergence-anchor evidence ingester.

This tool NEVER launches PALACE and NEVER writes under --snapshot-root.
It consumes a copied/snapshotted evidence directory whose anchor subdirectories
contain an explicit anchor_status.json. COMPLETE anchors may additionally carry
canonical s11.csv with columns: frequency_ghz,real,imag.

The live Worldshepherd solver directory should not be passed directly. Create a
read-only snapshot/copy first, then point this tool at that snapshot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

TERMINAL = {"COMPLETE", "FAILED", "TIMEOUT", "NONCONVERGED"}
MESH_ORDER = {"coarse": 0, "medium": 1, "fine": 2}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema") != "WS-PALACE-ANCHOR-MANIFEST-V1":
        raise ValueError("unexpected manifest schema")
    anchors = data.get("anchors", [])
    if len(anchors) != data.get("expected_anchor_count"):
        raise ValueError("manifest anchor count mismatch")
    ids = [a["anchor_id"] for a in anchors]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate anchor_id in manifest")
    return data


def read_s11(path: Path) -> list[tuple[float, complex]]:
    rows: list[tuple[float, complex]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"frequency_ghz", "real", "imag"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: s11.csv must contain {sorted(required)}")
        for row in reader:
            freq = float(row["frequency_ghz"])
            real = float(row["real"])
            imag = float(row["imag"])
            if not all(math.isfinite(v) for v in (freq, real, imag)):
                raise ValueError(f"{path}: non-finite S11 sample")
            rows.append((freq, complex(real, imag)))
    if len(rows) < 2:
        raise ValueError(f"{path}: fewer than 2 finite S11 samples")
    freqs = [f for f, _ in rows]
    if len(freqs) != len(set(freqs)):
        raise ValueError(f"{path}: duplicate frequencies")
    return sorted(rows)


def resonance_freq(samples: list[tuple[float, complex]]) -> float:
    return min(samples, key=lambda x: abs(x[1]))[0]


def compare_medium_fine(
    med: list[tuple[float, complex]],
    fine: list[tuple[float, complex]],
    ds11_max: float,
    dfres_pct_max: float,
) -> dict[str, Any]:
    m = {round(f, 12): z for f, z in med}
    n = {round(f, 12): z for f, z in fine}
    common = sorted(set(m) & set(n))
    if len(common) < 2:
        return {"evaluable": False, "reason": "fewer_than_2_common_frequency_points"}
    delta = max(abs(m[f] - n[f]) for f in common)
    fm = resonance_freq(med)
    ff = resonance_freq(fine)
    dfpct = abs(fm - ff) / max(abs(ff), 1e-15) * 100.0
    return {
        "evaluable": True,
        "common_frequency_points": len(common),
        "max_abs_delta_complex_s11": delta,
        "resonance_shift_percent": dfpct,
        "pass_delta_s11": delta <= ds11_max,
        "pass_resonance_shift": dfpct <= dfres_pct_max,
        "pass": delta <= ds11_max and dfpct <= dfres_pct_max,
    }


def ingest(snapshot_root: Path, manifest_path: Path, output: Path) -> dict[str, Any]:
    root = snapshot_root.resolve(strict=True)
    out = output.resolve()
    if is_relative_to(out, root):
        raise ValueError("--output must be outside --snapshot-root to keep ingestion non-destructive")
    manifest = load_manifest(manifest_path)
    by_id = {a["anchor_id"]: a for a in manifest["anchors"]}

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status_file in sorted(root.rglob("anchor_status.json")):
        status = load_json(status_file)
        anchor_id = status.get("anchor_id")
        if anchor_id not in by_id:
            raise ValueError(f"{status_file}: unknown anchor_id {anchor_id!r}")
        if anchor_id in seen:
            raise ValueError(f"duplicate snapshot record for {anchor_id}")
        seen.add(anchor_id)
        expected = by_id[anchor_id]
        for key in ("run_id", "run_hash", "angle_deg", "control_state", "polarization", "mesh_level"):
            if status.get(key) != expected[key]:
                raise ValueError(f"{status_file}: {key} does not match frozen manifest")
        state = str(status.get("status", "")).upper()
        if state not in TERMINAL:
            raise ValueError(f"{status_file}: status must be one of {sorted(TERMINAL)}")

        anchor_dir = status_file.parent
        files = []
        for p in sorted(x for x in anchor_dir.rglob("*") if x.is_file()):
            files.append({
                "path": str(p.relative_to(anchor_dir)),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })

        rec: dict[str, Any] = {
            **expected,
            "status": state,
            "snapshot_relative_dir": str(anchor_dir.relative_to(root)),
            "status_file_sha256": sha256_file(status_file),
            "files": files,
            "s11_present": False,
            "s11_valid": False,
        }
        s11 = anchor_dir / "s11.csv"
        if state == "COMPLETE":
            if not s11.exists():
                raise ValueError(f"{anchor_id}: COMPLETE requires canonical s11.csv")
            samples = read_s11(s11)
            rec.update({
                "s11_present": True,
                "s11_valid": True,
                "sample_count": len(samples),
                "frequency_min_ghz": samples[0][0],
                "frequency_max_ghz": samples[-1][0],
                "resonance_frequency_ghz": resonance_freq(samples),
                "s11_sha256": sha256_file(s11),
            })
        elif s11.exists():
            try:
                samples = read_s11(s11)
                rec.update({
                    "s11_present": True,
                    "s11_valid": True,
                    "sample_count": len(samples),
                    "s11_sha256": sha256_file(s11),
                })
            except Exception as exc:
                rec.update({"s11_present": True, "s11_error": str(exc)})
        records.append(rec)

    complete = [r for r in records if r["status"] == "COMPLETE"]
    failures = [r for r in records if r["status"] != "COMPLETE"]

    groups: dict[tuple[int, str, str], dict[str, dict[str, Any]]] = {}
    for r in complete:
        key = (r["angle_deg"], r["control_state"], r["polarization"])
        groups.setdefault(key, {})[r["mesh_level"]] = r

    thresholds = manifest["acceptance"]
    convergence = []
    for key, meshes in sorted(groups.items()):
        entry: dict[str, Any] = {
            "angle_deg": key[0],
            "control_state": key[1],
            "polarization": key[2],
            "complete_mesh_levels": sorted(meshes, key=lambda x: MESH_ORDER[x]),
            "evaluable": False,
        }
        if "medium" in meshes and "fine" in meshes:
            med_path = root / meshes["medium"]["snapshot_relative_dir"] / "s11.csv"
            fine_path = root / meshes["fine"]["snapshot_relative_dir"] / "s11.csv"
            cmp = compare_medium_fine(
                read_s11(med_path),
                read_s11(fine_path),
                float(thresholds["delta_complex_s11_max"]),
                float(thresholds["delta_fres_percent_max"]),
            )
            entry.update(cmp)
        convergence.append(entry)

    all_54_complete = len(complete) == manifest["expected_anchor_count"]
    all_groups_evaluable = len(convergence) == 18 and all(x.get("evaluable") for x in convergence)
    all_groups_pass = all_groups_evaluable and all(x.get("pass") for x in convergence)

    report = {
        "schema": "WS-PALACE-ANCHOR-SNAPSHOT-REPORT-V1",
        "snapshot_root_name": root.name,
        "manifest_sha256": sha256_file(manifest_path),
        "expected_anchor_count": manifest["expected_anchor_count"],
        "observed_terminal_anchor_count": len(records),
        "complete_anchor_count": len(complete),
        "failure_timeout_nonconverged_count": len(failures),
        "missing_anchor_count": manifest["expected_anchor_count"] - len(records),
        "records": records,
        "convergence_groups": convergence,
        "convergence_gate": {
            "all_54_complete": all_54_complete,
            "all_18_medium_fine_groups_evaluable": all_groups_evaluable,
            "all_18_groups_pass_frozen_thresholds": all_groups_pass,
            "gate_pass": all_54_complete and all_groups_pass,
        },
        "evidence_effect": "INTERNAL_NUMERICAL_EVIDENCE_ONLY",
        "external_gate_effect": "NONE",
        "claims_boundary": (
            "Snapshot ingestion and convergence can support only the frozen numerical campaign. "
            "They do not constitute VNA measurement, physical validation, partner validation, "
            "independent replication, qualification, certification, or marketplace contact authority."
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def write_status(path: Path, anchor: dict[str, Any], state: str) -> None:
    payload = {**anchor, "status": state}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_s11(path: Path, shift: float = 0.0) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["frequency_ghz", "real", "imag"])
        w.writeheader()
        for i in range(5):
            freq = 9.8 + 0.1 * i
            z = complex(0.20 + 0.01 * i + shift, -0.05 + 0.005 * i)
            w.writerow({"frequency_ghz": freq, "real": z.real, "imag": z.imag})


def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        manifest = {
            "schema": "WS-PALACE-ANCHOR-MANIFEST-V1",
            "expected_anchor_count": 2,
            "acceptance": {"delta_complex_s11_max": 0.02, "delta_fres_percent_max": 0.25},
            "anchors": [
                {"anchor_id":"ANCHOR-001","run_id":"R1","run_hash":"a"*64,"angle_deg":0,"control_state":"LOW_C","polarization":"TE","mesh_level":"medium"},
                {"anchor_id":"ANCHOR-002","run_id":"R1","run_hash":"a"*64,"angle_deg":0,"control_state":"LOW_C","polarization":"TE","mesh_level":"fine"}
            ]
        }
        mp = base / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        snap = base / "snapshot"
        for anchor, shift in zip(manifest["anchors"], (0.0, 0.005)):
            d = snap / anchor["anchor_id"]
            d.mkdir(parents=True)
            write_status(d / "anchor_status.json", anchor, "COMPLETE")
            write_s11(d / "s11.csv", shift)
        report = ingest(snap, mp, base / "report.json")
        assert report["complete_anchor_count"] == 2
        assert report["convergence_groups"][0]["pass_delta_s11"] is True
        assert report["external_gate_effect"] == "NONE"

        bad = snap / "ANCHOR-002" / "anchor_status.json"
        payload = load_json(bad)
        payload["run_hash"] = "b"*64
        bad.write_text(json.dumps(payload), encoding="utf-8")
        try:
            ingest(snap, mp, base / "bad-report.json")
        except ValueError:
            pass
        else:
            raise AssertionError("identity mismatch was not rejected")

        try:
            ingest(snap, mp, snap / "report.json")
        except ValueError:
            pass
        else:
            raise AssertionError("write-under-snapshot was not rejected")
    print("PALACE snapshot ingester self-test: PASS")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot-root", type=Path)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
        return
    if not (args.snapshot_root and args.manifest and args.output):
        p.error("--snapshot-root, --manifest and --output are required unless --self-test is used")
    report = ingest(args.snapshot_root, args.manifest, args.output)
    print(json.dumps({
        "observed_terminal_anchor_count": report["observed_terminal_anchor_count"],
        "complete_anchor_count": report["complete_anchor_count"],
        "failure_timeout_nonconverged_count": report["failure_timeout_nonconverged_count"],
        "gate_pass": report["convergence_gate"]["gate_pass"],
        "external_gate_effect": report["external_gate_effect"]
    }, indent=2))


if __name__ == "__main__":
    main()
