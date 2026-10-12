from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from .schema import digest


ROOT = Path(__file__).resolve().parent
DEFAULT_STRUCTURE = ROOT / "manifests" / "crsb_structure_b000.json"


EXPECTED_POSITIONS = {
    "Cr1": ("Cr", "2a", (0.0, 0.0, 0.0), 1),
    "Cr2": ("Cr", "2a", (0.0, 0.0, 0.5), -1),
    "Sb1": ("Sb", "2c", (1.0 / 3.0, 2.0 / 3.0, 0.25), 0),
    "Sb2": ("Sb", "2c", (2.0 / 3.0, 1.0 / 3.0, 0.75), 0),
}


def _close(a: float, b: float, tol: float = 1.0e-12) -> bool:
    return abs(float(a) - float(b)) <= tol


def validate_structure(path: Path = DEFAULT_STRUCTURE) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    sites = manifest["sites"]
    by_label = {s["label"]: s for s in sites}

    labels_ok = set(by_label) == set(EXPECTED_POSITIONS)
    position_checks = {}
    for label, (species, wyckoff, expected_frac, spin) in EXPECTED_POSITIONS.items():
        site = by_label.get(label)
        ok = bool(
            site
            and site["species"] == species
            and site["wyckoff"] == wyckoff
            and int(site["initial_spin_sign"]) == spin
            and len(site["fractional"]) == 3
            and all(_close(v, e) for v, e in zip(site["fractional"], expected_frac))
        )
        position_checks[label] = ok

    composition = Counter(s["species"] for s in sites)
    stoichiometry_ok = composition == Counter({"Cr": 2, "Sb": 2})
    cr_spin_sum = sum(
        int(s["initial_spin_sign"])
        for s in sites
        if s["species"] == "Cr"
    )
    compensated_initialization = cr_spin_sum == 0

    lattice = manifest["lattice_A"]
    lattice_ok = (
        _close(lattice["a"], 4.12)
        and _close(lattice["b"], 4.12)
        and _close(lattice["c"], 5.47)
        and _close(lattice["gamma_deg"], 120.0)
    )

    symmetry_ok = (
        manifest["space_group_parent"]["symbol"] == "P63/mmc"
        and int(manifest["space_group_parent"]["number"]) == 194
        and manifest["magnetic_model_space_group"] == "P3m1"
    )

    passed = (
        labels_ok
        and all(position_checks.values())
        and stoichiometry_ok
        and compensated_initialization
        and lattice_ok
        and symmetry_ok
    )

    record = {
        "program": manifest["program"],
        "benchmark": manifest["benchmark"],
        "labels_ok": labels_ok,
        "position_checks": position_checks,
        "stoichiometry": dict(sorted(composition.items())),
        "stoichiometry_ok": stoichiometry_ok,
        "cr_initial_spin_sum": cr_spin_sum,
        "compensated_initialization": compensated_initialization,
        "lattice_ok": lattice_ok,
        "symmetry_ok": symmetry_ok,
        "pass": passed,
        "claim_status": ["IMPLEMENTED IN SOFTWARE", "SUPPORTED BY LITERATURE"],
        "claim_boundary": manifest["claim_boundary"],
    }
    record["structure_digest"] = digest(record)
    return record


def main() -> None:
    print(json.dumps(validate_structure(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
