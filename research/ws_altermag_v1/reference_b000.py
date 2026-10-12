from __future__ import annotations

import json
import math
from pathlib import Path

from .forward import g_wave
from .schema import digest


ROOT = Path(__file__).resolve().parent
DEFAULT_REFERENCE = ROOT / "manifests" / "crsb_reference_b000.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_reference(path: Path = DEFAULT_REFERENCE) -> dict:
    ref = _load(path)
    nodal = ref["nodal_planes"]
    tol = 1.0e-12

    phi_checks = []
    probe_theta = math.radians(47.0)
    for phi_deg in nodal["phi_deg"]:
        val = g_wave(probe_theta, math.radians(float(phi_deg)))
        phi_checks.append({"phi_deg": float(phi_deg), "basis_value": val, "is_nodal": abs(val) <= tol})

    theta_checks = []
    probe_phi = math.radians(20.0)
    for theta_deg in nodal["theta_deg"]:
        val = g_wave(math.radians(float(theta_deg)), probe_phi)
        theta_checks.append({"theta_deg": float(theta_deg), "basis_value": val, "is_nodal": abs(val) <= tol})

    pair = ref["representative_split_pair"]
    measured_split = abs(float(pair["f2_kT"]) - float(pair["f1_kT"]))
    declared_split = float(pair["split_kT"])
    split_consistent = abs(measured_split - declared_split) <= 1.0e-12

    passed = (
        all(item["is_nodal"] for item in phi_checks)
        and all(item["is_nodal"] for item in theta_checks)
        and split_consistent
        and ref["order_parameter"]["irreducible_representation"] == "B1g"
        and ref["order_parameter"]["real_spherical_harmonic"] == "Y_4^-3"
    )

    record = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-R",
        "status": "SUPPORTED BY LITERATURE",
        "source": ref["source"],
        "reference_scope": "Published textual observables and symmetry metadata; not a full raw-data reproduction.",
        "phi_nodal_checks": phi_checks,
        "theta_nodal_checks": theta_checks,
        "representative_split_kT_recomputed": measured_split,
        "representative_split_consistent": split_consistent,
        "pass": passed,
        "claim_boundary": (
            "This adapter validates internal consistency between the encoded literature reference "
            "and the B1g-like analytic basis. It does not independently reproduce the experiment."
        ),
    }
    record["reference_digest"] = digest(record)
    return record


def main() -> None:
    print(json.dumps(validate_reference(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
